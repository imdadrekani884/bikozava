"""
Bikozava — Security, Authentication, Audit Logging, File Validation & Hardening (`app/security.py`)

Implements:
- Password hashing (Argon2id / bcrypt when installed, with cryptographic
  `hashlib.scrypt` + PBKDF2-HMAC-SHA256 support)
- Constant-time password and token verification (`hmac.compare_digest`)
- Server-side session security: idle timeout, absolute lifetime expiration,
  User-Agent fingerprint binding, and password-hash fingerprint invalidation
- Optional IP / CIDR network restriction (`ADMIN_ALLOWED_IPS`) supporting Tailscale VPN (`100.64.0.0/10`)
- Immutable Admin Audit Logging (`admin_audit_logs`)
- Session-backed CSRF token generation, rotation, and verification
- Database-backed login rate limiting per IP address & username AND public RSVP spam rate limiting
- Input sanitization, HTML/script block stripping, CRLF-safe `.ics` sanitization, open-redirect prevention,
  slug validation, URL validation, YouTube video ID extraction, and hex color validation
- Strict file upload security: extension allowlist, per-role size caps, magic-byte / MIME verification,
  SVG/HTML/polyglot rejection, Pillow decompression-bomb defense (`MAX_IMAGE_PIXELS`), dimension limits,
  path traversal protection, and WebP re-encoding
- Production Security HTTP headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, strict CORS)
"""

from __future__ import annotations

import base64
import functools
import hashlib
import hmac
import io
import ipaddress
import json
import os
import re
import secrets
import time
import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from PIL import Image, ImageOps

from .database import get_db
from .flask_compat import (
    Response,
    abort,
    current_app,
    flash,
    g,
    redirect,
    request,
    secure_filename,
    session,
    url_for,
)

# Guard against decompression bomb attacks (~25 Megapixels max)
Image.MAX_IMAGE_PIXELS = 25_000_000

# Optional Argon2 / bcrypt support
try:
    from argon2 import PasswordHasher as _Argon2Hasher  # type: ignore
    _ARGON2 = _Argon2Hasher()
except ImportError:
    _ARGON2 = None

try:
    import bcrypt as _bcrypt  # type: ignore
except ImportError:
    _bcrypt = None

try:
    import magic as _magic  # type: ignore
except ImportError:
    _magic = None


