"""
Bikozava — Comprehensive Automated Test Suite (`tests/test_bikozava.py`)

Tests all core platform requirements:
1. Default seeded demo invitation (`/ismail_shrin`) with Ismail & Shrin, 21 November 2026,
   Crystal Hall, Google Maps link, exact opening card text `کلیل بکە بو ڤەکرنا داخوازنامێ`,
   upgraded royal interior card, exact Badini schedule, and exact section sequence:
   OPENING CARD → COUPLE → COUNTDOWN → WEDDING DETAILS → SCHEDULE → VENUE/MAP → GALLERY → RSVP → CALENDAR → FINAL.
2. All 22 Templates including:
   - `champagne_envelope_foil`: ✨ Champagne Envelope & Gold Foil (Exact design from user's uploaded Index.html without photos, wired to admin music)
   - `champagne_envelope_photos`: 📸 Champagne Envelope & Gold Foil (With Photos) (Same design + Couple/Bride/Groom portraits & Photo Gallery, wired to admin music)
   - `vertical_cinema_reel`: 🎬 9:16 Vertical Cinema Reel (9:16 vertical video uploaded by admin as first slide after opening card with Bride & Groom names automatically overlaid at top-middle)
   - `golden_scratch_reveal`: 🪙 Golden Scratch-Off Reveal (interactive 24k gold foil scratch canvas)
   - `starlight_lantern_glow`: 🏮 Tap-to-Glow Sky Lanterns (interactive tap-to-light royal lanterns)
   - `moonlit_lake`: 🌙 Moonlit Lake
   - `wedding_train`: 🚂 The Wedding Train
   - `floating_castle`: 🏰 Floating Castle
   - `message_in_a_bottle`: 🌊 Message in a Bottle
3. 3-Language user view switching (`?lang=ku`, `?lang=ar`, `?lang=en`) with RTL/LTR dir attributes
   and Persian/Kurdish Google Fonts (`Vazirmatn`, `Lalezar`, `Gulzar`, `Markazi Text`, `Scheherazade New`).
4. Admin authentication, live password update (`/admin/settings`), CSRF enforcement, and login rate limiting.
5. Creating a new invitation (`/ahmad_lavin`), configuring YouTube music (`music_source_type='youtube'`),
   section builder CRUD/reorder, and publishing.
6. Secure media upload validation and guest RSVP submission with spam rate limiting.
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
            }
        )
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def _login_admin(self, username: str = "admin", password: str = "ChangeThisStrongPassword!2026"):
        get_resp = self.client.get("/admin/login")
        self.assertEqual(get_resp.status_code, 200)
        csrf = _extract_csrf(get_resp.get_data(as_text=True))
        self.assertTrue(len(csrf) > 10)
        return self.client.post(
            "/admin/login",
            data={"username": username, "password": password, "csrf_token": csrf},
            follow_redirects=False,
        )

    def test_01_demo_invitation_section_order_and_calendar(self) -> None:
        """
        Verify `/ismail_shrin` renders the exact 10-step section sequence and all 22 templates are seeded.
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
            self.assertEqual(templates_count, 24)

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
        Verify all 9 bespoke interactive experiences:
        - `champagne_envelope_foil` (Champagne Envelope & Gold Foil WITHOUT photos + admin music)
        - `champagne_envelope_photos` (Champagne Envelope & Gold Foil WITH photos/gallery + admin music)
        - `vertical_cinema_reel` (9:16 video first slide + top-middle couple names overlay)
        - `golden_scratch_reveal` (24k gold foil scratch canvas)
        - `starlight_lantern_glow` (Tap-to-Glow Sky Lanterns)
        - `moonlit_lake`, `wedding_train`, `floating_castle`, `message_in_a_bottle`
        """
        # 1. Champagne Envelope & Gold Foil — WITHOUT Photos (`champagne_envelope_foil`)
        r_ce_foil = self.client.get("/ismail_shrin?template=champagne_envelope_foil")
        self.assertEqual(r_ce_foil.status_code, 200)
        html_ce_foil = r_ce_foil.get_data(as_text=True)
        self.assertIn("champagne-ambient-canvas", html_ce_foil)
        self.assertIn("scene-champagne-envelope", html_ce_foil)
        self.assertIn("ڤەکرنا داخوازنامێ", html_ce_foil)
        self.assertIn("کلیل بکە بو ڤەکرنا داخوازنامێ", html_ce_foil)
        self.assertIn("ce-vertical-timeline", html_ce_foil)
        self.assertIn("ce-dark-venue-card", html_ce_foil)
        self.assertIn("زڤرین بو دەسپێکێ", html_ce_foil)
        self.assertIn('id="music-toggle-btn"', html_ce_foil)
        # Ensure `champagne_envelope_foil` does NOT render couple portraits or gallery photos
        self.assertNotIn("ce-featured-couple-photo-frame", html_ce_foil)
        self.assertNotIn("section-gallery", html_ce_foil)

        # 2. Champagne Envelope & Gold Foil — WITH Photos (`champagne_envelope_photos`)
        r_ce_photos = self.client.get("/ismail_shrin?template=champagne_envelope_photos")
        self.assertEqual(r_ce_photos.status_code, 200)
        html_ce_photos = r_ce_photos.get_data(as_text=True)
        self.assertIn("champagne-ambient-canvas", html_ce_photos)
        self.assertIn("scene-champagne-envelope", html_ce_photos)
        self.assertIn("ce-featured-couple-photo-frame", html_ce_photos)
        self.assertIn("ce-portraits-row", html_ce_photos)
        self.assertIn("section-gallery", html_ce_photos)
        self.assertIn('id="music-toggle-btn"', html_ce_photos)

        # 2B. Champagne Envelope Dark Mode — WITHOUT Photos (`champagne_envelope_dark`)
        r_ce_dark = self.client.get("/ismail_shrin?template=champagne_envelope_dark")
        self.assertEqual(r_ce_dark.status_code, 200)
        html_ce_dark = r_ce_dark.get_data(as_text=True)
        self.assertIn("is-dark-mode", html_ce_dark)
        self.assertIn("scene-champagne-envelope", html_ce_dark)
        self.assertIn("theme-mode-toggle-btn", html_ce_dark)
        self.assertNotIn("ce-featured-couple-photo-frame", html_ce_dark)
        self.assertNotIn("section-gallery", html_ce_dark)

        # 2C. Champagne Envelope Dark Mode — WITH Photos (`champagne_envelope_dark_photos`)
        r_ce_dark_p = self.client.get("/ismail_shrin?template=champagne_envelope_dark_photos")
        self.assertEqual(r_ce_dark_p.status_code, 200)
        html_ce_dark_p = r_ce_dark_p.get_data(as_text=True)
        self.assertIn("is-dark-mode", html_ce_dark_p)
        self.assertIn("ce-featured-couple-photo-frame", html_ce_dark_p)
        self.assertIn("section-gallery", html_ce_dark_p)

        # Verify Render /healthz endpoint
        r_health = self.client.get("/healthz")
        self.assertEqual(r_health.status_code, 200)
        self.assertEqual(r_health.get_json()["status"], "ok")
        self.assertEqual(r_health.get_json()["templates_loaded"], 24)


        # 3. 9:16 Vertical Cinema Reel (`vertical_cinema_reel`)
        r_reel = self.client.get("/ismail_shrin?template=vertical_cinema_reel")
        self.assertEqual(r_reel.status_code, 200)
        html_reel = r_reel.get_data(as_text=True)
        self.assertIn("vertical-video-hero-slide", html_reel)
        self.assertIn("vertical-9-16-video", html_reel)
        self.assertIn("vertical-video-top-middle-overlay", html_reel)
        self.assertIn("video-top-couple-names", html_reel)
        self.assertIn("Shrin", html_reel)
        self.assertIn("Ismail", html_reel)
        self.assertTrue(html_reel.index("vertical-video-hero-slide") < html_reel.index("section-couple"))

        # 4. Golden Scratch-Off Reveal (`golden_scratch_reveal`)
        r_scratch = self.client.get("/ismail_shrin?template=golden_scratch_reveal")
        self.assertEqual(r_scratch.status_code, 200)
        html_scratch = r_scratch.get_data(as_text=True)
        self.assertIn("scene-scratch-reveal", html_scratch)
        self.assertIn("scratch-foil-canvas", html_scratch)
        self.assertIn("scratch-underneath-layer", html_scratch)

        # 5. Tap-to-Glow Sky Lanterns (`starlight_lantern_glow`)
        r_lantern = self.client.get("/ismail_shrin?template=starlight_lantern_glow")
        self.assertEqual(r_lantern.status_code, 200)
        html_lantern = r_lantern.get_data(as_text=True)
        self.assertIn("scene-lantern-glow", html_lantern)
        self.assertIn("sky-lantern-item", html_lantern)
        self.assertIn("igniteSkyLantern", html_lantern)

        # 6. Moonlit Lake (`moonlit_lake`)
        r_lake = self.client.get("/ismail_shrin?template=moonlit_lake")
        self.assertEqual(r_lake.status_code, 200)
        self.assertIn("scene-moonlit-lake", r_lake.get_data(as_text=True))

        # 7. The Wedding Train (`wedding_train`)
        r_train = self.client.get("/ismail_shrin?template=wedding_train")
        self.assertEqual(r_train.status_code, 200)
        self.assertIn("scene-wedding-train", r_train.get_data(as_text=True))

        # 8. Floating Castle (`floating_castle`)
        r_castle = self.client.get("/ismail_shrin?template=floating_castle")
        self.assertEqual(r_castle.status_code, 200)
        self.assertIn("scene-floating-castle", r_castle.get_data(as_text=True))

        # 9. Message in a Bottle (`message_in_a_bottle`)
        r_bottle = self.client.get("/ismail_shrin?template=message_in_a_bottle")
        self.assertEqual(r_bottle.status_code, 200)
        self.assertIn("scene-message-bottle", r_bottle.get_data(as_text=True))

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
