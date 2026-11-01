"""
Bikozava — Public Invitation Routes (`app/routes/public.py`)

Routes:
- `GET /` : Redirects to the flagship demo invitation (`/ismail_shrin`)
- `GET /<slug>` : Renders the reusable wedding invitation engine for `<slug>`
  - Supports 3-language user view switching via `?lang=ku`, `?lang=ar`, `?lang=en`
  - Computes wedding calendar grid (`calendar_data`), Google Calendar deep link,
    and `.ics` download link (`/<slug>/calendar.ics`)
  - Supports both uploaded MP3/WAV audio (`music_source_type == 'upload'`) and
    custom YouTube wedding music (`music_source_type == 'youtube'`)
- `GET /<slug>/calendar.ics` : Generates an iCalendar (`.ics`) file for Apple/Outlook/Phone calendars
- `POST /<slug>/rsvp` : Submits a guest RSVP response with CSRF protection, input validation, and rate limiting
- `GET /health` : Production healthcheck endpoint
"""

from __future__ import annotations

import calendar as pycalendar
import hashlib
import hmac
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ..database import get_db
from ..flask_compat import (
    Blueprint,
    Response,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from ..i18n import (
    SUPPORTED_LANGUAGES,
    get_ui_strings,
    localize_field,
    normalize_lang,
)
from ..security import (
    clean_text,
    extract_youtube_video_id,
    get_client_ip,
    get_current_admin,
    is_rsvp_rate_limited,
    is_valid_slug,
    verify_csrf_token,
)

public_bp = Blueprint("public", __name__)


def _format_human_date(date_str: str) -> str:
    """Convert YYYY-MM-DD (e.g. '2026-11-21') into '21 November 2026' while preserving custom strings."""
    raw = (date_str or "").strip()
    try:
        dt = datetime.strptime(raw[:10], "%Y-%m-%d")
        return f"{dt.day} {dt.strftime('%B %Y')}"
    except Exception:
        return raw


def _build_calendar_data(date_str: str, time_str: str, title: str, venue: str, map_url: str, slug: str) -> Dict[str, Any]:
    """
    Build visual month calendar grid (weeks list, highlighted day) and Google Calendar URL
    for the `CALENDAR` section.
    """
    raw_date = (date_str or "2026-11-21").strip()[:10]
    try:
        dt = datetime.strptime(raw_date, "%Y-%m-%d")
    except Exception:
        dt = datetime(2026, 11, 21)

    hour, minute = 19, 0
    if time_str and ":" in time_str:
        try:
            parts = time_str.strip().split(":")
            hour = int(parts[0])
            minute = int(parts[1][:2])
        except Exception:
            hour, minute = 19, 0

    start_dt = dt.replace(hour=hour, minute=minute, second=0)
    end_dt = start_dt + timedelta(hours=4)

    cal = pycalendar.Calendar(firstweekday=6)
    weeks = cal.monthdayscalendar(dt.year, dt.month)

    gcal_dates = f"{start_dt.strftime('%Y%m%dT%H%M%S')}/{end_dt.strftime('%Y%m%dT%H%M%S')}"
    details_text = f"Wedding Celebration of {title} at {venue}."
    if map_url:
        details_text += f" Google Maps: {map_url}"

    gcal_params = urllib.parse.urlencode(
        {
            "action": "TEMPLATE",
            "text": f"{title} — Wedding Celebration",
            "dates": gcal_dates,
            "details": details_text,
            "location": venue or "Crystal Hall",
        }
    )
    google_calendar_url = f"https://www.google.com/calendar/render?{gcal_params}"

    month_names_ku = {
        1: "کانوونا دووێ",
        2: "شوبات",
        3: "ئادار",
        4: "نیسان",
        5: "گولان",
        6: "حوزەیران",
        7: "تیرمەهـ",
        8: "تەباخ",
        9: "ئەیلول",
        10: "چریا ئێکێ",
        11: "چریا دووێ (November)",
        12: "کانوونا ئێکێ",
    }
    month_names_ar = {
        1: "يناير",
        2: "فبراير",
        3: "مارس",
        4: "أبريل",
        5: "مايو",
        6: "يونيو",
        7: "يوليو",
        8: "أغسطس",
        9: "سبتمبر",
        10: "أكتوبر",
        11: "نوفمبر (November)",
        12: "ديسمبر",
    }

    return {
        "year": dt.year,
        "month": dt.month,
        "day": dt.day,
        "month_name_en": dt.strftime("%B %Y"),
        "month_name_ku": f"{month_names_ku.get(dt.month, dt.strftime('%B'))} {dt.year}",
        "month_name_ar": f"{month_names_ar.get(dt.month, dt.strftime('%B'))} {dt.year}",
        "time_12h": start_dt.strftime("%I:%M %p").lstrip("0"),
        "weeks": weeks,
        "google_calendar_url": google_calendar_url,
        "ics_url": f"/{slug}/calendar.ics",
    }


def _parse_schedule_lines(text_val: str) -> List[Dict[str, str]]:
    """Parse schedule lines like `7:00 — بخێرهاتن` into structured timeline items."""
    items: List[Dict[str, str]] = []
    for line in (text_val or "").splitlines():
        line = line.strip()
        if not line:
            continue
        for sep in ("—", "–", "-"):
            if sep in line:
                parts = line.split(sep, 1)
                items.append({"time": parts[0].strip(), "label": parts[1].strip()})
                break
        else:
            items.append({"time": "", "label": line})
    return items


@public_bp.route("/health", methods=["GET"])
def health() -> Any:
    return jsonify({"status": "ok", "service": "bikozava"})


@public_bp.route("/healthz", methods=["GET"])
def healthz() -> Any:
    """Render.com & UptimeRobot zero-downtime health check endpoint."""
    db = get_db()
    row = db.fetchone("SELECT COUNT(*) AS cnt FROM templates")
    return {
        "status": "ok",
        "service": "bikozava",
        "templates_loaded": int((row or {}).get("cnt", 0)),
    }, 200


@public_bp.route("/", methods=["GET"])
def home() -> Any:
    """Redirect root visitors to the featured Ismail & Shrin demo invitation or first published wedding."""
    db = get_db()
    demo = db.fetchone(
        "SELECT slug FROM invitations WHERE slug = 'ismail_shrin' AND is_published = 1"
    )
    if demo:
        return redirect(url_for("public.view_invitation", slug=demo["slug"]))

    first_pub = db.fetchone(
        "SELECT slug FROM invitations WHERE is_published = 1 ORDER BY id ASC LIMIT 1"
    )
    if first_pub:
        return redirect(url_for("public.view_invitation", slug=first_pub["slug"]))

    return redirect(url_for("admin.login"))


@public_bp.route("/<string:slug>/calendar.ics", methods=["GET"])
def download_ics(slug: str) -> Any:
    """Serve downloadable .ics calendar file for Apple Calendar / Outlook / mobile calendars."""
    clean_slug = (slug or "").strip().lower()
    if not is_valid_slug(clean_slug):
        abort(404, "Invitation not found.")

    db = get_db()
    inv = db.fetchone("SELECT * FROM invitations WHERE slug = ?", (clean_slug,))
    if not inv or (not inv.get("is_published") and not get_current_admin()):
        abort(404, "Invitation not found.")

    raw_date = (inv.get("wedding_date") or "2026-11-21").strip()[:10]
    try:
        dt = datetime.strptime(raw_date, "%Y-%m-%d")
    except Exception:
        dt = datetime(2026, 11, 21)

    start_dt = dt.replace(hour=19, minute=0, second=0)
    end_dt = start_dt + timedelta(hours=4)

    couple = f"{inv.get('groom_name_en') or inv.get('groom_name_ku')} & {inv.get('bride_name_en') or inv.get('bride_name_ku')}"
    venue = inv.get("venue_name_en") or inv.get("venue_name_ku") or "Crystal Hall"
    map_url = inv.get("map_url") or ""

    ics_content = "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Bikozava Wedding Platform//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "BEGIN:VEVENT",
            f"UID:wedding-{clean_slug}@bikozava.com",
            f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{couple} — Wedding Celebration",
            f"LOCATION:{venue}",
            f"DESCRIPTION:Wedding celebration of {couple} at {venue}. Map: {map_url}",
            "END:VEVENT",
            "END:VCALENDAR",
            "",
        ]
    )
    return Response(
        ics_content,
        status=200,
        headers={"Content-Disposition": f'attachment; filename="{clean_slug}_wedding.ics"'},
        mimetype="text/calendar; charset=utf-8",
    )