# =============================================================================
# 1. PASSWORD HASHING & VERIFICATION
# =============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using Argon2id (if installed), bcrypt (if installed),
    or cryptographic scrypt (RFC 7914 built into Python's ssl/hashlib).
    """
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")

    if _ARGON2 is not None:
        return _ARGON2.hash(password)

    if _bcrypt is not None:
        salt = _bcrypt.gensalt(rounds=12)
        return _bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    salt_bytes = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt_bytes,
        n=16384,
        r=8,
        p=1,
        dklen=64,
    )
    salt_b64 = base64.b64encode(salt_bytes).decode("ascii")
    hash_b64 = base64.b64encode(derived).decode("ascii")
    return f"scrypt$16384$8$1${salt_b64}${hash_b64}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a plaintext password against a stored Argon2, bcrypt, scrypt, or PBKDF2 hash in constant time."""
    if not password or not stored_hash:
        return False

    try:
        if stored_hash.startswith("$argon2") and _ARGON2 is not None:
            return bool(_ARGON2.verify(stored_hash, password))

        if (stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$")) and _bcrypt is not None:
            return bool(_bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")))

        if stored_hash.startswith("scrypt$"):
            parts = stored_hash.split("$")
            if len(parts) != 6:
                return False
            _, n_str, r_str, p_str, salt_b64, hash_b64 = parts
            salt_bytes = base64.b64decode(salt_b64.encode("ascii"))
            expected = base64.b64decode(hash_b64.encode("ascii"))
            candidate = hashlib.scrypt(
                password.encode("utf-8"),
                salt=salt_bytes,
                n=int(n_str),
                r=int(r_str),
                p=int(p_str),
                dklen=len(expected),
            )
            return hmac.compare_digest(candidate, expected)

        if stored_hash.startswith("pbkdf2:"):
            header, salt, hex_digest = stored_hash.split("$", 2)
            h_parts = header.split(":")
            iterations = int(h_parts[2]) if len(h_parts) >= 3 else 310_000
            dk = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                iterations,
            )
            return hmac.compare_digest(dk.hex(), hex_digest)
    except Exception:
        return False

    return False


def password_fingerprint(password_hash: str) -> str:
    """Short non-reversible fingerprint of a password hash used to invalidate old sessions on password change."""
    return hashlib.sha256((password_hash or "").encode("utf-8")).hexdigest()[:24]


def user_agent_fingerprint() -> str:
    """Short fingerprint of the client's User-Agent string."""
    ua = (request.headers.get("User-Agent", "") or "")[:300]
    return hashlib.sha256(ua.encode("utf-8")).hexdigest()[:24]


# =============================================================================
# 2. CLIENT IP, ADMIN NETWORK RESTRICTION (`ADMIN_ALLOWED_IPS` / TAILSCALE) & AUDIT LOGS
# =============================================================================

def get_client_ip() -> str:
    """
    Safely resolve the real client IP address behind Render / Cloudflare reverse proxies
    when TRUST_PROXY_HEADERS is enabled.
    """
    if current_app.config.get("TRUST_PROXY_HEADERS", True):
        cf_ip = request.headers.get("CF-Connecting-IP", "").strip()
        if cf_ip and len(cf_ip) <= 64:
            return cf_ip
        xff = request.headers.get("X-Forwarded-For", "").strip()
        if xff:
            first_ip = xff.split(",")[0].strip()
            if first_ip and len(first_ip) <= 64:
                return first_ip
    return (request.remote_addr or "127.0.0.1")[:64]


def is_ip_allowed_for_admin(ip_str: str) -> bool:
    """
    Verify whether `ip_str` is allowed to access `/admin` when `ADMIN_ALLOWED_IPS` is configured.
    - If `ADMIN_ALLOWED_IPS` is empty (default), returns True so mobile cellular IPs work.
    - Supports single IPs (`127.0.0.1`) and CIDR blocks (e.g., Tailscale VPN `100.64.0.0/10`).
    """
    raw_allowed = current_app.config.get("ADMIN_ALLOWED_IPS") or []
    if isinstance(raw_allowed, str):
        allowed_list = [x.strip() for x in raw_allowed.split(",") if x.strip()]
    else:
        allowed_list = [str(x).strip() for x in raw_allowed if str(x).strip()]

    if not allowed_list:
        return True

    try:
        client_ip = ipaddress.ip_address(ip_str.strip())
    except ValueError:
        return False

    for rule in allowed_list:
        try:
            if "/" in rule:
                if client_ip in ipaddress.ip_network(rule, strict=False):
                    return True
            else:
                if client_ip == ipaddress.ip_address(rule):
                    return True
        except ValueError:
            continue
    return False


def log_admin_action(
    action: str,
    target_type: str = "",
    target_id: str = "",
    details: Optional[Dict[str, Any]] = None,
    admin_user_id: Optional[int] = None,
    admin_username: Optional[str] = None,
) -> None:
    """Record an immutable security audit log entry in `admin_audit_logs`."""
    try:
        db = get_db()
        uid = admin_user_id if admin_user_id is not None else session.get("admin_user_id")
        uname = admin_username if admin_username is not None else (session.get("admin_username") or "")
        ip_addr = get_client_ip()
        ua = (request.headers.get("User-Agent", "") or "")[:250]
        details_str = json.dumps(details or {}, ensure_ascii=False)
        db.insert(
            """
            INSERT INTO admin_audit_logs (
                admin_user_id, admin_username, action, target_type, target_id,
                ip_address, user_agent, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(uid) if uid is not None else None,
                str(uname)[:120],
                str(action)[:120],
                str(target_type)[:80],
                str(target_id)[:120],
                ip_addr,
                ua,
                details_str,
            ),
        )
    except Exception:
        pass


# =============================================================================
# 3. CSRF PROTECTION
# =============================================================================

def generate_csrf_token() -> str:
    """Generate or retrieve the current session's CSRF token."""
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)
    return str(session["_csrf_token"])


def rotate_csrf_token() -> str:
    """Rotate the session's CSRF token upon authentication privilege changes."""
    session["_csrf_token"] = secrets.token_urlsafe(32)
    return str(session["_csrf_token"])


def verify_csrf_token() -> None:
    """Validate CSRF token on state-changing requests (POST, PUT, PATCH, DELETE)."""
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return

    expected = session.get("_csrf_token")
    provided = (
        request.form.get("csrf_token")
        or request.headers.get("X-CSRF-Token")
        or (request.get_json(silent=True) or {}).get("csrf_token")
    )

    if not expected or not provided or not hmac.compare_digest(str(expected), str(provided)):
        log_admin_action("csrf_validation_failed", target_type="endpoint", target_id=request.path)
        abort(403, "CSRF validation failed. Please refresh the page and try again.")


# =============================================================================
# 4. AUTHENTICATION, SESSION EXPIRATION & AUTHORIZATION DECORATORS
# =============================================================================

def start_admin_session(user_row: Dict[str, Any]) -> None:
    """Initialize a hardened, time-bounded, fingerprinted admin session."""
    now = int(time.time())
    session.clear()
    try:
        session.permanent = True
    except AttributeError:
        pass
    session["admin_user_id"] = int(user_row["id"])
    session["admin_username"] = str(user_row["username"])
    session["admin_role"] = str(user_row.get("role") or "admin")
    session["admin_pw_fp"] = password_fingerprint(str(user_row.get("password_hash") or ""))
    session["session_issued_at"] = now
    session["session_last_activity"] = now
    session["session_ua_hash"] = user_agent_fingerprint()
    rotate_csrf_token()
    g.current_admin = None


def get_current_admin() -> Optional[Dict[str, Any]]:
    """
    Fetch currently authenticated admin user from session and enforce:
    1. Network IP / Tailscale CIDR allowlist (`ADMIN_ALLOWED_IPS`)
    2. Session absolute lifetime (`PERMANENT_SESSION_LIFETIME_SECONDS`) & idle timeout (`ADMIN_SESSION_IDLE_TIMEOUT_SECONDS`)
    3. User-Agent fingerprint consistency (`session_ua_hash`)
    4. Active DB user status (`is_active`), `role == 'admin'`, and password-hash fingerprint (`admin_pw_fp`)
    """
    if hasattr(g, "current_admin") and g.current_admin is not None:
        return g.current_admin

    if not is_ip_allowed_for_admin(get_client_ip()):
        g.current_admin = None
        return None

    admin_id = session.get("admin_user_id")
    if not admin_id:
        g.current_admin = None
        return None

    now = int(time.time())
    max_lifetime = int(current_app.config.get("PERMANENT_SESSION_LIFETIME_SECONDS", 28800))
    idle_timeout = int(current_app.config.get("ADMIN_SESSION_IDLE_TIMEOUT_SECONDS", 1800))

    issued_at = session.get("session_issued_at")
    if issued_at is not None and (now - int(issued_at)) > max_lifetime:
        session.clear()
        g.current_admin = None
        return None

    last_activity = session.get("session_last_activity")
    if last_activity is not None and (now - int(last_activity)) > idle_timeout:
        session.clear()
        g.current_admin = None
        return None

    expected_ua = session.get("session_ua_hash")
    if expected_ua and expected_ua != user_agent_fingerprint():
        session.clear()
        g.current_admin = None
        return None

    db = get_db()
    user = db.fetchone(
        "SELECT id, username, email, role, is_active, password_hash FROM users WHERE id = ?",
        (int(admin_id),),
    )
    if not user or not user.get("is_active") or user.get("role") != "admin":
        session.clear()
        g.current_admin = None
        return None

    expected_pw_fp = session.get("admin_pw_fp")
    actual_pw_fp = password_fingerprint(str(user.get("password_hash") or ""))
    if expected_pw_fp and not hmac.compare_digest(str(expected_pw_fp), actual_pw_fp):
        session.clear()
        g.current_admin = None
        return None

    session["session_last_activity"] = now
    safe_user = {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "is_active": user["is_active"],
    }
    g.current_admin = safe_user
    return safe_user


def admin_required(view_func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator protecting admin routes from unauthenticated, unauthorized, or IP-restricted access."""
    @functools.wraps(view_func)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        client_ip = get_client_ip()
        if not is_ip_allowed_for_admin(client_ip):
            log_admin_action("admin_ip_blocked", target_type="path", target_id=request.path)
            abort(403, "Access to Admin Studio is restricted from your current IP address.")

        admin = get_current_admin()
        if not admin or admin.get("role") != "admin":
            if request.is_json or request.path.startswith("/admin/api/"):
                return {"error": "Authentication required", "status": 401}, 401
            flash("Please sign in to access the Bikozava admin studio.", "warning")
            return redirect(url_for("admin.login", next=request.path))

        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            verify_csrf_token()

        return view_func(*args, **kwargs)

    return wrapped


# =============================================================================
# 5. LOGIN & RSVP RATE LIMITING
# =============================================================================

def is_login_rate_limited(ip_address: str, username: str = "") -> Tuple[bool, int]:
    """
    Check if the given IP address or username has exceeded allowed failed login attempts
    within the configured time window.
    Returns (is_blocked, retry_after_seconds).
    """
    max_attempts = int(current_app.config.get("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", 5))
    window_sec = int(current_app.config.get("LOGIN_RATE_LIMIT_WINDOW_SECONDS", 300))
    cutoff_dt = datetime.now(timezone.utc) - timedelta(seconds=window_sec)
    cutoff_str = cutoff_dt.strftime("%Y-%m-%d %H:%M:%S")

    db = get_db()
    if username:
        row = db.fetchone(
            """
            SELECT COUNT(*) AS cnt
            FROM login_attempts
            WHERE (ip_address = ? OR LOWER(username) = LOWER(?))
              AND succeeded = FALSE
              AND attempted_at >= ?
            """,
            (ip_address, username[:120], cutoff_str),
        )
    else:
        row = db.fetchone(
            """
            SELECT COUNT(*) AS cnt
            FROM login_attempts
            WHERE ip_address = ? AND succeeded = FALSE AND attempted_at >= ?
            """,
            (ip_address, cutoff_str),
        )
    failed_count = int((row or {}).get("cnt", 0))
    if failed_count >= max_attempts:
        return True, window_sec
    return False, 0


def record_login_attempt(ip_address: str, username: str, succeeded: bool) -> None:
    """Record a login attempt and clear previous failures on success."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    if succeeded:
        db.execute(
            "DELETE FROM login_attempts WHERE (ip_address = ? OR LOWER(username) = LOWER(?)) AND succeeded = FALSE",
            (ip_address, (username or "")[:120]),
        )
    db.insert(
        "INSERT INTO login_attempts (ip_address, username, succeeded, attempted_at) VALUES (?, ?, ?, ?)",
        (ip_address[:64], (username or "")[:120], bool(succeeded), now_str),
    )


def is_rsvp_rate_limited(invitation_id: int, ip_hash: str) -> bool:
    """Prevent automated RSVP spam from a single IP (configurable via RSVP_RATE_LIMIT_MAX_ATTEMPTS)."""
    max_attempts = int(current_app.config.get("RSVP_RATE_LIMIT_MAX_ATTEMPTS", 10))
    window_sec = int(current_app.config.get("RSVP_RATE_LIMIT_WINDOW_SECONDS", 3600))
    cutoff_dt = datetime.now(timezone.utc) - timedelta(seconds=window_sec)
    cutoff_str = cutoff_dt.strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    row = db.fetchone(
        """
        SELECT COUNT(*) AS cnt
        FROM rsvp_responses
        WHERE invitation_id = ? AND ip_hash = ? AND created_at >= ?
        """,
        (invitation_id, ip_hash, cutoff_str),
    )
    return int((row or {}).get("cnt", 0)) >= max_attempts


# =============================================================================
# 6. INPUT VALIDATION, YOUTUBE PARSING & SANITIZATION
# =============================================================================

RESERVED_SLUGS = {
    "admin",
    "static",
    "login",
    "logout",
    "api",
    "health",
    "healthz",
    "favicon.ico",
    "robots.txt",
    "preview",
    "templates",
    "home",
    "uploads",
    "rsvp",
}

SLUG_REGEX = re.compile(r"^[a-z0-9]+(?:[_-][a-z0-9]+)*$")
HEX_COLOR_REGEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
YOUTUBE_ID_REGEX = re.compile(
    r"(?:youtube\.com/(?:watch\?.*v=|embed/|shorts/|v/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SCRIPT_STYLE_BLOCK_RE = re.compile(r"<(script|style|iframe|object|embed|svg)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]*>")
_PHONE_CLEAN_RE = re.compile(r"[^\d+\-\s()]")


def extract_youtube_video_id(raw_url_or_id: str) -> str:
    """
    Safely extract an 11-character YouTube video ID from any YouTube URL
    (`https://www.youtube.com/watch?v=...`, `https://youtu.be/...`, `https://www.youtube.com/embed/...`)
    or bare 11-char ID. Returns '' if invalid.
    """
    s = (raw_url_or_id or "").strip()
    if not s:
        return ""
    if re.match(r"^[A-Za-z0-9_-]{11}$", s):
        return s
    m = YOUTUBE_ID_REGEX.search(s)
    if m:
        return m.group(1)
    return ""


def sanitize_slug(raw_slug: str, groom_en: str = "", bride_en: str = "") -> str:
    """
    Normalize and validate a URL slug so it is strictly lowercase alphanumeric
    with underscores or hyphens (e.g., `ismail_shrin`, `ahmad_lavin`).
    """
    candidate = (raw_slug or "").strip().lower()
    if not candidate and (groom_en or bride_en):
        candidate = f"{groom_en}_{bride_en}".strip().lower()

    candidate = re.sub(r"[^a-z0-9_-]+", "_", candidate)
    candidate = re.sub(r"[_-]+", "_", candidate).strip("_-")

    if not candidate or len(candidate) < 2:
        candidate = f"wedding_{secrets.token_hex(3)}"

    if len(candidate) > 80:
        candidate = candidate[:80].rstrip("_-")

    if candidate in RESERVED_SLUGS:
        candidate = f"{candidate}_wedding"

    return candidate


def is_valid_slug(slug: str) -> bool:
    """Return True if slug is safe, non-reserved, and matches strict pattern."""
    if not slug or len(slug) > 100 or slug in RESERVED_SLUGS:
        return False
    return bool(SLUG_REGEX.match(slug))


def clean_text(val: Any, max_len: int = 2000, strip_html: bool = False) -> str:
    """Strip control characters (and optionally HTML/script tags) and enforce length limits while preserving Kurdish/Arabic script."""
    if val is None:
        return ""
    s = _CONTROL_CHARS_RE.sub("", str(val)).strip()
    if strip_html:
        s = _SCRIPT_STYLE_BLOCK_RE.sub("", s)
        s = _HTML_TAG_RE.sub("", s).replace("<", "").replace(">", "").strip()
    return s[:max_len]


def clean_phone(val: Any, max_len: int = 50) -> str:
    """Sanitize a guest phone number to digits, '+', '-', spaces, and parentheses."""
    s = clean_text(val, max_len=max_len, strip_html=True)
    return _PHONE_CLEAN_RE.sub("", s).strip()[:max_len]


def clean_ics_text(val: Any, max_len: int = 240) -> str:
    """Sanitize text for iCalendar (.ics) responses, preventing CRLF header/property injection."""
    s = clean_text(val, max_len=max_len, strip_html=True)
    return s.replace("\r", " ").replace("\n", " ").replace(";", "\\;").replace(",", "\\,")


def is_safe_admin_redirect(target_url: Any) -> bool:
    """Verify that a redirect URL is strictly a local `/admin...` path on the same host (blocks Open Redirects)."""
    if not target_url or not isinstance(target_url, str):
        return False
    target = target_url.strip()
    if target.startswith("//") or target.startswith("\\") or "\r" in target or "\n" in target:
        return False
    parsed = urllib.parse.urlsplit(target)
    if parsed.scheme or parsed.netloc:
        if parsed.netloc != request.host:
            return False
    return parsed.path.startswith("/admin")


def clean_color(val: Any, default: str = "#C8A253") -> str:
    """Validate 6-digit hex color code."""
    s = str(val or "").strip()
    if HEX_COLOR_REGEX.match(s):
        return s.upper()
    return default


def clean_url(val: Any, allow_relative: bool = False) -> str:
    """Validate URL to prevent `javascript:`, `vbscript:`, `file:`, or `data:` XSS injection."""
    s = str(val or "").strip()
    if not s:
        return ""
    s = _CONTROL_CHARS_RE.sub("", s)
    if allow_relative and s.startswith("/static/"):
        if ".." in s or "\\" in s or s.startswith("//"):
            return ""
        return s
    parsed = urllib.parse.urlsplit(s)
    if parsed.scheme.lower() in ("http", "https") and parsed.netloc:
        return s[:1000]
    return ""


# =============================================================================
# 7. SECURE FILE UPLOAD & IMAGE OPTIMIZATION
# =============================================================================

SAFE_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}
SAFE_AUDIO_MIMES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/ogg",
    "audio/mp4",
    "audio/x-m4a",
}
SAFE_VIDEO_MIMES = {"video/mp4", "video/webm"}


def detect_mime_type(data: bytes, filename: str) -> str:
    """Inspect magic bytes of uploaded file content to verify real file type and reject polyglot XSS payloads."""
    header = data[:4096]
    header_lower = header.lower()
    if header.startswith((b"MZ", b"\x7fELF", b"#!/")):
        return "application/x-executable"
    for sig in (b"<?php", b"<script", b"<svg", b"<!doctype html", b"<html", b"onload=", b"onerror=", b"javascript:"):
        if sig in header_lower:
            return "application/x-executable"

    if _magic is not None:
        try:
            detected = _magic.from_buffer(data[:2048], mime=True)
            if detected:
                det_str = str(detected).lower()
                if "svg" in det_str or "html" in det_str or "xml" in det_str or "script" in det_str:
                    return "application/x-executable"
                return det_str
        except Exception:
            pass

    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if data[:3] == b"ID3" or (len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
        return "audio/mpeg"
    if data[:4] == b"OggS":
        return "audio/ogg"
    if len(data) > 12 and data[4:8] == b"ftyp":
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return "audio/mp4" if ext == "m4a" else "video/mp4"
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm"

    return "application/octet-stream"


def validate_and_store_upload(
    file_storage: Any,
    media_role: str,
) -> Dict[str, Any]:
    """
    Securely validate, sanitize, optimize, and store an uploaded image, audio, or video file.
    Raises ValueError with a user-safe message if validation fails.
    """
    if not file_storage or not getattr(file_storage, "filename", ""):
        raise ValueError("No file provided.")

    raw_filename = str(file_storage.filename)
    if "\x00" in raw_filename:
        raise ValueError("Invalid filename.")

    orig_name = secure_filename(Path(raw_filename.replace("\\", "/")).name)
    if not orig_name or "." not in orig_name:
        raise ValueError("File must have a valid extension.")

    ext = orig_name.rsplit(".", 1)[-1].lower()
    raw_bytes = file_storage.read()
    file_size = len(raw_bytes)

    if file_size == 0:
        raise ValueError("Uploaded file is empty.")

    max_bytes = int(current_app.config.get("MAX_CONTENT_LENGTH", 25 * 1024 * 1024))
    if file_size > max_bytes:
        raise ValueError("File exceeds maximum allowed size.")

    detected_mime = detect_mime_type(raw_bytes, orig_name)
    if detected_mime == "application/x-executable":
        raise ValueError("Executable, SVG, HTML, or script files are strictly prohibited.")

    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    unique_id = uuid.uuid4().hex[:16]

    if media_role in ("bride", "groom", "couple", "gallery", "background", "logo"):
        max_img_bytes = int(current_app.config.get("MAX_IMAGE_UPLOAD_BYTES", 10 * 1024 * 1024))
        if file_size > max_img_bytes:
            raise ValueError("Image file exceeds the 10 MB maximum size.")

        allowed_exts = current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
        if ext not in allowed_exts or detected_mime not in SAFE_IMAGE_MIMES:
            raise ValueError("Invalid image format. Allowed formats: JPG, PNG, WEBP.")

        max_dim_limit = int(current_app.config.get("MAX_IMAGE_DIMENSION_PX", 6000))
        try:
            with Image.open(io.BytesIO(raw_bytes)) as verify_img:
                verify_img.verify()
            img = Image.open(io.BytesIO(raw_bytes))
            w, h = img.size
            if w <= 0 or h <= 0 or w > max_dim_limit or h > max_dim_limit:
                raise ValueError(f"Image dimensions ({w}x{h}) exceed the {max_dim_limit}x{max_dim_limit}px limit.")
            img = ImageOps.exif_transpose(img)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("Corrupted or invalid image file.") from exc

        subdir = "avatars" if media_role in ("bride", "groom", "couple", "logo") else "gallery"
        stored_name = f"{media_role}_{unique_id}.webp"
        thumb_name = f"{media_role}_{unique_id}_thumb.webp"

        target_dir = (upload_root / subdir).resolve()
        thumb_dir = (upload_root / "thumbs").resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        thumb_dir.mkdir(parents=True, exist_ok=True)

        full_dest = (target_dir / stored_name).resolve()
        thumb_dest = (thumb_dir / thumb_name).resolve()

        if not str(full_dest).startswith(str(upload_root)) or not str(thumb_dest).startswith(str(upload_root)):
            raise ValueError("Invalid upload destination.")

        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        main_img = img.copy()
        main_img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        main_img.save(full_dest, format="WEBP", quality=86, method=4)

        thumb_img = img.copy()
        thumb_img.thumbnail((480, 480), Image.Resampling.LANCZOS)
        thumb_img.save(thumb_dest, format="WEBP", quality=80, method=4)

        return {
            "original_filename": orig_name,
            "stored_filename": stored_name,
            "file_path": f"/static/uploads/{subdir}/{stored_name}",
            "thumb_path": f"/static/uploads/thumbs/{thumb_name}",
            "mime_type": "image/webp",
            "file_size": full_dest.stat().st_size,
        }

    elif media_role == "music":
        max_audio_bytes = int(current_app.config.get("MAX_AUDIO_UPLOAD_BYTES", 15 * 1024 * 1024))
        if file_size > max_audio_bytes:
            raise ValueError("Audio file exceeds the 15 MB maximum size.")

        allowed_exts = current_app.config["ALLOWED_AUDIO_EXTENSIONS"]
        if ext not in allowed_exts or detected_mime not in SAFE_AUDIO_MIMES:
            raise ValueError("Invalid audio file. Allowed formats: MP3, WAV, OGG, M4A.")

        stored_name = f"music_{unique_id}.{ext}"
        target_dir = (upload_root / "music").resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        full_dest = (target_dir / stored_name).resolve()
        if not str(full_dest).startswith(str(upload_root)):
            raise ValueError("Invalid upload destination.")

        full_dest.write_bytes(raw_bytes)
        return {
            "original_filename": orig_name,
            "stored_filename": stored_name,
            "file_path": f"/static/uploads/music/{stored_name}",
            "thumb_path": "",
            "mime_type": detected_mime,
            "file_size": file_size,
        }

    elif media_role == "video":
        max_video_bytes = int(current_app.config.get("MAX_VIDEO_UPLOAD_BYTES", 25 * 1024 * 1024))
        if file_size > max_video_bytes:
            raise ValueError("Video file exceeds the 25 MB maximum size.")

        allowed_exts = current_app.config["ALLOWED_VIDEO_EXTENSIONS"]
        if ext not in allowed_exts or detected_mime not in SAFE_VIDEO_MIMES:
            raise ValueError("Invalid video file. Allowed formats: MP4, WEBM.")

        stored_name = f"video_{unique_id}.{ext}"
        target_dir = (upload_root / "video").resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        full_dest = (target_dir / stored_name).resolve()
        if not str(full_dest).startswith(str(upload_root)):
            raise ValueError("Invalid upload destination.")

        full_dest.write_bytes(raw_bytes)
        return {
            "original_filename": orig_name,
            "stored_filename": stored_name,
            "file_path": f"/static/uploads/video/{stored_name}",
            "thumb_path": "",
            "mime_type": detected_mime,
            "file_size": file_size,
        }

    raise ValueError("Unsupported media role.")


# =============================================================================
# 8. HTTP SECURITY HEADERS (CSP + HSTS + Clickjacking + MIME Sniffing + Strict CORS)
# =============================================================================

def apply_security_headers(response: Response) -> Response:
    """Attach production-grade security headers and strict CORS policy to every HTTP response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=(), payment=(), usb=(), "
        "autoplay=(self \"https://www.youtube.com\")"
    )

    # Strict CORS Allowlist (never reflect arbitrary Origin or '*')
    origin = (request.headers.get("Origin") or "").strip().rstrip("/")
    if origin:
        allowed_origins = current_app.config.get("CORS_ALLOWED_ORIGINS") or set()
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-CSRF-Token"

    if (
        current_app.config.get("SESSION_COOKIE_SECURE")
        or current_app.config.get("FLASK_ENV") == "production"
        or request.headers.get("X-Forwarded-Proto") == "https"
    ):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

    if request.path.startswith("/admin"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"

    csp = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: https: https://i.ytimg.com; "
        "media-src 'self' data: blob:; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://www.youtube.com https://s.ytimg.com; "
        "frame-src 'self' https://www.google.com https://maps.google.com https://www.youtube.com https://www.youtube-nocookie.com; "
        "frame-ancestors 'self'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "object-src 'none';"
    )
    response.headers["Content-Security-Policy"] = csp
    return response
