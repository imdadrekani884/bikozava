# Bikozava — Luxury Multilingual Wedding Invitation Platform

**Bikozava** (`bikozava.com`) is a complete, production-ready digital wedding invitation platform built with Python (Flask / WSGI), PostgreSQL / Supabase (with zero-configuration SQLite fallback for local development), a secure mobile-first Admin Studio, a flexible 17-type Section Builder, 26 extensible invitation templates across two categories (**Minimal** and **Complex / Luxury**), and **3-language guest support** (**Pure Badini Kurdish** in Arabic script `RTL`, **Arabic** `RTL`, and **English** `LTR`).

Each wedding invitation is stored in the database and served dynamically from a single reusable invitation engine at its own clean public slug URL:

* `https://bikozava.com/ismail_shrin` (Pre-seeded flagship demo)

* `https://bikozava.com/ahmad_lavin`

* `https://bikozava.com/berivan_azad`

## Quick Start on Windows (PowerShell or Command Prompt)

### Option 1: One-Click Windows Launcher (Fastest)

1. Extract `bikozava-wedding-platform.zip` to any folder (e.g. `C:\bikozava`).

2. Double-click **`start_windows.bat`** (or run `.\start_windows.ps1` in PowerShell).

   * It automatically creates the `.venv` virtual environment, installs all Windows-compatible packages (`Flask`, `waitress`, `Pillow`, `python-magic-bin`, `argon2-cffi`, `bcrypt`), creates `.env` with a fresh cryptographic `SECRET_KEY`, seeds the database, and launches the server on `http://localhost:8000`.

### Option 2: Manual Setup in Windows PowerShell

Open **PowerShell** inside the extracted `bikozava` folder and run:

```
# 1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# (If PowerShell blocks script execution, run this once first:)
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 2. Install Windows-compatible dependencies
pip install -r requirements.txt

# 3. Copy .env.example to .env
Copy-Item .env.example .env

# 4. Generate a secure SECRET_KEY (optional — or edit .env in Notepad/VS Code)
python -c "import secrets; print(secrets.token_hex(32))"

# 5. Start the Bikozava server (runs on Waitress WSGI server on Windows)
python run.py

```

### Option 3: Manual Setup in Windows Command Prompt (`cmd.exe`)

```
cd bikozava
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
copy .env.example .env
python run.py

```

Once started, open your browser to:

* **Public Demo Invitation (Kurdish Badini — Default)**: `http://localhost:8000/ismail_shrin`

* **Public Demo Invitation (Arabic)**: `http://localhost:8000/ismail_shrin?lang=ar`

* **Public Demo Invitation (English)**: `http://localhost:8000/ismail_shrin?lang=en`

* **Admin Studio Login**: `http://localhost:8000/admin/login`

  * **Default Username**: `admin`

  * **Default Password**: `ChangeThisStrongPassword!2026` (configured in `.env`)

## Quick Setup on Linux / macOS

```
cd bikozava
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 run.py

```

## Key Features

### 1. Reusable Public Invitation Engine & 3-Language Guest View

* **Dynamic Slug Routing (`/<slug>`)**: Loads couple names, wedding date, venue, Google Maps URL, selected template, custom color palette, Google Fonts, media assets, and ordered sections from the database without exposing internal database IDs.

* **3-Language Guest Switcher (`?lang=ku`, `?lang=ar`, `?lang=en`)**:

  * **Kurdish Badini (`ku`, RTL — Default)**: Written in authentic Pure Badini Kurdish using Arabic script (never Sorani).

  * **Arabic (`ar`, RTL)**: Complete royal Arabic localization.

  * **English (`en`, LTR)**: Complete editorial English localization.

* **13-Step Luxury 3D Magical Butterfly Opening Experience**:

  * First screen displays a realistic ivory paper & champagne-gold embossed card centered on the mobile screen with a 3D sculpted butterfly resting on the seal and the exact required Badini prompt:
    `کلیل بکە بو ڤەکرنا داخوازنامێ`

  * When tapped:

     1. Card gently floats with realistic depth.

     2. Butterfly naturally flaps its wings.

     3. Golden particles appear and swirl.

     4. Card opens like a real gatefold paper invitation.

     5. Two paper panels unfold smoothly in 3D space.

     6. Butterfly spreads its wings.

     7. Butterfly lifts from the card with dynamic shadow falloff.

     8. Butterfly flies toward the camera.

     9. Butterfly gracefully flies upward and away.

    10. Camera rig follows the butterfly with cinematic depth.

    11. Warm golden light blooms across the screen.

    12. Wedding invitation content is revealed.

    13. Normal vertical scrolling is unlocked.

  * Automatically respects `prefers-reduced-motion: reduce`.

### 2. Default Pre-Seeded Demo Invitation (`/ismail_shrin`)

Immediately available upon startup:

* **Groom & Bride**: `Ismail & Shrin`

* **Date**: `21 November 2026` (with live countdown timer)

* **Venue**: `Crystal Hall`

