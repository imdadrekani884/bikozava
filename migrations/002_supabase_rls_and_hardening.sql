-- =============================================================================
-- BIKOZAVA WEDDING PLATFORM — SUPABASE ROW-LEVEL SECURITY (RLS) & STORAGE HARDENING
-- File: migrations/002_supabase_rls_and_hardening.sql
-- Target Supabase Project: rgshkpvhttjdbkycuesv (https://rgshkpvhttjdbkycuesv.supabase.co)
-- =============================================================================
-- NOTE: This migration is executed automatically by `init_db_schema()` when connected
-- to Supabase PostgreSQL, and can also be run manually in the Supabase SQL Editor.
-- It enables Row-Level Security (RLS) on all tables for public/client API roles
-- (`anon`, `authenticated`) while allowing the backend table owner (`postgres` /
-- `service_role`) full server-side access (`NO FORCE ROW LEVEL SECURITY`).
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. ENABLE ROW LEVEL SECURITY ON EVERY TABLE (WITHOUT BLOCKING TABLE OWNER `postgres`)
-- -----------------------------------------------------------------------------
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users NO FORCE ROW LEVEL SECURITY;

ALTER TABLE public.templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.templates NO FORCE ROW LEVEL SECURITY;

ALTER TABLE public.invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invitations NO FORCE ROW LEVEL SECURITY;

ALTER TABLE public.invitation_sections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invitation_sections NO FORCE ROW LEVEL SECURITY;

ALTER TABLE public.media_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.media_uploads NO FORCE ROW LEVEL SECURITY;

ALTER TABLE public.rsvp_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rsvp_responses NO FORCE ROW LEVEL SECURITY;

ALTER TABLE public.settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.settings NO FORCE ROW LEVEL SECURITY;

ALTER TABLE public.login_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.login_attempts NO FORCE ROW LEVEL SECURITY;

ALTER TABLE public.admin_audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_audit_logs NO FORCE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- 2. REVOKE DEFAULT PUBLIC / ANON / AUTHENTICATED PRIVILEGES ON PRIVATE TABLES
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON public.users FROM anon, authenticated;
        REVOKE ALL ON public.login_attempts FROM anon, authenticated;
        REVOKE ALL ON public.admin_audit_logs FROM anon, authenticated;
        REVOKE ALL ON public.settings FROM anon, authenticated;
        REVOKE ALL ON public.rsvp_responses FROM anon, authenticated;

        -- Column-level least-privilege SELECT on public tables (excludes preview_token & created_by)
        GRANT SELECT ON public.templates TO anon, authenticated;
        GRANT SELECT (
            id, slug,
            groom_name_ku, bride_name_ku, groom_name_ar, bride_name_ar, groom_name_en, bride_name_en,
            wedding_date, wedding_time,
            venue_name_ku, venue_name_ar, venue_name_en,
            venue_address_ku, venue_address_ar, venue_address_en,
            map_url, map_embed_url,
            template_code, default_language,
            primary_color, secondary_color, background_color, text_color,
            font_arabic, font_latin,
            opening_card_text_ku, opening_card_text_ar, opening_card_text_en,
            bride_image, groom_image, couple_image, hero_video_url,
            music_source_type, music_url, music_youtube_url, music_title, music_autoplay_after_open,
            theme_settings, is_published
        ) ON public.invitations TO anon, authenticated;

        GRANT SELECT ON public.invitation_sections TO anon, authenticated;
        GRANT SELECT (
            id, invitation_id, media_role, file_path, thumb_path, mime_type,
            caption_ku, caption_ar, caption_en, sort_order
        ) ON public.media_uploads TO anon, authenticated;

        -- Allow anon to INSERT into rsvp_responses ONLY for published invitations (no SELECT/UPDATE/DELETE)
        GRANT INSERT (
            invitation_id, guest_name, guest_phone, attending, guests_count, message, language, ip_hash
        ) ON public.rsvp_responses TO anon, authenticated;
    END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 3. DROP EXISTING POLICIES (IDEMPOTENT RE-RUN SUPPORT)
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "users_deny_client_access" ON public.users;
DROP POLICY IF EXISTS "login_attempts_deny_client_access" ON public.login_attempts;
DROP POLICY IF EXISTS "audit_logs_deny_client_access" ON public.admin_audit_logs;
DROP POLICY IF EXISTS "settings_deny_client_access" ON public.settings;
DROP POLICY IF EXISTS "settings_public_homepage_read" ON public.settings;
DROP POLICY IF EXISTS "templates_public_read_active" ON public.templates;
DROP POLICY IF EXISTS "invitations_public_read_published" ON public.invitations;
DROP POLICY IF EXISTS "sections_public_read_published" ON public.invitation_sections;
DROP POLICY IF EXISTS "media_public_read_published" ON public.media_uploads;
DROP POLICY IF EXISTS "rsvp_public_insert_published_only" ON public.rsvp_responses;
DROP POLICY IF EXISTS "rsvp_deny_public_select" ON public.rsvp_responses;

-- -----------------------------------------------------------------------------
-- 4. CREATE STRICT RLS POLICIES
-- -----------------------------------------------------------------------------

CREATE POLICY "users_deny_client_access"
    ON public.users FOR ALL USING (false) WITH CHECK (false);

CREATE POLICY "login_attempts_deny_client_access"
    ON public.login_attempts FOR ALL USING (false) WITH CHECK (false);

CREATE POLICY "audit_logs_deny_client_access"
    ON public.admin_audit_logs FOR ALL USING (false) WITH CHECK (false);

CREATE POLICY "settings_deny_client_access"
    ON public.settings FOR ALL USING (false) WITH CHECK (false);

CREATE POLICY "templates_public_read_active"
    ON public.templates FOR SELECT USING (is_active = TRUE);

CREATE POLICY "invitations_public_read_published"
    ON public.invitations FOR SELECT USING (is_published = TRUE);

CREATE POLICY "sections_public_read_published"
    ON public.invitation_sections FOR SELECT
    USING (
        is_enabled = TRUE
        AND EXISTS (
            SELECT 1 FROM public.invitations i
            WHERE i.id = invitation_sections.invitation_id
              AND i.is_published = TRUE
        )
    );

CREATE POLICY "media_public_read_published"
    ON public.media_uploads FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.invitations i
            WHERE i.id = media_uploads.invitation_id
              AND i.is_published = TRUE
        )
    );

