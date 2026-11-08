"""
Bikozava — Application Configuration (`app/config.py`)
Loads environment variables from `.env` and provides secure defaults for
Supabase PostgreSQL (`rgshkpvhttjdbkycuesv`) and local SQLite development.
Never hardcodes production credentials.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

BASE_DIR = Path(__file__).resolve().parent.parent
if load_dotenv is not None:
    load_dotenv(BASE_DIR / ".env")


def _parse_csv_list(raw: str) -> List[str]:
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


def _parse_origins(raw: str) -> Set[str]:
    return {
        item.strip().rstrip("/")
        for item in (raw or "").split(",")
        if item.strip() and item.strip() != "*"
    }


class Config:
    """Base configuration loaded from environment variables."""

    APP_NAME: str = os.getenv("APP_NAME", "Bikozava")
    FLASK_ENV: str = os.getenv("FLASK_ENV", "production")
    DEBUG: bool = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "True") and os.getenv("FLASK_ENV", "production") != "production"
    TESTING: bool = False

    # Secret key generated dynamically in dev if not set in .env; required in production
    _raw_secret: str = os.getenv("SECRET_KEY", "").strip()
    SECRET_KEY: str = (
        _raw_secret
        if (_raw_secret and _raw_secret != "replace_with_a_64_char_hex_secret_generated_via_secrets_token_hex")
        else secrets.token_hex(32)
    )

    PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "https://bikozava.com").rstrip("/")

    # Database: Supports PostgreSQL/Supabase (postgresql://...) and SQLite (sqlite:///...)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'instance' / 'bikozava.db'}",
    )

    # Supabase Project Configuration (Server-side only — never exposed to browser)
    SUPABASE_PROJECT_REF: str = os.getenv("SUPABASE_PROJECT_REF", "rgshkpvhttjdbkycuesv")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://rgshkpvhttjdbkycuesv.supabase.co")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_STORAGE_BUCKET: str = os.getenv("SUPABASE_STORAGE_BUCKET", "wedding-media")

    # Initial bootstrap admin credentials (read from .env; unified with .env.example)
    ADMIN_INITIAL_USERNAME: str = os.getenv("ADMIN_INITIAL_USERNAME", "admin")
    ADMIN_INITIAL_EMAIL: str = os.getenv("ADMIN_INITIAL_EMAIL", "admin@bikozava.com")
    ADMIN_INITIAL_PASSWORD: str = os.getenv("ADMIN_INITIAL_PASSWORD", "ChangeThisStrongPassword!2026")
    FORCE_RESET_ADMIN_PASSWORD: bool = os.getenv("FORCE_RESET_ADMIN_PASSWORD", "0") in ("1", "true", "True")

    # Optional Admin Network Restriction (Single IPs or CIDR blocks such as Tailscale 100.64.0.0/10)
    # Empty by default so dynamic mobile cellular IPs are not locked out unless configured.
    ADMIN_ALLOWED_IPS: List[str] = _parse_csv_list(os.getenv("ADMIN_ALLOWED_IPS", ""))

    # Session & Cookie Hardening
    SESSION_COOKIE_NAME: str = "bikozava_session"
    SESSION_COOKIE_HTTPONLY: bool = os.getenv("SESSION_COOKIE_HTTPONLY", "1") in ("1", "true", "True")
    SESSION_COOKIE_SECURE: bool = os.getenv("SESSION_COOKIE_SECURE", "0") in ("1", "true", "True")
    SESSION_COOKIE_SAMESITE: str = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    TRUST_PROXY_HEADERS: bool = os.getenv("TRUST_PROXY_HEADERS", "1") in ("1", "true", "True")
    PERMANENT_SESSION_LIFETIME_SECONDS: int = int(os.getenv("PERMANENT_SESSION_LIFETIME_SECONDS", "28800"))
    ADMIN_SESSION_IDLE_TIMEOUT_SECONDS: int = int(os.getenv("ADMIN_SESSION_IDLE_TIMEOUT_SECONDS", "1800"))

    # Strict CORS Allowlist (never '*')
    CORS_ALLOWED_ORIGINS: Set[str] = _parse_origins(
        os.getenv(
            "CORS_ALLOWED_ORIGINS",
            "https://bikozava.com,https://www.bikozava.com,http://localhost:8000,http://127.0.0.1:8000",
        )
    )

    # Rate Limiting
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = int(os.getenv("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "5"))
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))
    RSVP_RATE_LIMIT_MAX_ATTEMPTS: int = int(os.getenv("RSVP_RATE_LIMIT_MAX_ATTEMPTS", "10"))
    RSVP_RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RSVP_RATE_LIMIT_WINDOW_SECONDS", "3600"))

    # File Uploads & Per-Role Security Bounds
    UPLOAD_FOLDER: str = str(BASE_DIR / "app" / "static" / "uploads")
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH_MB", "25")) * 1024 * 1024
    MAX_IMAGE_UPLOAD_BYTES: int = int(os.getenv("MAX_IMAGE_UPLOAD_MB", "10")) * 1024 * 1024
    MAX_AUDIO_UPLOAD_BYTES: int = int(os.getenv("MAX_AUDIO_UPLOAD_MB", "15")) * 1024 * 1024
    MAX_VIDEO_UPLOAD_BYTES: int = int(os.getenv("MAX_VIDEO_UPLOAD_MB", "25")) * 1024 * 1024
    MAX_IMAGE_DIMENSION_PX: int = int(os.getenv("MAX_IMAGE_DIMENSION_PX", "6000"))

    ALLOWED_IMAGE_EXTENSIONS = set(
        os.getenv("ALLOWED_IMAGE_EXTENSIONS", "jpg,jpeg,png,webp").lower().split(",")
    )
    ALLOWED_AUDIO_EXTENSIONS = set(
        os.getenv("ALLOWED_AUDIO_EXTENSIONS", "mp3,wav,ogg,m4a").lower().split(",")
    )
    ALLOWED_VIDEO_EXTENSIONS = set(
        os.getenv("ALLOWED_VIDEO_EXTENSIONS", "mp4,webm").lower().split(",")
    )

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        return {
            k: getattr(cls, k)
            for k in dir(cls)
            if k.isupper() and not k.startswith("_")
        }


def load_config(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = Config.to_dict()
    if overrides:
        cfg.update(overrides)
    return cfg
