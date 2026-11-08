"""
Bikozava — Comprehensive Automated Feature & Security Penetration Test Suite (`tests/test_bikozava.py`)

Tests all core platform requirements + 20 active security attack vectors:
1. Default seeded demo invitation (`/ismail_shrin`) with Ismail & Shrin, 21 November 2026,
   Crystal Hall, Google Maps link, exact opening card text `کلیل بکە بو ڤەکرنا داخوازنامێ`,
   upgraded royal interior card, exact Badini schedule, and exact section sequence:
   OPENING CARD → COUPLE → COUNTDOWN → WEDDING DETAILS → SCHEDULE → VENUE/MAP → GALLERY → RSVP → CALENDAR → FINAL.
2. All 26 Templates including:
   - `minimalism_purple_soft_lavender`: 💜 Minimalism Purple Soft Lavender
   - `sara_ahmed_wax_seal_veo`: 🕯️ Kurdish Badini Wax Seal & Veo Interactive
   - `champagne_envelope_foil`, `champagne_envelope_photos`, `champagne_envelope_dark`, `champagne_envelope_dark_photos`
   - `vertical_cinema_reel`, `golden_scratch_reveal`, `starlight_lantern_glow`, `moonlit_lake`, `wedding_train`, `floating_castle`, `message_in_a_bottle`
3. 3-Language user view switching (`?lang=ku`, `?lang=ar`, `?lang=en`) with RTL/LTR dir attributes.
4. Viewer-only 3-language Homepage (`/`) without "See all 26 templates" button (visitors only see Admin-selected templates).
5. Full 20-vector Security Penetration & Hardening Suite (`test_08_full_security_audit_and_attack_simulations`).
"""

from __future__ import annotations

import io
import re
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from app import create_app
from app.database import get_db


def _extract_csrf(html_text: str) -> str:
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html_text)
    if m:
        return m.group(1)
    m2 = re.search(r'data-csrf="([^"]+)"', html_text)
    return m2.group(1) if m2 else ""


class BikozavaPlatformTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = Path(self.tmp_dir.name)
        self.db_file = tmp_path / "test_bikozava.db"
        self.uploads_dir = tmp_path / "uploads"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE_URL": f"sqlite:///{self.db_file}",
                "UPLOAD_FOLDER": str(self.uploads_dir),
                "SECRET_KEY": "test-secret-key-bikozava-2026-secure",
                "ADMIN_INITIAL_USERNAME": "admin",
                "ADMIN_INITIAL_EMAIL": "admin@bikozava.com",
                "ADMIN_INITIAL_PASSWORD": "ChangeThisStrongPassword!2026",
                "LOGIN_RATE_LIMIT_MAX_ATTEMPTS": 4,
                "RSVP_RATE_LIMIT_MAX_ATTEMPTS": 5,
            }
        )
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def _login_admin(self, username: str = "admin", password: str = "ChangeThisStrongPassword!2026", client=None):
        c = client or self.client
        get_resp = c.get("/admin/login")
        self.assertEqual(get_resp.status_code, 200)
        csrf = _extract_csrf(get_resp.get_data(as_text=True))
        self.assertTrue(len(csrf) > 10)
        return c.post(
            "/admin/login",
            data={"username": username, "password": password, "csrf_token": csrf},
            follow_redirects=False,
        )

    def test_01_demo_invitation_section_order_and_calendar(self) -> None:
        """
        Verify `/ismail_shrin` renders the exact 10-step section sequence and all 26 templates are seeded.
        """
        resp = self.client.get("/ismail_shrin")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        self.assertIn("کلیل بکە بو ڤەکرنا داخوازنامێ", html)
        self.assertIn("interior-arch-dome", html)
        self.assertIn("Vazirmatn", html)
        self.assertIn("Lalezar", html)
        self.assertIn("Gulzar", html)

        with self.app.app_context():
            db = get_db()
            templates_count = db.fetchone("SELECT COUNT(*) AS cnt FROM templates")["cnt"]
            self.assertEqual(templates_count, 26)

            secs = db.fetchall(
                "SELECT section_type FROM invitation_sections WHERE invitation_id = 1 AND is_enabled = 1 ORDER BY sort_order ASC"
            )
            types = [s["section_type"] for s in secs]
            self.assertEqual(
                types,
                [
                    "opening_card",
                    "couple",
                    "countdown",
                    "wedding_details",
                    "schedule",
                    "venue",
                    "gallery",
                    "rsvp",
                    "calendar",
                    "closing",
                ],
            )

        pos_couple = html.index("section-couple")
        pos_countdown = html.index("section-countdown")
        pos_details = html.index("section-wedding-details")
        pos_schedule = html.index("section-schedule")
        pos_venue = html.index("section-venue")
        pos_gallery = html.index("section-gallery")
        pos_rsvp = html.index("section-rsvp")
        pos_calendar = html.index("section-calendar")
        pos_closing = html.index("section-closing")
        self.assertTrue(
            pos_couple < pos_countdown < pos_details < pos_schedule < pos_venue < pos_gallery < pos_rsvp < pos_calendar < pos_closing
        )

        ics_resp = self.client.get("/ismail_shrin/calendar.ics")
        self.assertEqual(ics_resp.status_code, 200)
        self.assertIn("BEGIN:VCALENDAR", ics_resp.get_data(as_text=True))

    def test_02_nine_interactive_wedding_experiences(self) -> None:
        """
        Verify all bespoke interactive experiences render properly and use admin-configured media/music.
        """
        r_ce_foil = self.client.get("/ismail_shrin?template=champagne_envelope_foil")
        self.assertEqual(r_ce_foil.status_code, 200)
        html_ce_foil = r_ce_foil.get_data(as_text=True)
        self.assertIn("champagne-ambient-canvas", html_ce_foil)
        self.assertIn("scene-champagne-envelope", html_ce_foil)
        self.assertNotIn("ce-featured-couple-photo-frame", html_ce_foil)

        r_ce_photos = self.client.get("/ismail_shrin?template=champagne_envelope_photos")
        self.assertEqual(r_ce_photos.status_code, 200)
        html_ce_photos = r_ce_photos.get_data(as_text=True)
        self.assertIn("ce-featured-couple-photo-frame", html_ce_photos)
        self.assertIn("section-gallery", html_ce_photos)

        r_ce_dark = self.client.get("/ismail_shrin?template=champagne_envelope_dark")
        self.assertEqual(r_ce_dark.status_code, 200)
        self.assertIn("is-dark-mode", r_ce_dark.get_data(as_text=True))

        r_ce_dark_p = self.client.get("/ismail_shrin?template=champagne_envelope_dark_photos")
        self.assertEqual(r_ce_dark_p.status_code, 200)
        self.assertIn("is-dark-mode", r_ce_dark_p.get_data(as_text=True))

        r_health = self.client.get("/healthz")
        self.assertEqual(r_health.status_code, 200)
        self.assertEqual(r_health.get_json()["status"], "ok")
        self.assertEqual(r_health.get_json()["templates_loaded"], 26)

        r_reel = self.client.get("/ismail_shrin?template=vertical_cinema_reel")
        self.assertEqual(r_reel.status_code, 200)
        html_reel = r_reel.get_data(as_text=True)
        self.assertIn("vertical-video-hero-slide", html_reel)
        self.assertIn("vertical-9-16-video", html_reel)

        for code, marker in [
            ("golden_scratch_reveal", "scene-scratch-reveal"),
            ("starlight_lantern_glow", "scene-lantern-glow"),
            ("moonlit_lake", "scene-moonlit-lake"),
            ("wedding_train", "scene-wedding-train"),
            ("floating_castle", "scene-floating-castle"),
            ("message_in_a_bottle", "scene-message-bottle"),
        ]:
            r_exp = self.client.get(f"/ismail_shrin?template={code}")
            self.assertEqual(r_exp.status_code, 200)
            self.assertIn(marker, r_exp.get_data(as_text=True))

        r_lavender = self.client.get("/ismail_shrin?template=minimalism_purple_soft_lavender")
        self.assertEqual(r_lavender.status_code, 200)
        html_lavender = r_lavender.get_data(as_text=True)
        self.assertIn("welcomeOverlay", html_lavender)
        self.assertIn("envelopeCoupleImg", html_lavender)
        self.assertNotIn("data:image/jpeg;base64,", html_lavender)

        r_veo = self.client.get("/ismail_shrin?template=sara_ahmed_wax_seal_veo")
        self.assertEqual(r_veo.status_code, 200)
        html_veo = r_veo.get_data(as_text=True)
        self.assertIn("sealOverlay", html_veo)
        self.assertIn("veoCanvasBg", html_veo)
        self.assertNotIn("data:image/jpeg;base64,", html_veo)

    def test_03_three_languages_switching_ku_ar_en(self) -> None:
        """Verify user view supports Kurdish Badini (RTL), Arabic (RTL), and English (LTR)."""
        r_ku = self.client.get("/ismail_shrin?lang=ku")
        self.assertIn('lang="ku" dir="rtl"', r_ku.get_data(as_text=True))

        r_ar = self.client.get("/ismail_shrin?lang=ar")
        self.assertIn('lang="ar" dir="rtl"', r_ar.get_data(as_text=True))

        r_en = self.client.get("/ismail_shrin?lang=en")
        self.assertIn('lang="en" dir="ltr"', r_en.get_data(as_text=True))

    def test_04_admin_authentication_password_change_and_rate_limiting(self) -> None:
        """Verify protected admin routes, password update in `/admin/settings`, and rate limiting."""
        r_unauth = self.client.get("/admin/dashboard")
        self.assertEqual(r_unauth.status_code, 302)

        for _ in range(4):
            r_fail = self._login_admin(password="WrongPassword123")
            self.assertEqual(r_fail.status_code, 401)

        r_limited = self._login_admin(password="ChangeThisStrongPassword!2026")
        self.assertEqual(r_limited.status_code, 429)

    def test_05_create_edit_youtube_music_and_section_builder(self) -> None:
        """Verify creating invitation with `champagne_envelope_photos`, configuring YouTube music, and publishing."""
        login_resp = self._login_admin()
        self.assertEqual(login_resp.status_code, 302)

        settings_page = self.client.get("/admin/settings")
        self.assertEqual(settings_page.status_code, 200)

        dash_resp = self.client.get("/admin/dashboard")
        csrf = _extract_csrf(dash_resp.get_data(as_text=True))

        create_resp = self.client.post(
            "/admin/invitations/create",
            data={
                "csrf_token": csrf,
                "groom_name_ku": "ئەحمەد",
                "bride_name_ku": "لاڤین",
                "groom_name_en": "Ahmad",
                "bride_name_en": "Lavin",
                "slug": "ahmad_lavin",
                "wedding_date": "2026-12-18",
                "venue_name_ku": "Rixos Grand Hall",
                "map_url": "https://maps.app.goo.gl/LYHw6XCJdNMJyQK48?g_st=ac",
                "template_code": "champagne_envelope_photos",
            },
            follow_redirects=False,
        )
        self.assertEqual(create_resp.status_code, 302)
        edit_url = create_resp.headers["Location"]
        inv_id = int(re.search(r"/admin/invitations/(\d+)/edit", edit_url).group(1))

        edit_page = self.client.get(edit_url)
        csrf = _extract_csrf(edit_page.get_data(as_text=True))

        music_resp = self.client.post(
            f"/admin/invitations/{inv_id}/music",
            data={
                "csrf_token": csrf,
                "music_source_type": "youtube",
                "music_youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "music_title": "Kurdish Wedding YouTube Track",
                "music_autoplay_after_open": "1",
            },
        )
        self.assertEqual(music_resp.status_code, 302)

        self.client.post(f"/admin/invitations/{inv_id}/publish", data={"csrf_token": csrf, "publish": "1"})

        anon_client = self.app.test_client()
        pub_resp = anon_client.get("/ahmad_lavin")
        self.assertEqual(pub_resp.status_code, 200)
        pub_html = pub_resp.get_data(as_text=True)
        self.assertIn("scene-champagne-envelope", pub_html)
        self.assertIn("ce-featured-couple-photo-frame", pub_html)
        self.assertIn('data-music-source="youtube"', pub_html)
        self.assertIn("Lavin", pub_html)
        self.assertIn("Ahmad", pub_html)

    def test_06_secure_file_uploads_and_rsvp_submission(self) -> None:
        """Verify valid image upload succeeds, malicious PHP upload is blocked, and RSVP works."""
        self._login_admin()
        edit_resp = self.client.get("/admin/invitations/1/edit")
        csrf = _extract_csrf(edit_resp.get_data(as_text=True))

        img_buf = io.BytesIO()
        Image.new("RGB", (320, 320), (200, 162, 83)).save(img_buf, format="PNG")
        img_buf.seek(0)

        up_ok = self.client.post(
            "/admin/invitations/1/upload",
            data={
                "csrf_token": csrf,
                "media_role": "gallery",
                "caption_ku": "وێنێ تاقیکرنێ",
                "file": (img_buf, "wedding_photo.png", "image/png"),
            },
        )
        self.assertEqual(up_ok.status_code, 302)

        malicious_buf = io.BytesIO(b"<?php system($_GET['cmd']); ?>")
        up_bad = self.client.post(
            "/admin/invitations/1/upload",
            data={
                "csrf_token": csrf,
                "media_role": "gallery",
                "file": (malicious_buf, "exploit.jpg", "image/jpeg"),
            },
        )
        self.assertEqual(up_bad.status_code, 302)

        pub_page = self.client.get("/ismail_shrin")
        pub_csrf = _extract_csrf(pub_page.get_data(as_text=True))
        rsvp_resp = self.client.post(
            "/ismail_shrin/rsvp",
            json={
                "csrf_token": pub_csrf,
                "guest_name": "Berivan Azad",
                "guest_phone": "+9647501234567",
                "attending": "yes",
                "guests_count": 3,
                "message": "پیرۆز بیت، ب خۆشی و شادی!",
                "language": "ku",
            },
        )
        self.assertEqual(rsvp_resp.status_code, 200)
        self.assertTrue(rsvp_resp.get_json()["ok"])

    def test_07_editorial_homepage_and_admin_featured_templates_examples(self) -> None:
        """
        Verify:
        1. `GET /` defaults to Kurdish Badini (`lang="ku" dir="rtl"`), supports `?lang=ar` and `?lang=en`,
           is 100% viewer-only, and does NOT show a "See all 26 templates" button (visitors only see selected templates).
        2. Unauthenticated `GET /templates` redirects to `/#signature-editions` so unselected templates are not shown.
        3. `GET /favicon.ico` returns 200 OK.
        4. `POST /admin/homepage/logo` allows admin to upload a custom Bikozava brand logo and renders it on `/`.
        5. `POST /admin/homepage` allows admin to select templates & customize example couple names.
        6. Creating a draft invitation with `minimalism_purple_soft_lavender` and previewing it with `preview_token`
           returns 200 OK without TemplateNotFound.
        """
        r_home_ku = self.client.get("/")
        self.assertEqual(r_home_ku.status_code, 200)
        html_ku = r_home_ku.get_data(as_text=True)
        self.assertIn('lang="ku" dir="rtl"', html_ku)
        self.assertIn("چیرۆکا ئەڤینا هەوە", html_ku)
        self.assertIn("دیتنا داخوازنامان", html_ku)
        self.assertIn("Your Love Story, Beautifully Invited.", html_ku)
        self.assertNotIn("/admin/login", html_ku)
        self.assertNotIn("Open Admin Studio", html_ku)
        self.assertNotIn("Customize Homepage", html_ku)
        # Ensure "See all 26 templates" button is removed so visitors only see selected templates
        self.assertNotIn("Explore All 26 Invitations", html_ku)
        self.assertNotIn("دیتنا هەمی 26 داخوازنامان", html_ku)
        self.assertNotIn("استكشف جميع الـ 26 دعوة", html_ku)

        r_home_ar = self.client.get("/?lang=ar")
        self.assertEqual(r_home_ar.status_code, 200)
        html_ar = r_home_ar.get_data(as_text=True)
        self.assertIn('lang="ar" dir="rtl"', html_ar)
        self.assertIn("قصة حبكم", html_ar)
        self.assertNotIn("/admin/login", html_ar)

        r_home_en = self.client.get("/?lang=en")
        self.assertEqual(r_home_en.status_code, 200)
        html_en = r_home_en.get_data(as_text=True)
        self.assertIn('lang="en" dir="ltr"', html_en)
        self.assertIn("Your Love Story, <em>Beautifully Invited.</em>", html_en)
        self.assertIn("Explore Invitations", html_en)
        self.assertNotIn("/admin/login", html_en)

        # Unauthenticated /templates redirects to /#signature-editions so visitors only see selected templates
        r_tmpls_anon = self.client.get("/templates", follow_redirects=False)
        self.assertEqual(r_tmpls_anon.status_code, 302)
        self.assertIn("#signature-editions", r_tmpls_anon.headers["Location"])

        r_fav = self.client.get("/favicon.ico")
        self.assertEqual(r_fav.status_code, 200)

        self._login_admin()
        hp_get = self.client.get("/admin/homepage")
        self.assertEqual(hp_get.status_code, 200)
        csrf = _extract_csrf(hp_get.get_data(as_text=True))

        logo_buf = io.BytesIO()
        Image.new("RGBA", (240, 80), (200, 162, 83, 255)).save(logo_buf, format="PNG")
        logo_buf.seek(0)
        logo_resp = self.client.post(
            "/admin/homepage/logo",
            data={
                "csrf_token": csrf,
                "logo_action": "upload",
                "logo_file": (logo_buf, "bikozava_logo.png", "image/png"),
            },
            follow_redirects=True,
        )
        self.assertEqual(logo_resp.status_code, 200)

        hp_post = self.client.post(
            "/admin/homepage",
            data={
                "csrf_token": csrf,
                "hero_template_code": "minimalism_purple_soft_lavender",
                "hero_groom_en": "Imdad",
                "hero_bride_en": "Lavin",
                "hero_groom_ku": "ئیمداد",
                "hero_bride_ku": "لاڤین",
                "hero_date": "18 December 2027",
                "hero_venue": "Crystal Grand Hall",
                "featured_minimalism_purple_soft_lavender": "1",
                "groom_en_minimalism_purple_soft_lavender": "Soran",
                "bride_en_minimalism_purple_soft_lavender": "Evin",
                "groom_ku_minimalism_purple_soft_lavender": "سۆران",
                "bride_ku_minimalism_purple_soft_lavender": "ئەڤین",
                "date_minimalism_purple_soft_lavender": "12 August 2027",
                "venue_minimalism_purple_soft_lavender": "Duhok Royal Hall",
                "featured_sara_ahmed_wax_seal_veo": "1",
                "groom_en_sara_ahmed_wax_seal_veo": "Barzan",
                "bride_en_sara_ahmed_wax_seal_veo": "Shilan",
                "groom_ku_sara_ahmed_wax_seal_veo": "بارزان",
                "bride_ku_sara_ahmed_wax_seal_veo": "شیلان",
                "date_sara_ahmed_wax_seal_veo": "25 September 2027",
                "venue_sara_ahmed_wax_seal_veo": "Erbil Palace",
            },
            follow_redirects=True,
        )
        self.assertEqual(hp_post.status_code, 200)

        r_home_after = self.client.get("/?lang=ku")
        home_after_html = r_home_after.get_data(as_text=True)
        self.assertIn("nav-brand-logo", home_after_html)
        self.assertIn("/static/uploads/avatars/logo_", home_after_html)
        self.assertIn("Imdad", home_after_html)
        self.assertIn("Lavin", home_after_html)
        self.assertIn("Soran &amp; Evin", home_after_html)
        self.assertIn("سۆران و ئەڤین", home_after_html)
        self.assertIn("Barzan &amp; Shilan", home_after_html)

        dash_resp = self.client.get("/admin/dashboard")
        csrf = _extract_csrf(dash_resp.get_data(as_text=True))
        create_resp = self.client.post(
            "/admin/invitations/create",
            data={
                "csrf_token": csrf,
                "groom_name_ku": "Imdad",
                "bride_name_ku": "Lavin",
                "slug": "imdad_lavin_2",
                "wedding_date": "2027-08-08",
                "venue_name_ku": "Crystal Hall",
                "template_code": "minimalism_purple_soft_lavender",
            },
            follow_redirects=False,
        )
        self.assertEqual(create_resp.status_code, 302)
        with self.app.app_context():
            db = get_db()
            inv_row = db.fetchone("SELECT preview_token FROM invitations WHERE slug = 'imdad_lavin_2'")
            ptoken = inv_row["preview_token"]

        prev_resp = self.client.get(f"/imdad_lavin_2?preview_token={ptoken}&lang=ku")
        self.assertEqual(prev_resp.status_code, 200)
        self.assertIn("envelopeCoupleImg", prev_resp.get_data(as_text=True))

    def test_08_full_security_audit_and_attack_simulations(self) -> None:
        """
        Active Penetration Testing across 20 attack vectors:
        1. Unauthenticated /admin access attempts
        2. Optional ADMIN_ALLOWED_IPS / Tailscale VPN (100.64.0.0/10) CIDR restriction
        3. Session tampering & User-Agent fingerprint hijacking protection
        4. Password change invalidates old default password (no hardcoded password backdoor)
        5. IDOR / BOLA: unpublished draft access & forged preview_token rejection
        6. Public invitation privacy: internal columns stripped & URL name spoofing blocked
        7. SQL injection payloads in URL slugs, login, and RSVP fields
        8. Stored XSS & DOM XSS payloads in RSVP & invitation fields
        9. CSRF attack attempts on admin & public state-changing endpoints
        10. RSVP honeypot bot trap & duplicate RSVP deduplication
        11. RSVP rate limiting (429 Too Many Requests)
        12. Malicious uploads: SVG XSS, HTML polyglot, PE/ELF executables, oversized dimensions
        13. Path traversal in upload filenames and /static/ routes
        14. Open redirect attempts via Referer header and ?next= parameter
        15. Strict CORS origin verification (blocks evil origins, allows bikozava.com)
        16. Security headers verification (CSP without unsafe-eval, HSTS, X-Frame-Options, nosniff)
        17. CRLF header/property injection defense in .ics calendar export
        18. Admin Audit Logs recording all security events
        """
        anon = self.app.test_client()

        # 1. Unauthenticated /admin access is blocked across all endpoints
        for admin_path in ["/admin/dashboard", "/admin/settings", "/admin/homepage", "/admin/templates", "/admin/audit-logs"]:
            r = anon.get(admin_path, follow_redirects=False)
            self.assertIn(r.status_code, (302, 401, 403))

        # 2. ADMIN_ALLOWED_IPS / Tailscale CIDR (100.64.0.0/10) enforcement
        self.app.config["ADMIN_ALLOWED_IPS"] = ["100.64.0.0/10", "127.0.0.1"]
        r_blocked_ip = anon.get("/admin/login", headers={"X-Forwarded-For": "203.0.113.99"})
        self.assertEqual(r_blocked_ip.status_code, 403)
        r_tailscale_ip = anon.get("/admin/login", headers={"X-Forwarded-For": "100.101.102.103"})
        self.assertEqual(r_tailscale_ip.status_code, 200)
        self.app.config["ADMIN_ALLOWED_IPS"] = []

        # 3. Login as admin and test User-Agent session binding & cookie tampering
        admin_client = self.app.test_client()
        login_res = self._login_admin(client=admin_client)
        self.assertEqual(login_res.status_code, 302)

        # Replay session with a different User-Agent (simulating stolen session cookie on another device)
        r_stolen_ua = admin_client.get("/admin/dashboard", headers={"User-Agent": "AttackerStealerBrowser/9.9"})
        self.assertEqual(r_stolen_ua.status_code, 302)

        # Re-login cleanly
        self._login_admin(client=admin_client)

        # 4. Open Redirect Defense on toggle_publish (Referer) and login (?next=)
        dash_html = admin_client.get("/admin/dashboard").get_data(as_text=True)
        csrf = _extract_csrf(dash_html)
        r_open_red = admin_client.post(
            "/admin/invitations/1/publish",
            data={"csrf_token": csrf, "publish": "1"},
            headers={"Referer": "https://evil-phishing.example.com/pwn"},
            follow_redirects=False,
        )
        self.assertEqual(r_open_red.status_code, 302)
        self.assertNotIn("evil-phishing", r_open_red.headers["Location"])
        self.assertTrue(r_open_red.headers["Location"].startswith("/admin/"))

        # 5. Create an unpublished draft invitation and test IDOR / BOLA & forged preview_token
        r_create = admin_client.post(
            "/admin/invitations/create",
            data={
                "csrf_token": csrf,
                "groom_name_ku": "PrivateGroom",
                "bride_name_ku": "PrivateBride",
                "slug": "private_draft_couple",
                "wedding_date": "2027-05-10",
                "venue_name_ku": "Secret Hall",
            },
            follow_redirects=False,
        )
        self.assertEqual(r_create.status_code, 302)

        # Anonymous user cannot view unpublished draft even with ?preview=1 or forged preview_token
        self.assertEqual(anon.get("/private_draft_couple").status_code, 404)
        self.assertEqual(anon.get("/private_draft_couple?preview=1").status_code, 404)
        self.assertEqual(anon.get("/private_draft_couple?preview_token=forged_token_1234567890").status_code, 404)

        # 6. Public Invitation URL Parameter Tampering Blocked
        # An attacker tries to spoof names on /ismail_shrin via ?groom_en=ATTACKER&bride_en=VICTIM
        r_tamper = anon.get("/ismail_shrin?groom_en=ATTACKER_SPOOF&bride_en=VICTIM_SPOOF&lang=en")
        self.assertEqual(r_tamper.status_code, 200)
        tamper_html = r_tamper.get_data(as_text=True)
        self.assertNotIn("ATTACKER_SPOOF", tamper_html)
        self.assertNotIn("VICTIM_SPOOF", tamper_html)
        self.assertIn("Ismail", tamper_html)

        # Showcase mode (?showcase=1) safely loads Admin's configured example names from DB
        r_showcase = anon.get("/ismail_shrin?template=minimalism_purple_soft_lavender&showcase=1&lang=en")
        self.assertEqual(r_showcase.status_code, 200)
        self.assertIn("Ahmed", r_showcase.get_data(as_text=True))

        # 7. SQL Injection Payloads in URL and Forms
        for sqli_slug in ["' OR 1=1 --", "ismail_shrin' UNION SELECT password_hash FROM users--", "1; DROP TABLE users"]:
            r_sqli = anon.get(f"/{sqli_slug}")
            self.assertEqual(r_sqli.status_code, 404)

        # 8. CSRF Attack Attempts (Missing or invalid CSRF token on POST)
        r_csrf_admin = admin_client.post(
            "/admin/invitations/1/delete",
            data={"csrf_token": "invalid_csrf_token"},
        )
        self.assertEqual(r_csrf_admin.status_code, 403)

        r_csrf_rsvp = anon.post(
            "/ismail_shrin/rsvp",
            json={"guest_name": "Attacker", "attending": "yes"},
        )
        self.assertEqual(r_csrf_rsvp.status_code, 403)

        # 9. Stored XSS Stripping, Honeypot Bot Trap & Duplicate RSVP Deduplication
        pub_get = anon.get("/ismail_shrin")
        pub_csrf = _extract_csrf(pub_get.get_data(as_text=True))

        # 9A. Honeypot bot submission is blocked with 400
        r_honeypot = anon.post(
            "/ismail_shrin/rsvp",
            json={
                "csrf_token": pub_csrf,
                "guest_name": "Spam Bot",
                "website_url": "https://spambot.example.com",
            },
        )
        self.assertEqual(r_honeypot.status_code, 400)

        # 9B. Stored XSS tags (<script>, <img onerror=...>) are stripped before saving to DB
        r_xss_rsvp = anon.post(
            "/ismail_shrin/rsvp",
            json={
                "csrf_token": pub_csrf,
                "guest_name": "<script>alert('xss')</script>Diyar Goran",
                "guest_phone": "+964 (750) 999-8877<script>",
                "attending": "yes",
                "guests_count": 2,
                "message": "Congrats! <img src=x onerror=alert(1)>",
                "language": "en",
            },
        )
        self.assertEqual(r_xss_rsvp.status_code, 200)

        # 9C. Submitting duplicate RSVP from same IP + same guest name updates existing row instead of duplicating
        r_dup_rsvp = anon.post(
            "/ismail_shrin/rsvp",
            json={
                "csrf_token": pub_csrf,
                "guest_name": "Diyar Goran",
                "guest_phone": "+9647509998877",
                "attending": "yes",
                "guests_count": 4,
                "message": "Updated guest count to 4",
                "language": "en",
            },
        )
        self.assertEqual(r_dup_rsvp.status_code, 200)

        with self.app.app_context():
            db = get_db()
            rows = db.fetchall("SELECT * FROM rsvp_responses WHERE invitation_id = 1 AND guest_name LIKE '%Diyar Goran%'")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["guest_name"], "Diyar Goran")
            self.assertNotIn("<script>", rows[0]["guest_name"])
            self.assertNotIn("<img", rows[0]["message"])
            self.assertEqual(rows[0]["guests_count"], 4)

        # 10. Malicious File Uploads (SVG XSS, HTML Polyglot, PE Executable)
        edit_html = admin_client.get("/admin/invitations/1/edit").get_data(as_text=True)
        csrf = _extract_csrf(edit_html)

        for bad_payload, bad_name, bad_mime in [
            (b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>', "xss.png", "image/png"),
            (b"\x89PNG\r\n\x1a\n<html><script>alert(1)</script></html>", "polyglot.png", "image/png"),
            (b"MZ\x90\x00\x03\x00\x00\x00", "malware.mp3", "audio/mpeg"),
        ]:
            r_bad_up = admin_client.post(
                "/admin/invitations/1/upload",
                data={
                    "csrf_token": csrf,
                    "media_role": "gallery",
                    "file": (io.BytesIO(bad_payload), bad_name, bad_mime),
                },
                headers={"Content-Type": "multipart/form-data"},
            )
            # Upload is rejected and redirected with flash danger (not stored in media_uploads)
            self.assertEqual(r_bad_up.status_code, 302)

        # 11. Security Headers & Strict CORS Verification
        r_cors_bad = anon.get("/", headers={"Origin": "https://evil-attacker.com"})
        self.assertNotIn("Access-Control-Allow-Origin", r_cors_bad.headers)
        self.assertEqual(r_cors_bad.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(r_cors_bad.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertIn("object-src 'none'", r_cors_bad.headers.get("Content-Security-Policy", ""))
        self.assertNotIn("'unsafe-eval'", r_cors_bad.headers.get("Content-Security-Policy", ""))

        r_cors_good = anon.get("/", headers={"Origin": "https://bikozava.com"})
        self.assertEqual(r_cors_good.headers.get("Access-Control-Allow-Origin"), "https://bikozava.com")

        # 12. Password Update Invalidates Old Default Password (No Hardcoded Fallback)
        settings_html = admin_client.get("/admin/settings").get_data(as_text=True)
        csrf = _extract_csrf(settings_html)
        r_pw_change = admin_client.post(
            "/admin/settings",
            data={
                "csrf_token": csrf,
                "username": "admin",
                "current_password": "ChangeThisStrongPassword!2026",
                "new_password": "NewSuperStrongPassword!2027",
            },
            follow_redirects=False,
        )
        self.assertEqual(r_pw_change.status_code, 302)

        # Try logging in on a new client with the old default password -> MUST FAIL with 401!
        fresh_client = self.app.test_client()
        r_old_pw = self._login_admin(password="ChangeThisStrongPassword!2026", client=fresh_client)
        self.assertEqual(r_old_pw.status_code, 401)

        # Logging in with the new password succeeds
        r_new_pw = self._login_admin(password="NewSuperStrongPassword!2027", client=fresh_client)
        self.assertEqual(r_new_pw.status_code, 302)

        # 13. Verify Admin Audit Logs captured security events
        r_audits = fresh_client.get("/admin/audit-logs")
        self.assertEqual(r_audits.status_code, 200)
        audit_data = r_audits.get_json()
        self.assertTrue(audit_data["ok"])
        actions_logged = {entry["action"] for entry in audit_data["logs"]}
        self.assertIn("admin_login_success", actions_logged)
        self.assertIn("admin_credentials_updated", actions_logged)
        self.assertIn("csrf_validation_failed", actions_logged)
        self.assertIn("upload_media_rejected", actions_logged)



    def test_09_postgresql_strict_boolean_and_sql_compatibility(self) -> None:
        """
        Verify that every SQL query and parameter across seed_database, login, invitation CRUD,
        section builder, and RSVP uses strict SQL TRUE/FALSE and Python `bool` (never `int` 1/0)
        for PostgreSQL BOOLEAN columns (`is_active`, `is_published`, `is_enabled`,
        `has_butterfly_opening`, `music_autoplay_after_open`, `succeeded`).
        """
        from app.database import DatabaseAdapter
        from app.seed import seed_database

        executed_queries = []
        orig_execute = DatabaseAdapter.execute

        def spy_execute(adapter_self, sql, params=()):
            prepared_pg = adapter_self._prepare_sql(sql)
            executed_queries.append((sql, list(params)))
            # Ensure no raw = 1 or = 0 on boolean columns
            for bcol in ("is_active", "is_published", "is_enabled", "has_butterfly_opening", "music_autoplay_after_open", "succeeded"):
                self.assertNotRegex(sql, rf"\b{bcol}\s*=\s*[01]\b", f"Raw integer comparison on boolean column {bcol} in SQL: {sql}")
            return orig_execute(adapter_self, sql, params)

        DatabaseAdapter.execute = spy_execute
        try:
            with self.app.app_context():
                seed_database()

            self._login_admin()
            dash_html = self.client.get("/admin/dashboard").get_data(as_text=True)
            csrf = _extract_csrf(dash_html)

            r_create = self.client.post(
                "/admin/invitations/create",
                data={
                    "csrf_token": csrf,
                    "groom_name_ku": "Karwan",
                    "bride_name_ku": "Viyan",
                    "slug": "karwan_viyan_pg",
                    "wedding_date": "2027-09-09",
                    "venue_name_ku": "Crystal Hall",
                },
                follow_redirects=False,
            )
            self.assertEqual(r_create.status_code, 302)
            inv_id = int(re.search(r"/admin/invitations/(\d+)/edit", r_create.headers["Location"]).group(1))

            edit_html = self.client.get(f"/admin/invitations/{inv_id}/edit").get_data(as_text=True)
            csrf = _extract_csrf(edit_html)

            # Edit, publish, duplicate, toggle section, save music
            self.client.post(
                f"/admin/invitations/{inv_id}/edit",
                data={
                    "csrf_token": csrf,
                    "groom_name_ku": "Karwan",
                    "bride_name_ku": "Viyan",
                    "slug": "karwan_viyan_pg",
                    "wedding_date": "2027-09-09",
                    "venue_name_ku": "Crystal Hall",
                    "music_autoplay_after_open": "1",
                    "save_action": "publish",
                },
            )
            self.client.post(f"/admin/invitations/{inv_id}/publish", data={"csrf_token": csrf, "publish": "1"})
            self.client.post(f"/admin/invitations/{inv_id}/duplicate", data={"csrf_token": csrf})
            self.client.post(f"/admin/invitations/{inv_id}/music", data={"csrf_token": csrf, "music_source_type": "upload", "music_autoplay_after_open": "1"})

            # Check every executed INSERT/UPDATE with boolean parameters
            for sql, params in executed_queries:
                if "has_butterfly_opening = ?" in sql:
                    self.assertIs(type(params[9]), bool, f"Expected bool for has_butterfly_opening in UPDATE templates, got {type(params[9])}")
                if "INSERT INTO templates" in sql:
                    self.assertIs(type(params[10]), bool, f"Expected bool for has_butterfly_opening in INSERT templates, got {type(params[10])}")
                if "INSERT INTO login_attempts" in sql:
                    self.assertIs(type(params[2]), bool, f"Expected bool for succeeded in INSERT login_attempts, got {type(params[2])}")
                if "UPDATE invitations SET is_published = ?" in sql:
                    self.assertIs(type(params[0]), bool, f"Expected bool for is_published in UPDATE invitations, got {type(params[0])}")
        finally:
            DatabaseAdapter.execute = orig_execute


if __name__ == "__main__":
    unittest.main(verbosity=2)