CREATE POLICY "rsvp_deny_public_select"
    ON public.rsvp_responses FOR SELECT USING (false);

CREATE POLICY "rsvp_public_insert_published_only"
    ON public.rsvp_responses FOR INSERT
    WITH CHECK (
        char_length(trim(guest_name)) BETWEEN 2 AND 160
        AND attending IN ('yes', 'no', 'maybe')
        AND guests_count BETWEEN 1 AND 20
        AND char_length(message) <= 1000
        AND EXISTS (
            SELECT 1 FROM public.invitations i
            WHERE i.id = rsvp_responses.invitation_id
              AND i.is_published = TRUE
        )
    );

-- -----------------------------------------------------------------------------
-- 5. SAFE PUBLIC VIEW (Excludes `preview_token`, `created_by`, `views_count`)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW public.public_invitations_view AS
SELECT
    id, slug,
    groom_name_ku, bride_name_ku,
    groom_name_ar, bride_name_ar,
    groom_name_en, bride_name_en,
    wedding_date, wedding_time,
    venue_name_ku, venue_name_ar, venue_name_en,
    venue_address_ku, venue_address_ar, venue_address_en,
    map_url, map_embed_url,
    template_code, default_language,
    primary_color, secondary_color, background_color, text_color,
    font_arabic, font_latin,
    opening_card_text_ku, opening_card_text_ar, opening_card_text_en,
    bride_image, groom_image, couple_image, hero_video_url,
    music_source_type, music_url, music_youtube_url, music_title, music_autoplay_after_open,
    theme_settings
FROM public.invitations
WHERE is_published = TRUE;

-- -----------------------------------------------------------------------------
-- 6. SUPABASE STORAGE BUCKET & RLS POLICIES (`wedding-media`)
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'storage') THEN
        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES (
            'wedding-media',
            'wedding-media',
            true,
            26214400, -- 25 MB max
            ARRAY[
                'image/jpeg', 'image/png', 'image/webp',
                'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4',
                'video/mp4', 'video/webm'
            ]
        )
        ON CONFLICT (id) DO UPDATE SET
            public = EXCLUDED.public,
            file_size_limit = EXCLUDED.file_size_limit,
            allowed_mime_types = EXCLUDED.allowed_mime_types;

        EXECUTE 'DROP POLICY IF EXISTS "wedding_media_public_read" ON storage.objects';
        EXECUTE 'DROP POLICY IF EXISTS "wedding_media_deny_anon_write" ON storage.objects';
        EXECUTE 'DROP POLICY IF EXISTS "wedding_media_deny_anon_update" ON storage.objects';
        EXECUTE 'DROP POLICY IF EXISTS "wedding_media_deny_anon_delete" ON storage.objects';

        EXECUTE 'CREATE POLICY "wedding_media_public_read" ON storage.objects FOR SELECT TO anon, authenticated USING (bucket_id = ''wedding-media'')';
        EXECUTE 'CREATE POLICY "wedding_media_deny_anon_write" ON storage.objects FOR INSERT TO anon, authenticated WITH CHECK (false)';
        EXECUTE 'CREATE POLICY "wedding_media_deny_anon_update" ON storage.objects FOR UPDATE TO anon, authenticated USING (false)';
        EXECUTE 'CREATE POLICY "wedding_media_deny_anon_delete" ON storage.objects FOR DELETE TO anon, authenticated USING (false)';
    END IF;
END $$;

COMMIT;
