"""
Bikozava — Flask & Minimal WSGI Compatibility Layer (`app/flask_compat.py`)

When running in a standard production environment with `Flask` installed via
`pip install -r requirements.txt`, this module imports and re-exports the real
`flask` and `werkzeug` symbols directly.

When running in an offline or minimal container where `Flask` is not yet
installed in site-packages, this module provides a clean, standards-compliant
WSGI microframework implementation built on top of pre-installed `jinja2`,
`itsdangerous`, `markupsafe`, and `wsgiref` so that the exact same Flask
application code, blueprints, signed cookie sessions, file uploads, and test
client execute identically without code modifications.
"""

from __future__ import annotations

import cgi
import http.cookies
import io
import json
import mimetypes
import os
import re
import sys
import traceback
import urllib.parse
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

from itsdangerous import BadSignature, URLSafeTimedSerializer
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

try:
    # Use native Flask if installed in the environment
    import flask as _real_flask  # type: ignore
    from flask import (  # type: ignore
        Blueprint,
        Flask,
        Response,
        abort,
        current_app,
        flash,
        g,
         get_flashed_messages,
        jsonify,
        make_response,
        redirect,
        render_template,
        request,
        send_from_directory,
        session,
        url_for,
    )
    from werkzeug.utils import secure_filename  # type: ignore

    USING_NATIVE_FLASK = True