@public_bp.route("/<string:slug>", methods=["GET"])
def view_invitation(slug: str) -> Any:
    """
    Reusable Public Wedding Invitation Engine (`/<slug>`).
    Loads wedding metadata, selected template, theme settings, ordered enabled
    sections, gallery media, calendar grid, and 3-language localized copy from the database.
    """
    clean_slug = (slug or "").strip().lower()
    if not is_valid_slug(clean_slug):
        abort(404, "Invitation not found.")

    db = get_db()
    invitation = db.fetchone("SELECT * FROM invitations WHERE slug = ?", (clean_slug,))
    if not invitation:
        abort(404, "Invitation not found.")

    is_published = bool(invitation.get("is_published"))
    admin_user = get_current_admin()
    preview_token = request.args.get("preview_token", "")
    stored_token = str(invitation.get("preview_token") or "")
    valid_token = bool(
        preview_token
        and stored_token
        and hmac.compare_digest(preview_token, stored_token)
    )
    is_preview_mode = bool(request.args.get("preview") == "1" or valid_token)

    if not is_published and not admin_user and not valid_token:
        abort(404, "This invitation is not currently published.")

    if is_published and not is_preview_mode and not admin_user:
        db.execute(
            "UPDATE invitations SET views_count = views_count + 1 WHERE id = ?",
            (invitation["id"],),
        )
        db.commit()

    req_lang = request.args.get("lang", "").strip().lower()
    if req_lang in SUPPORTED_LANGUAGES:
        lang = req_lang
        session[f"lang_{clean_slug}"] = lang
    else:
        lang = normalize_lang(
            session.get(f"lang_{clean_slug}", ""),
            fallback=invitation.get("default_language", "ku"),
        )

    lang_meta = SUPPORTED_LANGUAGES[lang]
    ui = get_ui_strings(lang)

    # Allow live template preview override via `?template=...` for admin/preview testing
    override_template_code = request.args.get("template", "").strip().lower()
    active_template_code = override_template_code or invitation.get("template_code") or "magical_butterfly"

    template = db.fetchone(
        "SELECT * FROM templates WHERE code = ?",
        (active_template_code,),
    )
    if not template:
        template = db.fetchone("SELECT * FROM templates WHERE code = 'magical_butterfly'") or {
            "code": "magical_butterfly",
            "category": "luxury",
            "has_butterfly_opening": True,
            "default_theme": {},
        }

    raw_sections = db.fetchall(
        """
        SELECT * FROM invitation_sections
        WHERE invitation_id = ? AND is_enabled = 1
        ORDER BY sort_order ASC, id ASC
        """,
        (invitation["id"],),
    )

    gallery_uploads = db.fetchall(
        """
        SELECT * FROM media_uploads
        WHERE invitation_id = ? AND media_role = 'gallery'
        ORDER BY sort_order ASC, id ASC
        """,
        (invitation["id"],),
    )

    sections: List[Dict[str, Any]] = []
    has_opening_section = False
    for sec in raw_sections:
        stype = sec["section_type"]
        if stype == "opening_card":
            has_opening_section = True
        cjson = sec.get("content_json") if isinstance(sec.get("content_json"), dict) else {}
        loc_title = localize_field(sec, "title", lang)
        loc_subtitle = localize_field(sec, "subtitle", lang)
        loc_content = localize_field(sec, "content", lang)

        schedule_items: List[Dict[str, str]] = []
        if stype == "schedule":
            if lang == "ku" and sec.get("content_ku"):
                schedule_items = _parse_schedule_lines(sec["content_ku"])
            elif isinstance(cjson.get("items"), list) and cjson["items"]:
                for it in cjson["items"]:
                    t_label = (
                        it.get(f"title_{lang}")
                        or it.get("title_ku")
                        or it.get("title_en")
                        or ""
                    )
                    schedule_items.append({"time": it.get("time", ""), "label": t_label})
            else:
                schedule_items = _parse_schedule_lines(loc_content)

        sections.append(
            {
                "id": sec["id"],
                "type": stype,
                "title": loc_title,
                "subtitle": loc_subtitle,
                "content": loc_content,
                "content_ku": sec.get("content_ku", ""),
                "content_ar": sec.get("content_ar", ""),
                "content_en": sec.get("content_en", ""),
                "json": cjson,
                "schedule_items": schedule_items,
            }
        )

    gallery_items: List[Dict[str, str]] = []
    seen_urls = set()
    for g_up in gallery_uploads:
        url = g_up["file_path"]
        if url not in seen_urls:
            seen_urls.add(url)
            gallery_items.append(
                {
                    "url": url,
                    "thumb": g_up.get("thumb_path") or url,
                    "caption": localize_field(g_up, "caption", lang),
                }
            )
    for sec in sections:
        if sec["type"] == "gallery":
            for img_obj in sec["json"].get("images", []):
                url = img_obj.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    cap = (
                        img_obj.get(f"caption_{lang}")
                        or img_obj.get("caption_ku")
                        or img_obj.get("caption_en")
                        or ""
                    )
                    gallery_items.append({"url": url, "thumb": url, "caption": cap})

    groom_display = localize_field(invitation, "groom_name", lang) or invitation["groom_name_ku"]
    bride_display = localize_field(invitation, "bride_name", lang) or invitation["bride_name_ku"]
    venue_display = localize_field(invitation, "venue_name", lang) or invitation["venue_name_ku"]
    venue_address = localize_field(invitation, "venue_address", lang) or invitation["venue_address_ku"]
    human_date = _format_human_date(invitation["wedding_date"])
    opening_card_exact_badini = invitation.get("opening_card_text_ku") or "کلیل بکە بو ڤەکرنا داخوازنامێ"

    youtube_video_id = extract_youtube_video_id(invitation.get("music_youtube_url") or "")
    music_source_type = invitation.get("music_source_type") or ("youtube" if youtube_video_id else "upload")

    calendar_data = _build_calendar_data(
        invitation.get("wedding_date", "2026-11-21"),
        invitation.get("wedding_time", "19:00"),
        f"{invitation.get('groom_name_en') or groom_display} & {invitation.get('bride_name_en') or bride_display}",
        venue_display or "Crystal Hall",
        invitation.get("map_url", ""),
        clean_slug,
    )

    return render_template(
        "public/invitation.html",
        invitation=invitation,
        template=template,
        sections=sections,
        has_opening_section=has_opening_section,
        gallery_items=gallery_items,
        groom_display=groom_display,
        bride_display=bride_display,
        venue_display=venue_display,
        venue_address=venue_address,
        human_date=human_date,
        calendar_data=calendar_data,
        music_source_type=music_source_type,
        youtube_video_id=youtube_video_id,
        opening_card_exact_badini=opening_card_exact_badini,
        lang=lang,
        lang_meta=lang_meta,
        supported_languages=SUPPORTED_LANGUAGES,
        ui=ui,
        is_preview_mode=is_preview_mode,
    )


