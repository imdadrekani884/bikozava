"""
Bikozava — Public Invitation Routes (`app/routes/public.py`)

Routes:
- `GET /` : Renders the 3-language luxury editorial homepage (`bikozava.com`) showing ONLY the Admin-selected templates
- `GET /templates` : Redirects unauthenticated visitors to `/#signature-editions` so users only see Admin-selected templates
- `GET /<slug>` : Renders the reusable wedding invitation engine for `<slug>`
  - Supports 3-language user view switching via `?lang=ku`, `?lang=ar`, `?lang=en`
  - Strips internal columns (`preview_token`, `created_by`) before rendering
  - Prevents arbitrary URL parameter tampering on couple names (only loads Admin-configured example names for showcase previews or logged-in Admin)
- `GET /<slug>/calendar.ics` : Generates an iCalendar (`.ics`) file with CRLF injection sanitization
- `POST /<slug>/rsvp` : Submits a guest RSVP response with CSRF protection, honeypot bot trap, HTML tag stripping, duplicate prevention, and rate limiting
- `GET /health` & `GET /healthz` : Production healthcheck endpoints
"""

from __future__ import annotations

import calendar as pycalendar
import hashlib
import hmac
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from ..database import get_db
from ..seed import get_homepage_config
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
    clean_ics_text,
    clean_phone,
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