except ImportError:
    USING_NATIVE_FLASK = False

    _current_app_var: ContextVar[Optional["Flask"]] = ContextVar("current_app", default=None)
    _request_var: ContextVar[Optional["Request"]] = ContextVar("request", default=None)
    _session_var: ContextVar[Optional[Dict[str, Any]]] = ContextVar("session", default=None)
    _g_var: ContextVar[Optional[" _AppCtxGlobals"]] = ContextVar("g", default=None)

    class _Proxy:
        def __init__(self, getter: Callable[[], Any]):
            object.__setattr__(self, "_getter", getter)

        def _get(self) -> Any:
            val = object.__getattribute__(self, "_getter")()
            if val is None:
                raise RuntimeError("Working outside of application/request context.")
            return val

        def __getattr__(self, name: str) -> Any:
            return getattr(self._get(), name)

        def __setattr__(self, name: str, value: Any) -> None:
            setattr(self._get(), name, value)

        def __getitem__(self, key: Any) -> Any:
            return self._get()[key]

        def __setitem__(self, key: Any, value: Any) -> None:
            self._get()[key] = value

        def __delitem__(self, key: Any) -> None:
            del self._get()[key]

        def __contains__(self, key: Any) -> bool:
            return key in self._get()

        def get(self, key: Any, default: Any = None) -> Any:
            return self._get().get(key, default)

        def pop(self, key: Any, *args: Any) -> Any:
            return self._get().pop(key, *args)

        def clear(self) -> None:
            self._get().clear()

        def update(self, *args: Any, **kwargs: Any) -> None:
            self._get().update(*args, **kwargs)

        def keys(self) -> Any:
            return self._get().keys()

        def items(self) -> Any:
            return self._get().items()

        def values(self) -> Any:
            return self._get().values()

    class _AppCtxGlobals:
        def get(self, name: str, default: Any = None) -> Any:
            return self.__dict__.get(name, default)

    current_app: Any = _Proxy(lambda: _current_app_var.get())
    request: Any = _Proxy(lambda: _request_var.get())
    session: Any = _Proxy(lambda: _session_var.get())
    g: Any = _Proxy(lambda: _g_var.get())

    def secure_filename(filename: str) -> str:
        if not filename:
            return ""
        filename = os.path.basename(filename.replace("\\", "/"))
        filename = re.sub(r"[^A-Za-z0-9_.-]", "_", filename)
        filename = filename.strip("._")
        return filename or "uploaded_file"

    class HTTPException(Exception):
        def __init__(self, code: int, description: str = ""):
            super().__init__(f"HTTP {code}: {description}")
            self.code = code
            self.description = description

    def abort(code: int, description: str = "") -> None:
        raise HTTPException(code, description)

    class FileStorage:
        def __init__(self, stream: bytes, filename: str, content_type: str = "application/octet-stream"):
            self.stream = io.BytesIO(stream)
            self._bytes = stream
            self.filename = filename
            self.content_type = content_type
            self.mimetype = (content_type or "application/octet-stream").split(";")[0].strip().lower()

        def read(self, size: int = -1) -> bytes:
            return self.stream.read(size)

        def seek(self, pos: int, whence: int = 0) -> int:
            return self.stream.seek(pos, whence)

        def tell(self) -> int:
            return self.stream.tell()

        def save(self, dst: Union[str, Path]) -> None:
            dst_path = Path(dst)
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dst_path, "wb") as f:
                f.write(self._bytes)

        def __bool__(self) -> bool:
            return bool(self.filename and len(self._bytes) > 0)

    class MultiDict(dict):
        def __init__(self, mapping: Optional[Dict[str, List[Any]]] = None):
            super().__init__()
            self._lists: Dict[str, List[Any]] = {}
            if mapping:
                for k, v in mapping.items():
                    if isinstance(v, list):
                        self._lists[k] = v
                        super().__setitem__(k, v[0] if v else "")
                    else:
                        self._lists[k] = [v]
                        super().__setitem__(k, v)

        def getlist(self, key: str) -> List[Any]:
            return list(self._lists.get(key, []))

        def setlist(self, key: str, values: List[Any]) -> None:
            self._lists[key] = list(values)
            super().__setitem__(key, values[0] if values else "")

    class Request:
        def __init__(self, environ: Dict[str, Any], app: "Flask"):
            self.environ = environ
            self.method = environ.get("REQUEST_METHOD", "GET").upper()
            raw_path = environ.get("PATH_INFO", "/") or "/"
            self.path = raw_path
            self.query_string = environ.get("QUERY_STRING", "")
            self.remote_addr = (
                environ.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
                or environ.get("REMOTE_ADDR", "127.0.0.1")
                or "127.0.0.1"
            )
            self.scheme = environ.get("wsgi.url_scheme", "http")
            self.host = environ.get("HTTP_HOST", "localhost:8000")
            self.url_root = f"{self.scheme}://{self.host}/"
            self.url = f"{self.scheme}://{self.host}{self.path}" + (f"?{self.query_string}" if self.query_string else "")
            self.endpoint: Optional[str] = None
            self.view_args: Dict[str, Any] = {}

            # Headers
            self.headers: Dict[str, str] = {}
            for k, v in environ.items():
                if k.startswith("HTTP_"):
                    hname = k[5:].replace("_", "-").title()
                    self.headers[hname] = str(v)
            if "CONTENT_TYPE" in environ and environ["CONTENT_TYPE"]:
                self.headers["Content-Type"] = str(environ["CONTENT_TYPE"])
            if "CONTENT_LENGTH" in environ and environ["CONTENT_LENGTH"]:
                self.headers["Content-Length"] = str(environ["CONTENT_LENGTH"])

            # Cookies
            self.cookies: Dict[str, str] = {}
            cookie_header = environ.get("HTTP_COOKIE", "")
            if cookie_header:
                c = http.cookies.SimpleCookie()
                try:
                    c.load(cookie_header)
                    for k, morsel in c.items():
                        self.cookies[k] = morsel.value
                except Exception:
                    pass

            # Query args
            parsed_qs = urllib.parse.parse_qs(self.query_string, keep_blank_values=True)
            self.args = MultiDict(parsed_qs)

            # Body / Form / Files / JSON
            self.form = MultiDict()
            self.files = MultiDict()
            self._raw_body = b""
            self._json_cache: Any = None

            content_length_str = environ.get("CONTENT_LENGTH") or "0"
            try:
                content_length = int(content_length_str)
            except ValueError:
                content_length = 0

            max_len = app.config.get("MAX_CONTENT_LENGTH")
            if max_len and content_length > max_len:
                abort(413, "Request entity too large")

            wsgi_input = environ.get("wsgi.input")
            if wsgi_input and content_length > 0:
                self._raw_body = wsgi_input.read(content_length)

            ctype = (environ.get("CONTENT_TYPE") or "").lower()
            if self.method in ("POST", "PUT", "PATCH", "DELETE") and self._raw_body:
                if "application/x-www-form-urlencoded" in ctype:
                    parsed_form = urllib.parse.parse_qs(
                        self._raw_body.decode("utf-8", errors="replace"),
                        keep_blank_values=True,
                    )
                    self.form = MultiDict(parsed_form)
                elif "multipart/form-data" in ctype:
                    env_copy = {
                        "REQUEST_METHOD": self.method,
                        "CONTENT_TYPE": environ.get("CONTENT_TYPE", ""),
                        "CONTENT_LENGTH": str(len(self._raw_body)),
                    }
                    fs = cgi.FieldStorage(
                        fp=io.BytesIO(self._raw_body),
                        environ=env_copy,
                        keep_blank_values=True,
                    )
                    form_lists: Dict[str, List[str]] = {}
                    file_lists: Dict[str, List[FileStorage]] = {}
                    if fs.list:
                        for item in fs.list:
                            if getattr(item, "filename", None) is not None and item.filename != "":
                                data = item.file.read() if item.file else b""
                                fobj = FileStorage(
                                    stream=data,
                                    filename=item.filename,
                                    content_type=getattr(item, "type", "application/octet-stream"),
                                )
                                file_lists.setdefault(item.name, []).append(fobj)
                            else:
                                val = item.value if isinstance(item.value, str) else (
                                    item.value.decode("utf-8", errors="replace") if item.value else ""
                                )
                                form_lists.setdefault(item.name, []).append(val)
                    self.form = MultiDict(form_lists)
                    self.files = MultiDict(file_lists)

        @property
        def data(self) -> bytes:
            return self._raw_body

        @property
        def is_json(self) -> bool:
            ctype = self.headers.get("Content-Type", "").lower()
            return "application/json" in ctype

        def get_json(self, silent: bool = False, force: bool = False) -> Any:
            if self._json_cache is not None:
                return self._json_cache
            if not self._raw_body:
                return None
            try:
                self._json_cache = json.loads(self._raw_body.decode("utf-8"))
                return self._json_cache
            except Exception:
                if silent:
                    return None
                abort(400, "Invalid JSON payload")

    class Response:
        def __init__(
            self,
            response: Union[str, bytes, Iterable[bytes]] = "",
            status: int = 200,
            headers: Optional[Dict[str, str]] = None,
            mimetype: str = "text/html; charset=utf-8",
        ):
            if isinstance(response, str):
                self.data = response.encode("utf-8")
            elif isinstance(response, bytes):
                self.data = response
            else:
                self.data = b"".join(response)
            self.status_code = int(status)
            self.headers: Dict[str, str] = {}
            self._cookies: List[str] = []
            if headers:
                for k, v in headers.items():
                    self.headers[k] = v
            if "Content-Type" not in self.headers:
                self.headers["Content-Type"] = mimetype

        def get_data(self, as_text: bool = False) -> Union[str, bytes]:
            if as_text:
                return self.data.decode("utf-8", errors="replace")
            return self.data

        def get_json(self) -> Any:
            return json.loads(self.get_data(as_text=True))

        def set_cookie(
            self,
            key: str,
            value: str = "",
            max_age: Optional[int] = None,
            path: str = "/",
            secure: bool = False,
            httponly: bool = True,
            samesite: str = "Lax",
        ) -> None:
            c = http.cookies.SimpleCookie()
            c[key] = value
            c[key]["path"] = path
            if max_age is not None:
                c[key]["max-age"] = str(max_age)
            if secure:
                c[key]["secure"] = True
            if httponly:
                c[key]["httponly"] = True
            if samesite:
                c[key]["samesite"] = samesite
            self._cookies.append(c.output(header="").strip())

        def delete_cookie(self, key: str, path: str = "/") -> None:
            self.set_cookie(key, "", max_age=0, path=path)

    def make_response(rv: Any, status: Optional[int] = None, headers: Optional[Dict[str, str]] = None) -> Response:
        if isinstance(rv, Response):
            if status is not None:
                rv.status_code = int(status)
            if headers:
                rv.headers.update(headers)
            return rv
        if isinstance(rv, tuple):
            body = rv[0]
            st = rv[1] if len(rv) > 1 else (status or 200)
            hd = rv[2] if len(rv) > 2 else headers
            return make_response(body, st, hd)
        if isinstance(rv, dict):
            return Response(
                json.dumps(rv, ensure_ascii=False),
                status=status or 200,
                headers=headers,
                mimetype="application/json; charset=utf-8",
            )
        return Response(rv, status=status or 200, headers=headers)

    def jsonify(*args: Any, **kwargs: Any) -> Response:
        payload = args[0] if args else kwargs
        return Response(
            json.dumps(payload, ensure_ascii=False),
            status=200,
            mimetype="application/json; charset=utf-8",
        )

    def redirect(location: str, code: int = 302) -> Response:
        return Response(
            f'<!doctype html><title>Redirect</title><p>Redirecting to <a href="{location}">{location}</a></p>',
            status=code,
            headers={"Location": location},
        )

    def flash(message: str, category: str = "info") -> None:
        flashes = session.get("_flashes", [])
        flashes.append([category, message])
        session["_flashes"] = flashes

    def get_flashed_messages(with_categories: bool = False) -> List[Any]:
        flashes = session.pop("_flashes", [])
        if with_categories:
            return [(c, m) for c, m in flashes]
        return [m for _, m in flashes]

    def send_from_directory(directory: Union[str, Path], path: str, **kwargs: Any) -> Response:
        base_dir = Path(directory).resolve()
        rel_clean = path.lstrip("/\\")
        target = (base_dir / rel_clean).resolve()
        if not str(target).startswith(str(base_dir)) or not target.is_file():
            abort(404, "File not found")
        mime, _ = mimetypes.guess_type(str(target))
        with open(target, "rb") as f:
            data = f.read()
        headers = {"Cache-Control": "public, max-age=3600"}
        return Response(data, status=200, headers=headers, mimetype=mime or "application/octet-stream")

    class _RouteRule:
        def __init__(self, rule: str, endpoint: str, view_func: Callable[..., Any], methods: List[str]):
            self.rule = rule
            self.endpoint = endpoint
            self.view_func = view_func
            self.methods = [m.upper() for m in methods]
            self.param_types: Dict[str, str] = {}

            # Convert Flask route syntax like /admin/invitations/<int:id>/edit to regex
            pattern = "^"
            pos = 0
            for m in re.finditer(r"<(?:(int|path|string):)?([a-zA-Z_][a-zA-Z0-9_]*)>", rule):
                pattern += re.escape(rule[pos : m.start()])
                ptype = m.group(1) or "string"
                pname = m.group(2)
                self.param_types[pname] = ptype
                if ptype == "int":
                    pattern += f"(?P<{pname}>[0-9]+)"
                elif ptype == "path":
                    pattern += f"(?P<{pname}>.+)"
                else:
                    pattern += f"(?P<{pname}>[^/]+)"
                pos = m.end()
            pattern += re.escape(rule[pos:]) + "$"
            self.regex = re.compile(pattern)

        def match(self, path: str) -> Optional[Dict[str, Any]]:
            m = self.regex.match(path)
            if not m:
                return None
            params: Dict[str, Any] = {}
            for k, v in m.groupdict().items():
                if self.param_types.get(k) == "int":
                    params[k] = int(v)
                else:
                    params[k] = v
            return params

        def build(self, values: Dict[str, Any]) -> str:
            url = self.rule
            used = set()
            for pname, ptype in self.param_types.items():
                if pname not in values:
                    raise KeyError(f"Missing URL parameter {pname} for endpoint {self.endpoint}")
                val = str(values[pname])
                used.add(pname)
                url = re.sub(rf"<(?:{ptype}:)?{pname}>", val, url)
            extra = {k: v for k, v in values.items() if k not in used and not k.startswith("_")}
            if extra:
                qs = urllib.parse.urlencode(extra)
                url = f"{url}?{qs}"
            return url

    def url_for(endpoint: str, **values: Any) -> str:
        app = current_app
        external = values.pop("_external", False)
        if endpoint == "static":
            filename = values.get("filename", "")
            path = f"/static/{filename.lstrip('/')}"
            if external:
                base = app.config.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
                return f"{base}{path}"
            return path
        for rule in app._rules:
            if rule.endpoint == endpoint:
                built = rule.build(values)
                if external:
                    base = app.config.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
                    return f"{base}{built}"
                return built
        raise ValueError(f"Unknown endpoint: {endpoint}")

    def render_template(template_name: str, **context: Any) -> str:
        app = current_app
        ctx: Dict[str, Any] = {
            "request": request,
            "session": session,
            "g": g,
            "url_for": url_for,
            "get_flashed_messages": get_flashed_messages,
            "config": app.config,
        }
        for processor in app._context_processors:
            ctx.update(processor())
        ctx.update(context)
        tmpl = app.jinja_env.get_template(template_name)
        return tmpl.render(**ctx)

    class Blueprint:
        def __init__(self, name: str, import_name: str, url_prefix: str = ""):
            self.name = name
            self.import_name = import_name
            self.url_prefix = url_prefix.rstrip("/")
            self.deferred_routes: List[Tuple[str, str, Callable[..., Any], List[str]]] = []

        def route(self, rule: str, methods: Optional[List[str]] = None, endpoint: Optional[str] = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
                ep = endpoint or f.__name__
                self.deferred_routes.append((rule, ep, f, methods or ["GET"]))
                return f
            return decorator

    class _AppContext:
        def __init__(self, app: "Flask"):
            self.app = app
            self._tok_app = None
            self._tok_g = None

        def __enter__(self) -> "Flask":
            self._tok_app = _current_app_var.set(self.app)
            self._tok_g = _g_var.set(_AppCtxGlobals())
            return self.app

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            for fn in self.app._teardown_funcs:
                try:
                    fn(exc_val)
                except Exception:
                    pass
            if self._tok_g is not None:
                _g_var.reset(self._tok_g)
            if self._tok_app is not None:
                _current_app_var.reset(self._tok_app)

    class Flask:
        def __init__(
            self,
            import_name: str,
            static_folder: str = "static",
            template_folder: str = "templates",
        ):
            self.import_name = import_name
            base_path = Path(__file__).resolve().parent
            self.root_path = str(base_path)
            self.static_folder = str((base_path / static_folder).resolve())
            self.template_folder = str((base_path / template_folder).resolve())
            self.config: Dict[str, Any] = {
                "SECRET_KEY": "dev-secret-key",
                "SESSION_COOKIE_NAME": "bikozava_session",
                "SESSION_COOKIE_HTTPONLY": True,
                "SESSION_COOKIE_SECURE": False,
                "SESSION_COOKIE_SAMESITE": "Lax",
                "PERMANENT_SESSION_LIFETIME_SECONDS": 28800,
                "MAX_CONTENT_LENGTH": 25 * 1024 * 1024,
            }
            self._rules: List[_RouteRule] = []
            self._before_request_funcs: List[Callable[[], Any]] = []
            self._after_request_funcs: List[Callable[[Response], Response]] = []
            self._teardown_funcs: List[Callable[[Optional[BaseException]], None]] = []
            self._context_processors: List[Callable[[], Dict[str, Any]]] = []
            self._error_handlers: Dict[int, Callable[[Any], Any]] = {}

            self.jinja_env = Environment(
                loader=FileSystemLoader(self.template_folder),
                autoescape=select_autoescape(["html", "xml"]),
            )
            self.jinja_env.filters["tojson"] = lambda v: Markup(json.dumps(v, ensure_ascii=False))

            # Built-in static file route
            self.add_url_rule(
                "/static/<path:filename>",
                endpoint="static",
                view_func=self._serve_static,
                methods=["GET"],
            )

        def _serve_static(self, filename: str) -> Response:
            return send_from_directory(self.static_folder, filename)

        def app_context(self) -> _AppContext:
            return _AppContext(self)

        def add_url_rule(
            self,
            rule: str,
            endpoint: str,
            view_func: Callable[..., Any],
            methods: Optional[List[str]] = None,
        ) -> None:
            self._rules.append(_RouteRule(rule, endpoint, view_func, methods or ["GET"]))

        def route(self, rule: str, methods: Optional[List[str]] = None, endpoint: Optional[str] = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
                ep = endpoint or f.__name__
                self.add_url_rule(rule, ep, f, methods or ["GET"])
                return f
            return decorator

        def register_blueprint(self, bp: Blueprint, url_prefix: Optional[str] = None) -> None:
            prefix = (url_prefix if url_prefix is not None else bp.url_prefix).rstrip("/")
            for rule, ep, func, methods in bp.deferred_routes:
                full_rule = f"{prefix}/{rule.lstrip('/')}" if prefix else rule
                if full_rule != "/" and full_rule.endswith("/"):
                    full_rule = full_rule.rstrip("/")
                full_ep = f"{bp.name}.{ep}"
                self.add_url_rule(full_rule, full_ep, func, methods)

        def before_request(self, f: Callable[[], Any]) -> Callable[[], Any]:
            self._before_request_funcs.append(f)
            return f

        def after_request(self, f: Callable[[Response], Response]) -> Callable[[Response], Response]:
            self._after_request_funcs.append(f)
            return f

        def teardown_appcontext(self, f: Callable[[Optional[BaseException]], None]) -> Callable[[Optional[BaseException]], None]:
            self._teardown_funcs.append(f)
            return f

        def context_processor(self, f: Callable[[], Dict[str, Any]]) -> Callable[[], Dict[str, Any]]:
            self._context_processors.append(f)
            return f

        def errorhandler(self, code: int) -> Callable[[Callable[[Any], Any]], Callable[[Any], Any]]:
            def decorator(f: Callable[[Any], Any]) -> Callable[[Any], Any]:
                self._error_handlers[code] = f
                return f
            return decorator

        def _serializer(self) -> URLSafeTimedSerializer:
            return URLSafeTimedSerializer(str(self.config["SECRET_KEY"]), salt="bikozava-cookie-session")

        def _load_session(self, req: Request) -> Dict[str, Any]:
            cookie_name = self.config.get("SESSION_COOKIE_NAME", "bikozava_session")
            raw = req.cookies.get(cookie_name)
            if not raw:
                return {}
            max_age = int(self.config.get("PERMANENT_SESSION_LIFETIME_SECONDS", 28800))
            try:
                data = self._serializer().loads(raw, max_age=max_age)
                return data if isinstance(data, dict) else {}
            except BadSignature:
                return {}

        def _save_session(self, sess: Dict[str, Any], resp: Response) -> None:
            cookie_name = self.config.get("SESSION_COOKIE_NAME", "bikozava_session")
            if not sess:
                resp.delete_cookie(cookie_name)
                return
            signed = self._serializer().dumps(sess)
            resp.set_cookie(
                cookie_name,
                signed,
                max_age=int(self.config.get("PERMANENT_SESSION_LIFETIME_SECONDS", 28800)),
                path="/",
                secure=bool(self.config.get("SESSION_COOKIE_SECURE", False)),
                httponly=bool(self.config.get("SESSION_COOKIE_HTTPONLY", True)),
                samesite=str(self.config.get("SESSION_COOKIE_SAMESITE", "Lax")),
            )

        def handle_Sync_Request(self, environ: Dict[str, Any]) -> Response:
            tok_app = _current_app_var.set(self)
            tok_g = _g_var.set(_AppCtxGlobals())
            tok_req = None
            tok_sess = None
            exc_caught: Optional[BaseException] = None
            try:
                req = Request(environ, self)
                tok_req = _request_var.set(req)
                sess = self._load_session(req)
                tok_sess = _session_var.set(sess)

                resp: Optional[Response] = None
                try:
                    # Match route first so request.endpoint is populated in before_request
                    matched_rule: Optional[_RouteRule] = None
                    matched_args: Optional[Dict[str, Any]] = None
                    method_mismatch = False
                    for rule in self._rules:
                        m = rule.match(req.path)
                        if m is not None:
                            if req.method in rule.methods or (req.method == "HEAD" and "GET" in rule.methods):
                                matched_rule = rule
                                matched_args = m
                                break
                            else:
                                method_mismatch = True

                    if matched_rule is not None and matched_args is not None:
                        req.endpoint = matched_rule.endpoint
                        req.view_args = matched_args

                    for bf in self._before_request_funcs:
                        rv = bf()
                        if rv is not None:
                            resp = make_response(rv)
                            break

                    if resp is None:
                        if matched_rule is None:
                            if method_mismatch:
                                abort(405, "Method Not Allowed")
                            abort(404, "Not Found")
                        rv = matched_rule.view_func(**(matched_args or {}))
                        resp = make_response(rv)

                except HTTPException as he:
                    handler = self._error_handlers.get(he.code)
                    if handler:
                        resp = make_response(handler(he), he.code)
                    else:
                        resp = Response(
                            f"<h1>{he.code}</h1><p>{he.description}</p>",
                            status=he.code,
                        )
                except Exception as exc:
                    exc_caught = exc
                    handler = self._error_handlers.get(500)
                    if handler:
                        resp = make_response(handler(exc), 500)
                    else:
                        resp = Response("<h1>500 Internal Server Error</h1>", status=500)

                for af in self._after_request_funcs:
                    resp = af(resp)

                self._save_session(sess, resp)
                return resp
            finally:
                for fn in self._teardown_funcs:
                    try:
                        fn(exc_caught)
                    except Exception:
                        pass
                if tok_sess is not None:
                    _session_var.reset(tok_sess)
                if tok_req is not None:
                    _request_var.reset(tok_req)
                _g_var.reset(tok_g)
                _current_app_var.reset(tok_app)

        def wsgi_app(self, environ: Dict[str, Any], start_response: Callable[[str, List[Tuple[str, str]]], Any]) -> Iterable[bytes]:
            resp = self.handle_Sync_Request(environ)
            status_phrases = {
                200: "200 OK",
                201: "201 Created",
                204: "204 No Content",
                301: "301 Moved Permanently",
                302: "302 Found",
                400: "400 Bad Request",
                401: "401 Unauthorized",
                403: "403 Forbidden",
                404: "404 Not Found",
                405: "405 Method Not Allowed",
                413: "413 Payload Too Large",
                429: "429 Too Many Requests",
                500: "500 Internal Server Error",
            }
            status_line = status_phrases.get(resp.status_code, f"{resp.status_code} OK")
            header_list = list(resp.headers.items())
            for cookie_val in resp._cookies:
                header_list.append(("Set-Cookie", cookie_val))
            header_list.append(("Content-Length", str(len(resp.data))))
            start_response(status_line, header_list)
            return [resp.data]

        def __call__(self, environ: Dict[str, Any], start_response: Callable[[str, List[Tuple[str, str]]], Any]) -> Iterable[bytes]:
            return self.wsgi_app(environ, start_response)

        def test_client(self) -> "_TestClient":
            return _TestClient(self)

        def run(self, host: str = "0.0.0.0", port: int = 8000, debug: bool = False) -> None:
            from wsgiref.simple_server import make_server
            print(f" * Running Bikozava on http://{host}:{port} (Press CTRL+C to quit)")
            with make_server(host, port, self) as httpd:
                httpd.serve_forever()

    class _TestClient:
        def __init__(self, app: Flask):
            self.app = app
            self.cookies: Dict[str, str] = {}

        def _encode_multipart(self, data: Dict[str, Any]) -> Tuple[bytes, str]:
            boundary = "----BikozavaTestBoundary7MA4YWxkTrZu0gW"
            body = io.BytesIO()
            for key, val in data.items():
                if isinstance(val, tuple):
                    # (stream_or_bytes, filename, content_type)
                    raw_stream, fname = val[0], val[1]
                    ctype = val[2] if len(val) > 2 else (mimetypes.guess_type(fname)[0] or "application/octet-stream")
                    content = raw_stream.read() if hasattr(raw_stream, "read") else raw_stream
                    if isinstance(content, str):
                        content = content.encode("utf-8")
                    body.write(f"--{boundary}\r\n".encode("utf-8"))
                    body.write(
                        f'Content-Disposition: form-data; name="{key}"; filename="{fname}"\r\n'.encode("utf-8")
                    )
                    body.write(f"Content-Type: {ctype}\r\n\r\n".encode("utf-8"))
                    body.write(content)
                    body.write(b"\r\n")
                else:
                    body.write(f"--{boundary}\r\n".encode("utf-8"))
                    body.write(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
                    body.write(str(val).encode("utf-8"))
                    body.write(b"\r\n")
            body.write(f"--{boundary}--\r\n".encode("utf-8"))
            return body.getvalue(), f"multipart/form-data; boundary={boundary}"

        def open(
            self,
            path: str,
            method: str = "GET",
            data: Optional[Dict[str, Any]] = None,
            json_data: Any = None,
            headers: Optional[Dict[str, str]] = None,
            follow_redirects: bool = False,
            content_type: Optional[str] = None,
            environ_base: Optional[Dict[str, str]] = None,
        ) -> Response:
            parsed = urllib.parse.urlsplit(path)
            req_path = parsed.path or "/"
            qs = parsed.query or ""

            body_bytes = b""
            ctype = content_type or ""
            if json_data is not None:
                body_bytes = json.dumps(json_data).encode("utf-8")
                ctype = "application/json"
            elif data is not None:
                has_files = any(isinstance(v, tuple) for v in data.values())
                if has_files or "multipart/form-data" in ctype:
                    body_bytes, ctype = self._encode_multipart(data)
                else:
                    body_bytes = urllib.parse.urlencode(data, doseq=True).encode("utf-8")
                    ctype = "application/x-www-form-urlencoded"

            environ: Dict[str, Any] = {
                "REQUEST_METHOD": method.upper(),
                "PATH_INFO": req_path,
                "QUERY_STRING": qs,
                "SERVER_NAME": "localhost",
                "SERVER_PORT": "8000",
                "HTTP_HOST": "localhost:8000",
                "REMOTE_ADDR": (environ_base or {}).get("REMOTE_ADDR", "127.0.0.1"),
                "wsgi.url_scheme": "http",
                "wsgi.input": io.BytesIO(body_bytes),
                "CONTENT_LENGTH": str(len(body_bytes)),
                "CONTENT_TYPE": ctype,
            }
            if self.cookies:
                environ["HTTP_COOKIE"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
            if headers:
                for hk, hv in headers.items():
                    environ[f"HTTP_{hk.upper().replace('-', '_')}"] = hv

            resp = self.app.handle_Sync_Request(environ)

            # Update client cookie jar
            for sc in resp._cookies:
                c = http.cookies.SimpleCookie()
                c.load(sc)
                for ck, morsel in c.items():
                    if morsel["max-age"] == "0" or morsel.value == "":
                        self.cookies.pop(ck, None)
                    else:
                        self.cookies[ck] = morsel.value

            if follow_redirects and resp.status_code in (301, 302, 303, 307, 308):
                loc = resp.headers.get("Location", "/")
                if loc.startswith("http://") or loc.startswith("https://"):
                    sp = urllib.parse.urlsplit(loc)
                    loc = sp.path + (f"?{sp.query}" if sp.query else "")
                return self.open(loc, method="GET", follow_redirects=True, environ_base=environ_base)
            return resp

        def get(self, path: str, **kwargs: Any) -> Response:
            return self.open(path, method="GET", **kwargs)

        def post(self, path: str, data: Optional[Dict[str, Any]] = None, json: Any = None, **kwargs: Any) -> Response:
            return self.open(path, method="POST", data=data, json_data=json, **kwargs)