* **Google Maps**: `https://maps.app.goo.gl/LYHw6XCJdNMJyQK48?g_st=ac`

* **Template**: `Magical Butterfly` (`magical_butterfly`)

* **Exact Evening Schedule (`بەرنامێ شەڤێ`)**:

  * `7:00 — بخێرهاتن`

  * `7:30 — هاتنا بیکو زاڤا`

  * `8:00 — شیڤ خارن`

  * `9:00 — دیلان`

* **Audio**: Bundled Kurdish/Eastern-inspired instrumental serenade (`bikozava_kurdish_serenade.wav`) that starts only after guest interaction, with a floating mute/unmute control and session memory.

### 3. Mobile-First Admin Studio & Flexible Section Builder

* **Routes**:

  * `/admin` & `/admin/login`: Rate-limited admin authentication

  * `/admin/dashboard`: Overview metrics, invitation cards, one-click Copy Public URL, Publish/Unpublish, Duplicate, Delete, and Create modal

  * `/admin/invitations/<id>/edit`: Full Studio with 3-language editors, template/color/font pickers, media uploader, and live Mobile (`390px`) & Desktop preview simulator

  * `/admin/templates`: Visual showcase of all 26 templates

  * `/admin/invitations/<id>/rsvps`: Guest attendance tracker

* **Flexible 17-Type Section Builder**:
  Admins can freely add, remove, enable/disable, duplicate, edit (in all 3 languages), and reorder any combination of:

   1. `opening_card` (Opening Card)

   2. `couple` (Bride & Groom)

   3. `invitation_message` (Invitation Message)

   4. `countdown` (Live Countdown)

   5. `wedding_date` (Wedding Date)

   6. `venue` (Venue)

   7. `google_maps` (Google Maps)

   8. `schedule` (Wedding Schedule)

   9. `gallery` (Photo Gallery)

  10. `love_story` (Love Story)

  11. `family` (Family)

  12. `rsvp` (RSVP Form)

  13. `video` (Highlight Video)

  14. `custom_text` (Custom Text)

  15. `contact` (Contact)

  16. `music` (Background Music)

  17. `closing` (Closing)

### 4. Two Extensible Template Categories (26 Built-In Templates)

* **Minimal Templates (6)**: `minimalism_purple_soft_lavender` (💜 Minimalism Purple Soft Lavender — Watercolor purple roses & lilac blossoms, purple envelope with admin couple photo, single-card gallery viewer, scratch-to-reveal countdown, blooming flower schedule & admin music), `minimal_ivory`, `minimal_champagne`, `modern_white`, `editorial`, `soft_floral`

* **Complex / Luxury & Interactive Templates (20)**: `sara_ahmed_wax_seal_veo` (🕯️ Kurdish Badini Wax Seal & Veo Interactive — Split royal curtain doors with pearl & gold monogram wax seal, 60fps Veo cinematic hero engine over admin couple photo/video with soaring birds & sunset rays, 3D ring calendar, polaroid gallery carousel, floating glass dock & admin music), `champagne_envelope_foil` (✨ Champagne Envelope & Gold Foil — No Photos), `champagne_envelope_photos` (📸 Champagne Envelope & Gold Foil — With Photos), `champagne_envelope_dark` (🌑 Midnight Obsidian & Gold Foil — Dark Mode), `champagne_envelope_dark_photos` (🌙 Midnight Obsidian & Gold Foil — Dark Mode + Photos), `magical_butterfly`, `vertical_cinema_reel` (🎬 9:16 Vertical Cinema Reel), `golden_scratch_reveal` (🪙 Golden Scratch-Off Reveal), `starlight_lantern_glow` (🏮 Tap-to-Glow Sky Lanterns), `moonlit_lake` (🌙 Moonlit Lake), `wedding_train` (🚂 The Wedding Train), `floating_castle` (🏰 Floating Castle), `message_in_a_bottle` (🌊 Message in a Bottle), `royal_luxury`, `golden_palace`, `cinematic_garden`, `luxury_floral`, `traditional_kurdish_luxury`, `black_and_gold`, `romantic_crystal`

## Project Structure