@public_bp.route("/favicon.ico", methods=["GET"])
def favicon() -> Any:
    """Serve a luxury gold emblem SVG favicon so browsers never log 404 on /favicon.ico."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="16" fill="#171310"/>'
        '<circle cx="32" cy="32" r="24" fill="none" stroke="#C8A253" stroke-width="2"/>'
        '<path d="M32 14L37 26L49 26L39 34L43 46L32 38L21 46L25 34L15 26L27 26Z" fill="#C8A253"/>'
        '</svg>'
    )
    return Response(svg, status=200, mimetype="image/svg+xml")


@public_bp.route("/", methods=["GET"])
def home() -> Any:
    """
    Render the luxury editorial Bikozava homepage (`bikozava.com`).
    Loads ONLY the Admin-curated featured templates and example couple names from `homepage_config`.
    """
    db = get_db()
    req_lang = request.args.get("lang", "").strip().lower()
    if req_lang in SUPPORTED_LANGUAGES:
        lang = req_lang
        session["home_lang"] = lang
    else:
        lang = normalize_lang(session.get("home_lang", ""), fallback="ku")

    lang_meta = SUPPORTED_LANGUAGES[lang]
    ui = get_ui_strings(lang)

    all_templates = db.fetchall("SELECT * FROM templates WHERE is_active = TRUE ORDER BY sort_order ASC")
    templates_by_code = {t["code"]: t for t in all_templates}

    homepage_cfg = get_homepage_config(db)
    featured_showcase: List[Dict[str, Any]] = []
    for item in homepage_cfg.get("featured_items", []):
        tcode = item.get("template_code", "")
        tmpl_obj = templates_by_code.get(tcode)
        if tmpl_obj:
            featured_showcase.append(
                {
                    "template": tmpl_obj,
                    "template_code": tcode,
                    "groom_en": item.get("groom_en") or "Ismail",
                    "bride_en": item.get("bride_en") or "Shrin",
                    "groom_ku": item.get("groom_ku") or "ئیسماعیل",
                    "bride_ku": item.get("bride_ku") or "شیرین",
                    "example_date": item.get("example_date") or "21 November 2026",
                    "example_venue": item.get("example_venue") or "Crystal Hall",
                }
            )

    demo_inv = db.fetchone(
        "SELECT slug, couple_image, bride_image, groom_image FROM invitations WHERE slug = 'ismail_shrin' AND is_published = TRUE"
    ) or db.fetchone(
        "SELECT slug, couple_image, bride_image, groom_image FROM invitations WHERE is_published = TRUE ORDER BY id ASC LIMIT 1"
    ) or {
        "slug": "ismail_shrin",
        "couple_image": "/static/img/demo/couple_ismail_shrin.webp",
        "bride_image": "/static/img/demo/bride_shrin.webp",
        "groom_image": "/static/img/demo/groom_ismail.webp",
    }

    return render_template(
        "public/home.html",
        homepage_cfg=homepage_cfg,
        featured_showcase=featured_showcase,
        total_templates=len(featured_showcase),
        demo_slug=demo_inv["slug"],
        demo_inv=demo_inv,
        lang=lang,
        lang_meta=lang_meta,
        ui=ui,
    )


@public_bp.route("/templates", methods=["GET"])
def explore_templates() -> Any:
    """
    Public visitors only see the templates selected by the Admin on the homepage (`/#signature-editions`).
    If an Admin is logged in, allow viewing the full gallery; otherwise redirect visitors to `/#signature-editions`.
    """
    if not get_current_admin():
        return redirect("/#signature-editions")

    db = get_db()
    all_templates = db.fetchall("SELECT * FROM templates WHERE is_active = TRUE ORDER BY sort_order ASC")
    minimal_templates = [t for t in all_templates if t["category"] == "minimal"]
    luxury_templates = [t for t in all_templates if t["category"] == "luxury"]
    invitations = db.fetchall(
        "SELECT id, slug, groom_name_en, bride_name_en, groom_name_ku, bride_name_ku FROM invitations WHERE is_published = TRUE ORDER BY id DESC LIMIT 100"
    )
    demo_slug = invitations[0]["slug"] if invitations else "ismail_shrin"
    return render_template(
        "admin/templates.html",
        minimal_templates=minimal_templates,
        luxury_templates=luxury_templates,
        invitations=invitations,
        demo_slug=demo_slug,
        is_public_explore=True,
    )


@public_bp.route("/<string:slug>/calendar.ics", methods=["GET"])
def download_ics(slug: str) -> Any:
    """Serve downloadable .ics calendar file for Apple Calendar / Outlook / mobile calendars (with CRLF injection sanitization)."""
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

    couple = clean_ics_text(
        f"{inv.get('groom_name_en') or inv.get('groom_name_ku')} & {inv.get('bride_name_en') or inv.get('bride_name_ku')}",
        max_len=140,
    )
    venue = clean_ics_text(inv.get("venue_name_en") or inv.get("venue_name_ku") or "Crystal Hall", max_len=160)
    map_url = clean_ics_text(inv.get("map_url") or "", max_len=240)

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
    preview_token = request.args.get("preview_token", "") or request.args.get("preview", "")
    stored_token = str(invitation.get("preview_token") or "")
    valid_token = bool(
        preview_token
        and stored_token
        and len(preview_token) >= 8
        and hmac.compare_digest(preview_token, stored_token)
    )
    is_preview_mode = bool((request.args.get("preview") == "1" and admin_user) or valid_token)

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

    # Allow live template preview override via `?template=...` on demo invitation or for admin/preview_token
    override_template_code = clean_text(request.args.get("template", ""), max_len=64, strip_html=True).lower()
    can_override_template = bool(admin_user or valid_token or clean_slug == "ismail_shrin")
    raw_template_code = (
        override_template_code if (override_template_code and can_override_template) else (invitation.get("template_code") or "magical_butterfly")
    )
    template_aliases = {
        "purple_soft_lavender": "minimalism_purple_soft_lavender",
        "minimalism_purple_lavender": "minimalism_purple_soft_lavender",
        "sara_ahmed_kurdish_badini_interactive_wedding_invitation": "sara_ahmed_wax_seal_veo",
        "kurdish_badini_wax_seal_veo": "sara_ahmed_wax_seal_veo",
        "wax_seal_veo_cinema": "sara_ahmed_wax_seal_veo",
    }
    active_template_code = template_aliases.get(raw_template_code, raw_template_code)

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
        WHERE invitation_id = ? AND is_enabled = TRUE
        ORDER BY sort_order ASC, id ASC
        """,
        (invitation["id"],),
    )

    gallery_uploads = db.fetchall(
        """
        SELECT id, invitation_id, media_role, file_path, thumb_path, mime_type,
               caption_ku, caption_ar, caption_en, sort_order
        FROM media_uploads
        WHERE invitation_id = ? AND media_role = 'gallery'
        ORDER BY sort_order ASC, id ASC
        LIMIT 100
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

    invitation = dict(invitation)
    # Strip private/internal columns so they are never exposed in public template contexts
    invitation.pop("preview_token", None)
    invitation.pop("created_by", None)

    # Prevent URL Parameter Tampering on Couple Names:
    # Public visitors CANNOT spoof arbitrary `?groom_en=...&bride_en=...` on a couple's invitation!
    # Showcase example names are only applied from Admin's saved `homepage_config` when `showcase` is set
    # on `ismail_shrin`, OR when an authenticated Admin previews from Admin Studio.
    ex_date = ""
    showcase_mode = clean_text(request.args.get("showcase", ""), max_len=24, strip_html=True)
    if clean_slug == "ismail_shrin" and showcase_mode:
        hp_cfg = get_homepage_config(db)
        if showcase_mode == "hero":
            invitation["groom_name_en"] = hp_cfg.get("hero_groom_en") or invitation["groom_name_en"]
            invitation["bride_name_en"] = hp_cfg.get("hero_bride_en") or invitation["bride_name_en"]
            invitation["groom_name_ku"] = hp_cfg.get("hero_groom_ku") or invitation["groom_name_ku"]
            invitation["bride_name_ku"] = hp_cfg.get("hero_bride_ku") or invitation["bride_name_ku"]
            invitation["groom_name_ar"] = hp_cfg.get("hero_groom_ku") or invitation["groom_name_ar"]
            invitation["bride_name_ar"] = hp_cfg.get("hero_bride_ku") or invitation["bride_name_ar"]
            ex_date = hp_cfg.get("hero_date") or ""
            if hp_cfg.get("hero_venue"):
                invitation["venue_name_en"] = hp_cfg["hero_venue"]
                invitation["venue_name_ku"] = hp_cfg["hero_venue"]
        else:
            for item in hp_cfg.get("featured_items", []):
                if item.get("template_code") == active_template_code:
                    invitation["groom_name_en"] = item.get("groom_en") or invitation["groom_name_en"]
                    invitation["bride_name_en"] = item.get("bride_en") or invitation["bride_name_en"]
                    invitation["groom_name_ku"] = item.get("groom_ku") or invitation["groom_name_ku"]
                    invitation["bride_name_ku"] = item.get("bride_ku") or invitation["bride_name_ku"]
                    invitation["groom_name_ar"] = item.get("groom_ku") or invitation["groom_name_ar"]
                    invitation["bride_name_ar"] = item.get("bride_ku") or invitation["bride_name_ar"]
                    ex_date = item.get("example_date") or ""
                    if item.get("example_venue"):
                        invitation["venue_name_en"] = item["example_venue"]
                        invitation["venue_name_ku"] = item["example_venue"]
                    break
    elif admin_user:
        ex_groom_en = clean_text(request.args.get("groom_en"), max_len=80, strip_html=True)
        ex_bride_en = clean_text(request.args.get("bride_en"), max_len=80, strip_html=True)
        ex_groom_ku = clean_text(request.args.get("groom_ku"), max_len=80, strip_html=True)
        ex_bride_ku = clean_text(request.args.get("bride_ku"), max_len=80, strip_html=True)
        ex_date = clean_text(request.args.get("example_date"), max_len=64, strip_html=True)
        ex_venue = clean_text(request.args.get("example_venue"), max_len=120, strip_html=True)

        if ex_groom_en:
            invitation["groom_name_en"] = ex_groom_en
            if not ex_groom_ku:
                invitation["groom_name_ku"] = ex_groom_en
        if ex_bride_en:
            invitation["bride_name_en"] = ex_bride_en
            if not ex_bride_ku:
                invitation["bride_name_ku"] = ex_bride_en
        if ex_groom_ku:
            invitation["groom_name_ku"] = ex_groom_ku
            invitation["groom_name_ar"] = ex_groom_ku
        if ex_bride_ku:
            invitation["bride_name_ku"] = ex_bride_ku
            invitation["bride_name_ar"] = ex_bride_ku
        if ex_venue:
            invitation["venue_name_en"] = ex_venue
            invitation["venue_name_ku"] = ex_venue

    groom_display = localize_field(invitation, "groom_name", lang) or invitation["groom_name_ku"]
    bride_display = localize_field(invitation, "bride_name", lang) or invitation["bride_name_ku"]
    venue_display = localize_field(invitation, "venue_name", lang) or invitation["venue_name_ku"]
    venue_address = localize_field(invitation, "venue_address", lang) or invitation["venue_address_ku"]
    human_date = ex_date if ex_date else _format_human_date(invitation["wedding_date"])
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

    effective_gallery = list(gallery_items)
    if not effective_gallery:
        for fallback_url, fallback_cap in [
            (invitation.get("couple_image") or "/static/img/demo/couple_ismail_shrin.webp", f"{groom_display} & {bride_display}"),
            (invitation.get("bride_image") or "/static/img/demo/bride_shrin.webp", bride_display),
            (invitation.get("groom_image") or "/static/img/demo/groom_ismail.webp", groom_display),
            ("/static/img/demo/gallery_crystal_hall.webp", venue_display or "Crystal Hall"),
            ("/static/img/demo/gallery_rings.webp", human_date),
        ]:
            if fallback_url:
                effective_gallery.append({"url": fallback_url, "thumb": fallback_url, "caption": fallback_cap})

    primary_schedule_items: List[Dict[str, str]] = []
    invitation_message_text = ""
    closing_section_text = ""
    enabled_section_types = [s["type"] for s in sections]

    for s in sections:
        if s["type"] == "schedule" and s.get("schedule_items") and not primary_schedule_items:
            primary_schedule_items = s["schedule_items"]
        elif s["type"] in ("wedding_details", "invitation_message") and s.get("content") and not invitation_message_text:
            invitation_message_text = s["content"]
        elif s["type"] == "couple" and s.get("content") and not invitation_message_text:
            invitation_message_text = s["content"]
        elif s["type"] == "closing" and s.get("content") and not closing_section_text:
            closing_section_text = s["content"]

    if not primary_schedule_items:
        primary_schedule_items = [
            {"time": "7:00", "label": "بخێرهاتن"},
            {"time": "7:30", "label": "هاتنا بیکو زاڤا"},
            {"time": "8:00", "label": "شیڤ خارن"},
            {"time": "9:00", "label": "دیلان"},
        ]

    rsvp_row = db.fetchone(
        "SELECT COALESCE(SUM(guests_count), 0) AS total_guests FROM rsvp_responses WHERE invitation_id = ? AND attending = 'yes'",
        (invitation["id"],),
    )
    rsvp_confirmed_count = int((rsvp_row or {}).get("total_guests") or 0)

    template_file = "public/invitation.html"
    if template.get("code") == "minimalism_purple_soft_lavender":
        candidate_path = Path(__file__).resolve().parent.parent / "templates" / "public" / "purple_soft_lavender.html"
        if candidate_path.exists():
            template_file = "public/purple_soft_lavender.html"
    elif template.get("code") == "sara_ahmed_wax_seal_veo":
        candidate_path = Path(__file__).resolve().parent.parent / "templates" / "public" / "wax_seal_veo_cinema.html"
        if candidate_path.exists():
            template_file = "public/wax_seal_veo_cinema.html"

    return render_template(
        template_file,
        invitation=invitation,
        template=template,
        sections=sections,
        enabled_section_types=enabled_section_types,
        has_opening_section=has_opening_section,
        gallery_items=gallery_items,
        effective_gallery=effective_gallery,
        primary_schedule_items=primary_schedule_items,
        invitation_message_text=invitation_message_text,
        closing_section_text=closing_section_text,
        rsvp_confirmed_count=rsvp_confirmed_count,
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
    """Record a guest's RSVP for a published invitation with CSRF, honeypot, HTML stripping, deduplication, and rate-limit protection."""
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

    payload = request.get_json(silent=True) if request.is_json else request.form

    # Honeypot anti-bot field check
    honeypot = clean_text((payload or {}).get("website_url") or (payload or {}).get("company") or "", max_len=120, strip_html=True)
    if honeypot:
        if request.is_json:
            return jsonify({"ok": False, "error": "Automated spam detected."}), 400
        abort(400, "Automated spam detected.")

    secret = current_app.config.get("SECRET_KEY", "bikozava")
    ip_hash = hashlib.sha256(f"{secret}:{get_client_ip()}".encode("utf-8")).hexdigest()[:32]
    if is_rsvp_rate_limited(int(invitation["id"]), ip_hash):
        if request.is_json:
            return jsonify({"ok": False, "error": "Too many RSVP submissions. Please try again later."}), 429
        abort(429, "Too many RSVP submissions.")

    guest_name = clean_text((payload or {}).get("guest_name"), max_len=150, strip_html=True)
    guest_phone = clean_phone((payload or {}).get("guest_phone") or (payload or {}).get("phone"), max_len=50)
    attending = clean_text((payload or {}).get("attending") or "yes", max_len=16, strip_html=True).lower()
    if attending not in ("yes", "no", "maybe"):
        attending = "yes"

    try:
        guests_count = int((payload or {}).get("guests_count") or 1)
    except (ValueError, TypeError):
        guests_count = 1
    guests_count = max(1, min(20, guests_count))

    message = clean_text((payload or {}).get("message"), max_len=1000, strip_html=True)
    lang = normalize_lang((payload or {}).get("language", invitation.get("default_language", "ku")))

    if not guest_name or len(guest_name) < 2:
        if request.is_json:
            return jsonify({"ok": False, "error": "Please enter your name."}), 400
        return redirect(url_for("public.view_invitation", slug=clean_slug, lang=lang))

    # Duplicate submission protection: if the same guest from the same IP already submitted for this invitation,
    # update their existing RSVP record rather than inserting duplicate spam rows.
    existing_rsvp = db.fetchone(
        """
        SELECT id FROM rsvp_responses
        WHERE invitation_id = ? AND ip_hash = ? AND LOWER(guest_name) = LOWER(?)
        ORDER BY id DESC LIMIT 1
        """,
        (invitation["id"], ip_hash, guest_name),
    )
    if existing_rsvp:
        db.execute(
            """
            UPDATE rsvp_responses
            SET guest_phone = ?, attending = ?, guests_count = ?, message = ?, language = ?
            WHERE id = ?
            """,
            (guest_phone, attending, guests_count, message, lang, existing_rsvp["id"]),
        )
        db.commit()
    else:
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
