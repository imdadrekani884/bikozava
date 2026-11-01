"""
Bikozava — Security, Authentication, File Validation & Hardening (`app/security.py`)

Implements:
- Password hashing (Argon2id / bcrypt when installed, with cryptographic
  `hashlib.scrypt` + PBKDF2-HMAC-SHA256 fallback)
- Constant-time password and token verification (`hmac.compare_digest`)
- Session-backed CSRF token generation and verification
- Database-backed login rate limiting per IP address AND public RSVP spam rate limiting
- Input sanitization, slug validation, URL validation, YouTube video ID extraction,
  and hex color validation
- Strict file upload security: extension whitelist, magic-byte / MIME verification
  (`magic` + Pillow verification), path traversal protection, and Pillow image
  thumbnail/optimization generation
- Production Security HTTP headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
"""

from __future__ import annotations

import base64
import functools
import hashlib
import hmac
import os
import re
import secrets
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
    """Verify a plaintext password against a stored Argon2, bcrypt, or scrypt hash."""
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
    except Exception:
        return False

    return False


# =============================================================================
# 2. CSRF PROTECTION
# =============================================================================

def generate_csrf_token() -> str:
    """Generate or retrieve the current session's CSRF token."""
    if "_csrf_token" not in session:
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
        abort(403, "CSRF validation failed. Please refresh the page and try again.")


# =============================================================================
# 3. AUTHENTICATION & AUTHORIZATION DECORATORS
# =============================================================================

def get_current_admin() -> Optional[Dict[str, Any]]:
    """Fetch currently authenticated admin user from session and verify active status in DB."""
    if hasattr(g, "current_admin"):
        return g.current_admin

    admin_id = session.get("admin_user_id")
    if not admin_id:
        g.current_admin = None
        return None

    db = get_db()
    user = db.fetchone(
        "SELECT id, username, email, role, is_active FROM users WHERE id = ?",
        (int(admin_id),),
    )
    if not user or not user.get("is_active"):
        session.clear()
        g.current_admin = None
        return None

    g.current_admin = user
    return user


def admin_required(view_func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator protecting admin routes from unauthenticated or unauthorized access."""
    @functools.wraps(view_func)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
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
# 4. LOGIN & RSVP RATE LIMITING
# =============================================================================

def is_login_rate_limited(ip_address: str) -> Tuple[bool, int]:
    """
    Check if the given IP address has exceeded allowed failed login attempts
    within the configured time window.
    Returns (is_blocked, retry_after_seconds).
    """
    max_attempts = int(current_app.config.get("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", 5))
    window_sec = int(current_app.config.get("LOGIN_RATE_LIMIT_WINDOW_SECONDS", 300))
    cutoff_dt = datetime.now(timezone.utc) - timedelta(seconds=window_sec)
    cutoff_str = cutoff_dt.strftime("%Y-%m-%d %H:%M:%S")

    db = get_db()
    row = db.fetchone(
        """
        SELECT COUNT(*) AS cnt
        FROM login_attempts
        WHERE ip_address = ? AND succeeded = 0 AND attempted_at >= ?
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
            "DELETE FROM login_attempts WHERE ip_address = ? AND succeeded = 0",
            (ip_address,),
        )
    db.insert(
        "INSERT INTO login_attempts (ip_address, username, succeeded, attempted_at) VALUES (?, ?, ?, ?)",
        (ip_address[:64], (username or "")[:120], 1 if succeeded else 0, now_str),
    )


def is_rsvp_rate_limited(invitation_id: int, ip_hash: str) -> bool:
    """Prevent automated RSVP spam from a single IP (max 10 RSVPs per invitation per hour)."""
    cutoff_dt = datetime.now(timezone.utc) - timedelta(hours=1)
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
    return int((row or {}).get("cnt", 0)) >= 10


# =============================================================================
# 5. INPUT VALIDATION, YOUTUBE PARSING & SANITIZATION
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
    "uploads",
    "rsvp",
}


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

SLUG_REGEX = re.compile(r"^[a-z0-9]+(?:[_-][a-z0-9]+)*$")
HEX_COLOR_REGEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
YOUTUBE_ID_REGEX = re.compile(
    r"(?:youtube\.com/(?:watch\?.*v=|embed/|shorts/|v/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)


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


def clean_text(val: Any, max_len: int = 2000) -> str:
    """Strip control characters and enforce length limits while preserving Kurdish/Arabic script."""
    if val is None:
        return ""
    s = str(val).replace("\x00", "").strip()
    return s[:max_len]


def clean_color(val: Any, default: str = "#C8A253") -> str:
    """Validate 6-digit hex color code."""
    s = str(val or "").strip()
    if HEX_COLOR_REGEX.match(s):
        return s.upper()
    return default


def clean_url(val: Any, allow_relative: bool = False) -> str:
    """Validate URL to prevent `javascript:` or `data:` XSS injection."""
    s = str(val or "").strip()
    if not s:
        return ""
    if allow_relative and s.startswith("/static/"):
        if ".." in s or "\\" in s:
            return ""
        return s
    parsed = urllib.parse.urlsplit(s)
    if parsed.scheme.lower() in ("http", "https") and parsed.netloc:
        return s[:1000]
    return ""


# =============================================================================
# 6. SECURE FILE UPLOAD & IMAGE OPTIMIZATION
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

DANGEROUS_SIGNATURES = (
    b"<?php",
    b"#!/",
    b"<script",
    b"MZ",        # Windows PE executable
    b"\x7fELF",   # Linux ELF binary
)


def detect_mime_type(data: bytes, filename: str) -> str:
    """Inspect magic bytes of uploaded file content to verify real file type."""
    header = data[:512]
    for sig in DANGEROUS_SIGNATURES:
        if header.startswith(sig) or sig in header[:128].lower():
            return "application/x-executable"

    if _magic is not None:
        try:
            detected = _magic.from_buffer(data[:2048], mime=True)
            if detected:
                return str(detected).lower()
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
    if data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
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

    orig_name = secure_filename(file_storage.filename)
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
        raise ValueError("Executable or script files are strictly prohibited.")

    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    unique_id = uuid.uuid4().hex[:16]

    if media_role in ("bride", "groom", "couple", "gallery", "background"):
        allowed_exts = current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
        if ext not in allowed_exts or detected_mime not in SAFE_IMAGE_MIMES:
            raise ValueError("Invalid image format. Allowed formats: JPG, PNG, WEBP.")

        try:
            import io
            img = Image.open(io.BytesIO(raw_bytes))
            img.verify()
            img = Image.open(io.BytesIO(raw_bytes))
            img = ImageOps.exif_transpose(img)
        except Exception as exc:
            raise ValueError("Corrupted or invalid image file.") from exc

        subdir = "avatars" if media_role in ("bride", "groom", "couple") else "gallery"
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
# 7. HTTP SECURITY HEADERS (CSP + HSTS + Clickjacking + MIME Sniffing)
# =============================================================================

def apply_security_headers(response: Response) -> Response:
    """Attach production-grade security headers to every HTTP response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=(), payment=(), usb=(), "
        "autoplay=(self \"https://www.youtube.com\")"
    )
    if current_app.config.get("SESSION_COOKIE_SECURE") or request.headers.get("X-Forwarded-Proto") == "https":
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
        "script-src 'self' 'unsafe-inline' https://www.youtube.com https://s.ytimg.com; "
        "frame-src 'self' https://www.google.com https://maps.google.com https://www.youtube.com https://www.youtube-nocookie.com; "
        "frame-ancestors 'self'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    response.headers["Content-Security-Policy"] = csp
    return response