```
bikozava/
├── app/
│   ├── __init__.py                 # Application factory, error handlers, context processors
│   ├── config.py                   # Environment configuration (.env loader)
│   ├── database.py                 # Unified PostgreSQL/Supabase + SQLite parameterized DB layer
│   ├── flask_compat.py             # Native Flask + standalone WSGI compatibility engine
│   ├── i18n.py                     # 3-Language localization (Badini Kurdish, Arabic, English)
│   ├── security.py                 # Argon2/bcrypt/scrypt hashing, CSRF, rate limiting, upload validation
│   ├── seed.py                     # Idempotent seeder (Admin, 26 templates, Ismail & Shrin demo, audio/images)
│   ├── routes/
│   │   ├── admin.py                # Protected admin routes, CRUD, section builder, media uploads
│   │   └── public.py               # Public /<slug> engine, 3-language switcher, RSVP endpoint
│   ├── static/
│   │   ├── audio/                  # Bundled instrumental wedding audio + admin upload instructions
│   │   ├── css/
│   │   │   ├── admin.css           # Mobile-first Admin Studio stylesheet
│   │   │   └── invitation.css      # Mobile-first Public Invitation & 3D Butterfly stylesheet
│   │   ├── img/demo/               # Generated WebP demo portraits & gallery images
│   │   ├── js/
│   │   │   ├── admin.js            # Admin Studio, preview switcher, clipboard helper
│   │   │   └── invitation.js       # 13-step 3D butterfly choreography, particles, audio & countdown
│   │   └── uploads/                # Validated & optimized user uploads (avatars, gallery, music, video, thumbs)
│   └── templates/
│       ├── admin/                  # Admin Jinja2 templates (base, login, dashboard, editor, templates, rsvps)
│       ├── errors/                 # Safe production HTTP error page
│       └── public/
│           ├── invitation.html             # Reusable 3-language public wedding invitation template
│           ├── purple_soft_lavender.html   # Minimalism Purple Soft Lavender interactive template
│           └── wax_seal_veo_cinema.html    # Kurdish Badini Wax Seal & Veo interactive template
├── migrations/
│   └── 001_initial_schema.sql      # Complete PostgreSQL / Supabase database schema
├── tests/
│   └── test_bikozava.py            # Automated end-to-end test suite
├── .env.example                    # Environment variable template (no hardcoded secrets)
├── .gitignore                      # Git ignore rules
├── Dockerfile                      # Production container definition
├── gunicorn.conf.py                # Linux Gunicorn WSGI server configuration
├── Procfile                        # PaaS process declaration
├── requirements.txt                # Windows/Linux/macOS Python package dependencies
├── run.py                          # Cross-platform Waitress / Flask server entrypoint
├── start_windows.bat               # One-click Windows Command Prompt / Explorer launcher
├── start_windows.ps1               # Windows PowerShell launcher
├── wsgi.py                         # Production WSGI entrypoint
└── README.md                       # Complete setup, database, security & deployment guide

```

## Database Setup (Supabase / PostgreSQL vs Local SQLite)

### Option A: Local SQLite (Zero-Config Default on Windows)

By default, `.env.example` uses `DATABASE_URL=sqlite:///instance/bikozava.db`. On Windows, Bikozava automatically creates `instance\bikozava.db` and seeds the 26 templates and the **Ismail & Shrin** demo wedding on first launch.

### Option B: Supabase / PostgreSQL (Cloud Production)

1. Create a new Supabase project at `https://supabase.com` (or provision a managed PostgreSQL 15+ instance).

2. Open the **Supabase SQL Editor** and run the contents of `migrations/001_initial_schema.sql` (or let Bikozava run it automatically on startup).

3. Copy your Supabase PostgreSQL connection string into `.env`:

   ```
   DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require
   
   ```

4. Start the server (`python run.py`)—`app/seed.py` will idempotently seed the templates and demo wedding into PostgreSQL.

## Running the Automated Test Suite on Windows

```
python -m unittest discover -s tests -v

```

## Production Serving on Windows vs Linux

* **Windows Server / Local Production (Waitress)**:

  ```
  waitress-serve --host=0.0.0.0 --port=8000 --threads=6 wsgi:app
  
  ```

  (Or simply run `python run.py`, which automatically uses Waitress when `FLASK_DEBUG=0`.)

* **Linux VPS (Gunicorn + Nginx)**:

  ```
  gunicorn -c gunicorn.conf.py wsgi:app
  
  ```

## Security Architecture Notes

1. **Password Hashing**: Uses **Argon2id** (`argon2-cffi`) or **bcrypt** when installed, with automatic cryptographic **scrypt** (`hashlib.scrypt`, `N=16384, r=8, p=1`) fallback and constant-time digest comparison (`hmac.compare_digest`).

2. **CSRF Protection**: Every state-changing `POST` request across the Admin Studio and public RSVP form validates a cryptographic session CSRF token.

3. **Login Rate Limiting**: Failed login attempts are tracked per IP address in the `login_attempts` table and blocked with HTTP `429 Too Many Requests` once the threshold is reached.

4. **SQL Injection Prevention**: Every database operation in `app/database.py` uses strict parameterized queries (`?` / `%s` placeholders).

5. **Upload Validation & Optimization**: Uploaded files are validated against extension whitelists, magic-byte signatures (blocking PHP, ELF, PE, and script headers), and Pillow image verification. Valid images are re-encoded into clean WebP files with generated thumbnails (`app/static/uploads/thumbs/`) and stripped of EXIF metadata.

6. **Strict Slug Sanitization & Draft Isolation**: Slugs are sanitized against path traversal and reserved routes. Unpublished invitations return `404` to anonymous visitors and can only be previewed by a logged-in admin or via a cryptographic `preview_token`.

7. **HTTP Security Headers**: Every response includes `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy`, and `Permissions-Policy`.