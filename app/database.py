"""
Bikozava — Unified Database Layer (`app/database.py`)
Supports:
  1. PostgreSQL / Supabase (`postgresql://...` or `postgres://...`) via `psycopg2`
  2. SQLite (`sqlite:///...`) via `sqlite3` for instant local runs and automated tests
     (fully cross-platform on Windows `C:\\...` drive paths, macOS, and Linux)

All queries use parameterized placeholders (`?` internally, automatically converted
to `%s` when running against PostgreSQL/Supabase) to guarantee 100% SQL injection
protection.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .flask_compat import current_app, g


class DatabaseAdapter:
    """Unified wrapper around PostgreSQL (psycopg2) and SQLite3 connections."""

    def __init__(self, database_url: str):
        # Automatically normalize legacy postgres:// scheme (used by Render/Heroku) to postgresql:// for psycopg2
        if database_url.startswith("postgres://"):
            database_url = "postgresql://" + database_url[len("postgres://"):]
        self.database_url = database_url
        self.is_postgres = database_url.startswith("postgresql://")
        self._conn: Any = None

    def connect(self) -> Any:
        if self._conn is not None:
            return self._conn

        if self.is_postgres:
            import psycopg2  # type: ignore
            import psycopg2.extras  # type: ignore

            self._conn = psycopg2.connect(
                self.database_url,
                cursor_factory=psycopg2.extras.RealDictCursor,
            )
            return self._conn
        else:
            raw_path = re.sub(r"^sqlite:(?:///)?", "", self.database_url)
            if raw_path != ":memory:":
                if re.match(r"^/[A-Za-z]:[/\\]", raw_path):
                    raw_path = raw_path[1:]
                db_path = Path(raw_path)
                if not db_path.is_absolute():
                    base_dir = Path(__file__).resolve().parent.parent
                    db_path = (base_dir / db_path).resolve()
                db_path.parent.mkdir(parents=True, exist_ok=True)
                target = str(db_path)
            else:
                target = ":memory:"

            conn = sqlite3.connect(target, detect_types=sqlite3.PARSE_DECLTYPES)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            self._conn = conn
            return self._conn

    def _prepare_sql(self, sql: str) -> str:
        if self.is_postgres:
            return sql.replace("?", "%s")
        return sql

    def execute(self, sql: str, params: Sequence[Any] = ()) -> Any:
        conn = self.connect()
        prepared = self._prepare_sql(sql)
        cur = conn.cursor()
        cur.execute(prepared, tuple(params))
        return cur

    def fetchone(self, sql: str, params: Sequence[Any] = ()) -> Optional[Dict[str, Any]]:
        cur = self.execute(sql, params)
        row = cur.fetchone()
        cur.close()
        if row is None:
            return None
        return self._normalize_row(dict(row))

    def fetchall(self, sql: str, params: Sequence[Any] = ()) -> List[Dict[str, Any]]:
        cur = self.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return [self._normalize_row(dict(r)) for r in rows]

    def insert(self, sql: str, params: Sequence[Any] = ()) -> int:
        conn = self.connect()
        if self.is_postgres:
            sql_ret = sql.rstrip().rstrip(";")
            if "RETURNING" not in sql_ret.upper():
                sql_ret += " RETURNING id"
            cur = self.execute(sql_ret, params)
            row = cur.fetchone()
            conn.commit()
            cur.close()
            if row and "id" in row:
                return int(row["id"])
            return 0
        else:
            cur = self.execute(sql, params)
            conn.commit()
            last_id = int(cur.lastrowid or 0)
            cur.close()
            return last_id

    def commit(self) -> None:
        if self._conn is not None:
            self._conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    @staticmethod
    def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
        for k, v in list(row.items()):
            if k in ("preview_style", "default_theme", "theme_settings", "content_json"):
                if isinstance(v, str):
                    try:
                        row[k] = json.loads(v) if v.strip() else {}
                    except Exception:
                        row[k] = {}
                elif v is None:
                    row[k] = {}
            elif k in ("is_active", "is_published", "is_enabled", "has_butterfly_opening", "music_autoplay_after_open", "succeeded"):
                row[k] = bool(v)
        return row


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(160) NOT NULL UNIQUE,
    password_hash VARCHAR(512) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'admin',
    is_active INTEGER NOT NULL DEFAULT 1,
    last_login_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(64) NOT NULL UNIQUE,
    name_ku VARCHAR(120) NOT NULL,
    name_ar VARCHAR(120) NOT NULL,
    name_en VARCHAR(120) NOT NULL,
    category VARCHAR(32) NOT NULL CHECK (category IN ('minimal', 'luxury')),
    description_ku TEXT NOT NULL DEFAULT '',
    description_ar TEXT NOT NULL DEFAULT '',
    description_en TEXT NOT NULL DEFAULT '',
    preview_style TEXT NOT NULL DEFAULT '{}',
    default_theme TEXT NOT NULL DEFAULT '{}',
    has_butterfly_opening INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invitations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug VARCHAR(120) NOT NULL UNIQUE,
    groom_name_ku VARCHAR(120) NOT NULL,
    bride_name_ku VARCHAR(120) NOT NULL,
    groom_name_ar VARCHAR(120) NOT NULL DEFAULT '',
    bride_name_ar VARCHAR(120) NOT NULL DEFAULT '',
    groom_name_en VARCHAR(120) NOT NULL DEFAULT '',
    bride_name_en VARCHAR(120) NOT NULL DEFAULT '',
    wedding_date VARCHAR(64) NOT NULL,
    wedding_time VARCHAR(32) NOT NULL DEFAULT '19:00',
    venue_name_ku VARCHAR(200) NOT NULL DEFAULT '',
    venue_name_ar VARCHAR(200) NOT NULL DEFAULT '',
    venue_name_en VARCHAR(200) NOT NULL DEFAULT '',
    venue_address_ku TEXT NOT NULL DEFAULT '',
    venue_address_ar TEXT NOT NULL DEFAULT '',
    venue_address_en TEXT NOT NULL DEFAULT '',
    map_url TEXT NOT NULL DEFAULT '',
    map_embed_url TEXT NOT NULL DEFAULT '',
    template_code VARCHAR(64) NOT NULL DEFAULT 'magical_butterfly',
    default_language VARCHAR(8) NOT NULL DEFAULT 'ku' CHECK (default_language IN ('ku', 'ar', 'en')),
    primary_color VARCHAR(16) NOT NULL DEFAULT '#C8A253',
    secondary_color VARCHAR(16) NOT NULL DEFAULT '#1E1915',
    background_color VARCHAR(16) NOT NULL DEFAULT '#FAF6EE',
    text_color VARCHAR(16) NOT NULL DEFAULT '#241C15',
    font_arabic VARCHAR(80) NOT NULL DEFAULT 'Vazirmatn',
    font_latin VARCHAR(80) NOT NULL DEFAULT 'Cormorant Garamond',
    opening_card_text_ku TEXT NOT NULL DEFAULT 'کلیل بکە بو ڤەکرنا داخوازنامێ',
    opening_card_text_ar TEXT NOT NULL DEFAULT 'إضغط لفتح بطاقة الدعوة',
    opening_card_text_en TEXT NOT NULL DEFAULT 'Tap to Open Your Invitation',
    bride_image VARCHAR(512) NOT NULL DEFAULT '',
    groom_image VARCHAR(512) NOT NULL DEFAULT '',
    couple_image VARCHAR(512) NOT NULL DEFAULT '',
    hero_video_url VARCHAR(512) NOT NULL DEFAULT '',
    music_source_type VARCHAR(24) NOT NULL DEFAULT 'upload',
    music_url VARCHAR(512) NOT NULL DEFAULT '',
    music_youtube_url VARCHAR(512) NOT NULL DEFAULT '',
    music_title VARCHAR(160) NOT NULL DEFAULT '',
    music_autoplay_after_open INTEGER NOT NULL DEFAULT 1,
    theme_settings TEXT NOT NULL DEFAULT '{}',
    is_published INTEGER NOT NULL DEFAULT 0,
    preview_token VARCHAR(128) NOT NULL DEFAULT '',
    views_count INTEGER NOT NULL DEFAULT 0,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_invitations_slug ON invitations(slug);
CREATE INDEX IF NOT EXISTS idx_invitations_published ON invitations(is_published);

CREATE TABLE IF NOT EXISTS invitation_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invitation_id INTEGER NOT NULL REFERENCES invitations(id) ON DELETE CASCADE,
    section_type VARCHAR(48) NOT NULL,
    title_ku VARCHAR(240) NOT NULL DEFAULT '',
    title_ar VARCHAR(240) NOT NULL DEFAULT '',
    title_en VARCHAR(240) NOT NULL DEFAULT '',
    subtitle_ku VARCHAR(320) NOT NULL DEFAULT '',
    subtitle_ar VARCHAR(320) NOT NULL DEFAULT '',
    subtitle_en VARCHAR(320) NOT NULL DEFAULT '',
    content_ku TEXT NOT NULL DEFAULT '',
    content_ar TEXT NOT NULL DEFAULT '',
    content_en TEXT NOT NULL DEFAULT '',
    content_json TEXT NOT NULL DEFAULT '{}',
    is_enabled INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sections_invitation_order
    ON invitation_sections(invitation_id, sort_order);

CREATE TABLE IF NOT EXISTS media_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invitation_id INTEGER REFERENCES invitations(id) ON DELETE CASCADE,
    media_role VARCHAR(32) NOT NULL CHECK (media_role IN ('bride', 'groom', 'couple', 'gallery', 'music', 'video', 'background')),
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    thumb_path VARCHAR(512) NOT NULL DEFAULT '',
    mime_type VARCHAR(80) NOT NULL,
    file_size INTEGER NOT NULL DEFAULT 0,
    caption_ku VARCHAR(255) NOT NULL DEFAULT '',
    caption_ar VARCHAR(255) NOT NULL DEFAULT '',
    caption_en VARCHAR(255) NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_media_invitation_role
    ON media_uploads(invitation_id, media_role, sort_order);

CREATE TABLE IF NOT EXISTS rsvp_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invitation_id INTEGER NOT NULL REFERENCES invitations(id) ON DELETE CASCADE,
    guest_name VARCHAR(160) NOT NULL,
    guest_phone VARCHAR(64) NOT NULL DEFAULT '',
    attending VARCHAR(24) NOT NULL DEFAULT 'yes' CHECK (attending IN ('yes', 'no', 'maybe')),
    guests_count INTEGER NOT NULL DEFAULT 1 CHECK (guests_count BETWEEN 1 AND 20),
    message TEXT NOT NULL DEFAULT '',
    language VARCHAR(8) NOT NULL DEFAULT 'ku',
    ip_hash VARCHAR(128) NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rsvp_invitation ON rsvp_responses(invitation_id, created_at);

CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(80) PRIMARY KEY,
    value_text TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address VARCHAR(64) NOT NULL,
    username VARCHAR(120) NOT NULL DEFAULT '',
    succeeded INTEGER NOT NULL DEFAULT 0,
    attempted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_login_attempts_ip_time
    ON login_attempts(ip_address, attempted_at);
"""