@public_bp.route("/<string:slug>/rsvp", methods=["POST"])
def submit_rsvp(slug: str) -> Any:
    """Record a guest's RSVP for a published invitation with CSRF & spam rate-limit protection."""
    verify_csrf_token()

    clean_slug = (slug or "").strip().lower()
    if not is_valid_slug(clean_slug):
        abort(404, "Invitation not found.")

    db = get_db()
    invitation = db.fetchone(
        "SELECT id, slug, default_language, is_published FROM invitations WHERE slug = ?",
        (clean_slug,),
    )
    if not invitation or (not invitation.get("is_published") and not get_current_admin()):
        abort(404, "Invitation not found.")

    ip_hash = hashlib.sha256(get_client_ip().encode("utf-8")).hexdigest()[:32]
    if is_rsvp_rate_limited(int(invitation["id"]), ip_hash):
        if request.is_json:
            return jsonify({"ok": False, "error": "Too many RSVP submissions. Please try again later."}), 429
        abort(429, "Too many RSVP submissions.")

    payload = request.get_json(silent=True) if request.is_json else request.form
    guest_name = clean_text((payload or {}).get("guest_name"), max_len=150)
    guest_phone = clean_text((payload or {}).get("guest_phone"), max_len=50)
    attending = clean_text((payload or {}).get("attending") or "yes", max_len=16).lower()
    if attending not in ("yes", "no", "maybe"):
        attending = "yes"

    try:
        guests_count = int((payload or {}).get("guests_count") or 1)
    except ValueError:
        guests_count = 1
    guests_count = max(1, min(20, guests_count))

    message = clean_text((payload or {}).get("message"), max_len=1000)
    lang = normalize_lang((payload or {}).get("language", invitation.get("default_language", "ku")))

    if not guest_name or len(guest_name) < 2:
        if request.is_json:
            return jsonify({"ok": False, "error": "Please enter your name."}), 400
        return redirect(url_for("public.view_invitation", slug=clean_slug, lang=lang))

    db.insert(
        """
        INSERT INTO rsvp_responses (
            invitation_id, guest_name, guest_phone, attending,
            guests_count, message, language, ip_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            invitation["id"],
            guest_name,
            guest_phone,
            attending,
            guests_count,
            message,
            lang,
            ip_hash,
        ),
    )

    ui = get_ui_strings(lang)
    if request.is_json:
        return jsonify({"ok": True, "message": ui["rsvp_success"]})

    return redirect(url_for("public.view_invitation", slug=clean_slug, lang=lang, rsvp="sent"))

