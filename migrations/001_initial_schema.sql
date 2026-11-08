-- =============================================================================
-- BIKOZAVA WEDDING INVITATION PLATFORM — POSTGRESQL / SUPABASE SCHEMA
-- Migration: 001_initial_schema.sql
-- Project Ref: rgshkpvhttjdbkycuesv
-- Compatible with Supabase PostgreSQL 15+ and standard PostgreSQL
-- =============================================================================

-- 1. ADMINS / USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(160) NOT NULL UNIQUE,
    password_hash VARCHAR(512) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'admin',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. INVITATION TEMPLATES TABLE
CREATE TABLE IF NOT EXISTS templates (
    id SERIAL PRIMARY KEY,
    code VARCHAR(64) NOT NULL UNIQUE,
    name_ku VARCHAR(120) NOT NULL,
    name_ar VARCHAR(120) NOT NULL,
    name_en VARCHAR(120) NOT NULL,
    category VARCHAR(32) NOT NULL CHECK (category IN ('minimal', 'luxury')),
    description_ku TEXT NOT NULL DEFAULT '',
    description_ar TEXT NOT NULL DEFAULT '',
    description_en TEXT NOT NULL DEFAULT '',
    preview_style JSONB NOT NULL DEFAULT '{}'::jsonb,
    default_theme JSONB NOT NULL DEFAULT '{}'::jsonb,
    has_butterfly_opening BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. INVITATIONS TABLE
CREATE TABLE IF NOT EXISTS invitations (
    id SERIAL PRIMARY KEY,
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
    music_source_type VARCHAR(24) NOT NULL DEFAULT 'upload' CHECK (music_source_type IN ('upload', 'youtube', 'none')),
    music_url VARCHAR(512) NOT NULL DEFAULT '',
    music_youtube_url VARCHAR(512) NOT NULL DEFAULT '',
    music_title VARCHAR(160) NOT NULL DEFAULT '',
    music_autoplay_after_open BOOLEAN NOT NULL DEFAULT TRUE,
    theme_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    preview_token VARCHAR(128) NOT NULL DEFAULT '',
    views_count INTEGER NOT NULL DEFAULT 0,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_invitations_slug ON invitations(slug);
CREATE INDEX IF NOT EXISTS idx_invitations_published ON invitations(is_published);

-- 4. INVITATION SECTIONS TABLE
CREATE TABLE IF NOT EXISTS invitation_sections (
    id SERIAL PRIMARY KEY,
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
    content_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sections_invitation_order
    ON invitation_sections(invitation_id, sort_order);

-- 5. MEDIA / UPLOADS TABLE
CREATE TABLE IF NOT EXISTS media_uploads (
    id SERIAL PRIMARY KEY,
    invitation_id INTEGER REFERENCES invitations(id) ON DELETE CASCADE,
    media_role VARCHAR(32) NOT NULL CHECK (media_role IN ('bride', 'groom', 'couple', 'gallery', 'music', 'video', 'background', 'logo')),
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
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_media_invitation_role
    ON media_uploads(invitation_id, media_role, sort_order);

-- 6. RSVP RESPONSES TABLE
CREATE TABLE IF NOT EXISTS rsvp_responses (
    id SERIAL PRIMARY KEY,
    invitation_id INTEGER NOT NULL REFERENCES invitations(id) ON DELETE CASCADE,
    guest_name VARCHAR(160) NOT NULL,
    guest_phone VARCHAR(64) NOT NULL DEFAULT '',
    attending VARCHAR(24) NOT NULL DEFAULT 'yes' CHECK (attending IN ('yes', 'no', 'maybe')),
    guests_count INTEGER NOT NULL DEFAULT 1 CHECK (guests_count BETWEEN 1 AND 20),
    message TEXT NOT NULL DEFAULT '',
    language VARCHAR(8) NOT NULL DEFAULT 'ku',
    ip_hash VARCHAR(128) NOT NULL DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rsvp_invitation ON rsvp_responses(invitation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rsvp_dedup ON rsvp_responses(invitation_id, ip_hash, guest_name);

-- 7. PLATFORM SETTINGS TABLE
CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(80) PRIMARY KEY,
    value_text TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 8. LOGIN AUDIT / RATE LIMIT TABLE
CREATE TABLE IF NOT EXISTS login_attempts (
    id SERIAL PRIMARY KEY,
    ip_address VARCHAR(64) NOT NULL,
    username VARCHAR(120) NOT NULL DEFAULT '',
    succeeded BOOLEAN NOT NULL DEFAULT FALSE,
    attempted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_login_attempts_ip_time
    ON login_attempts(ip_address, attempted_at DESC);

-- 9. ADMIN SECURITY AUDIT LOGS TABLE
CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id SERIAL PRIMARY KEY,
    admin_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    admin_username VARCHAR(120) NOT NULL DEFAULT '',
    action VARCHAR(120) NOT NULL,
    target_type VARCHAR(80) NOT NULL DEFAULT '',
    target_id VARCHAR(120) NOT NULL DEFAULT '',
    ip_address VARCHAR(64) NOT NULL DEFAULT '',
    user_agent TEXT NOT NULL DEFAULT '',
    details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_created
    ON admin_audit_logs(created_at DESC);