def get_db() -> DatabaseAdapter:
    """Return request/app-scoped database adapter."""
    db = g.get("_database_adapter")
    if db is None:
        db = DatabaseAdapter(current_app.config["DATABASE_URL"])
        g._database_adapter = db
    return db


def close_db(exception: Optional[BaseException] = None) -> None:
    db = g.get("_database_adapter")
    if db is not None:
        db.close()
        db. _conn = None
        g._database_adapter = None


def init_db_schema() -> None:
    """Create all database tables if they do not exist, and auto-migrate new columns."""
    db = get_db()
    conn = db.connect()
    if db.is_postgres:
        schema_file = Path(__file__).resolve().parent.parent / "migrations" / "001_initial_schema.sql"
        sql = schema_file.read_text(encoding="utf-8")
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        cur.close()
    else:
        conn.executescript(SQLITE_SCHEMA)
        # Ensure existing SQLite DBs have the new music columns if upgrading in-place
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(invitations);")
        existing_cols = {row[1] for row in cur.fetchall()}
        if "music_source_type" not in existing_cols:
            conn.execute("ALTER TABLE invitations ADD COLUMN music_source_type VARCHAR(24) NOT NULL DEFAULT 'upload';")
        if "music_youtube_url" not in existing_cols:
            conn.execute("ALTER TABLE invitations ADD COLUMN music_youtube_url VARCHAR(512) NOT NULL DEFAULT '';")
        conn.commit()
        cur.close()
