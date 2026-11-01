"""
Bikozava — Application Configuration (`app/config.py`)
Loads environment variables from `.env` and provides secure defaults.
Never hardcodes production credentials.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base configuration loaded from environment variables."""

    APP_NAME: str = os.getenv("APP_NAME", "Bikozava")
    FLASK_ENV: str = os.getenv("FLASK_ENV", "production")
    DEBUG: bool = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "True")
    TESTING: bool = False

    # Secret key generated dynamically in dev if not set in .env; required in production
    SECRET_KEY: str = os.getenv("SECRET_KEY") or secrets.token_hex(32)

    PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "https://bikozava.com").rstrip("/")

    # Database: Supports PostgreSQL/Supabase (postgresql://...) and SQLite (sqlite:///...)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'instance' / 'bikozava.db'}",
    )

    # Optional Supabase Configuration (never exposed to browser)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_STORAGE_BUCKET: str = os.getenv("SUPABASE_STORAGE_BUCKET", "wedding-media")

    # Initial bootstrap admin credentials (read from .env; unified with .env.example)
    ADMIN_INITIAL_USERNAME: str = os.getenv("ADMIN_INITIAL_USERNAME", "admin")
    ADMIN_INITIAL_EMAIL: str = os.getenv("ADMIN_INITIAL_EMAIL", "admin@bikozava.com")
    ADMIN_INITIAL_PASSWORD: str = os.getenv("ADMIN_INITIAL_PASSWORD", "ChangeThisStrongPassword!2026")

    # Session & Cookie Hardening
    SESSION_COOKIE_NAME: str = "bikozava_session"
    SESSION_COOKIE_HTTPONLY: bool = os.getenv("SESSION_COOKIE_HTTPONLY", "1") in ("1", "true", "True")
    SESSION_COOKIE_SECURE: bool = os.getenv("SESSION_COOKIE_SECURE", "0") in ("1", "true", "True")
    SESSION_COOKIE_SAMESITE: str = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    TRUST_PROXY_HEADERS: bool = os.getenv("TRUST_PROXY_HEADERS", "1") in ("1", "true", "True")
    PERMANENT_SESSION_LIFETIME_SECONDS: int = int(os.getenv("PERMANENT_SESSION_LIFETIME_SECONDS", "28800"))

    # Rate Limiting
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = int(os.getenv("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "5"))
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))

    # File Uploads
    UPLOAD_FOLDER: str = str(BASE_DIR / "app" / "static" / "uploads")
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH_MB", "25")) * 1024 * 1024
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
