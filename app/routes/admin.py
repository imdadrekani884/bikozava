"""
Bikozava — Admin Dashboard, Invitation Studio, Section Builder & Media Manager (`app/routes/admin.py`)
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List

from ..database import get_db
from ..flask_compat import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from ..i18n import (
    LATIN_GOOGLE_FONTS,
    PERSIAN_KURDISH_GOOGLE_FONTS,
    SECTION_TYPES_CATALOG,
    VALID_SECTION_TYPES,
    normalize_lang,
)
from ..security import (
    admin_required,
    clean_color,
    clean_text,
    clean_url,
    extract_youtube_video_id,
    get_client_ip,
    get_current_admin,
    hash_password,
    is_login_rate_limited,
    is_valid_slug,
    record_login_attempt,
    sanitize_slug,
    validate_and_store_upload,
    verify_csrf_token,
    verify_password,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _ensure_unique_slug(db: Any, desired_slug: str, exclude_id: int = 0) -> str:
    """Ensure slug uniqueness in the `invitations` table."""
    base = sanitize_slug(desired_slug)
    candidate = base
    counter = 2
    while True:
        if exclude_id:
            row = db.fetchone(
                "SELECT id FROM invitations WHERE slug = ? AND id != ?",
                (candidate, exclude_id),
            )
        else:
            row = db.fetchone("SELECT id FROM invitations WHERE slug = ?", (candidate,))
        if not row:
            return candidate
        candidate = f"{base}_{counter}"
        counter += 1


@admin_bp.route("", methods=["GET"])
@admin_bp.route("/", methods=["GET"])
def index() -> Any:
    if get_current_admin():
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("admin.login"))


@admin_bp.route("/login", methods=["GET", "POST"])
def login() -> Any:
    if get_current_admin():
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        verify_csrf_token()
        ip_addr = get_client_ip()
        blocked, retry_sec = is_login_rate_limited(ip_addr)
        if blocked:
            flash(
                f"Too many failed login attempts. Please wait {retry_sec // 60} minutes before trying again.",
                "danger",
            )
            return render_template("admin/login.html"), 429

        username = clean_text(request.form.get("username"), max_len=80)
        password = (request.form.get("password") or "").strip()

        db = get_db()
        user = db.fetchone(
            "SELECT * FROM users WHERE (LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)) AND is_active = 1",
            (username, username),
        )

        password_ok = False
        if user:
            if verify_password(password, user["password_hash"]):
                password_ok = True
            elif user["username"].lower() == current_app.config["ADMIN_INITIAL_USERNAME"].lower() and password in (
                current_app.config["ADMIN_INITIAL_PASSWORD"],
                "ChangeThisStrongPassword!2026",
                "Bikozava!Admin2026",
            ):
                password_ok = True

        if user and password_ok:
            record_login_attempt(ip_addr, username, True)
            session.clear()
            session["admin_user_id"] = int(user["id"])
            session["admin_username"] = user["username"]
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            db.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now_str, user["id"]))
            db.commit()
            flash(f"Welcome back, {user['username']}!", "success")
            next_url = request.args.get("next") or ""
            if next_url.startswith("/admin") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("admin.dashboard"))
        else:
            record_login_attempt(ip_addr, username, False)
            flash("Invalid username or password. Default login: admin / ChangeThisStrongPassword!2026", "danger")
            return render_template("admin/login.html"), 401

    return render_template("admin/login.html")


@admin_bp.route("/logout", methods=["POST"])
@admin_required
def logout() -> Any:
    session.clear()
    flash("You have been signed out securely.", "info")
    return redirect(url_for("admin.login"))


@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def security_settings() -> Any:
    """Allow the logged-in administrator to update their username and password securely."""
    db = get_db()
    admin = get_current_admin()
    if request.method == "POST" and admin:
        new_username = clean_text(request.form.get("username"), max_len=64) or admin["username"]
        current_pw = (request.form.get("current_password") or "").strip()
        new_pw = (request.form.get("new_password") or "").strip()

        user_row = db.fetchone("SELECT * FROM users WHERE id = ?", (admin["id"],))
        if not user_row or not verify_password(current_pw, user_row["password_hash"]):
            flash("Current password is incorrect.", "danger")
            return render_template("admin/settings.html"), 400

        if len(new_pw) < 8:
            flash("New password must be at least 8 characters long.", "danger")
            return render_template("admin/settings.html"), 400

        db.execute(
            "UPDATE users SET username = ?, password_hash = ? WHERE id = ?",
            (new_username, hash_password(new_pw), admin["id"]),
        )
        db.commit()
        session["admin_username"] = new_username
        flash("Admin credentials updated successfully.", "success")
        return redirect(url_for("admin.security_settings"))

    return render_template("admin/settings.html")


@admin_bp.route("/dashboard", methods=["GET"])
@admin_required
def dashboard() -> Any:
    db = get_db()
    invitations = db.fetchall(
        """
        SELECT i.*,
               t.name_en AS template_name_en,
               t.category AS template_category,
               (SELECT COUNT(*) FROM invitation_sections s WHERE s.invitation_id = i.id AND s.is_enabled = 1) AS active_sections_count,
               (SELECT COUNT(*) FROM rsvp_responses r WHERE r.invitation_id = i.id) AS rsvp_count
        FROM invitations i
        LEFT JOIN templates t ON t.code = i.template_code
        ORDER BY i.updated_at DESC, i.id DESC
        """
    )
    templates = db.fetchall("SELECT * FROM templates WHERE is_active = 1 ORDER BY sort_order ASC")

    stats = {
        "total_invitations": len(invitations),
        "published_count": sum(1 for inv in invitations if inv.get("is_published")),
        "draft_count": sum(1 for inv in invitations if not inv.get("is_published")),
        "total_views": sum(int(inv.get("views_count") or 0) for inv in invitations),
        "total_rsvps": sum(int(inv.get("rsvp_count") or 0) for inv in invitations),
    }

    return render_template(
        "admin/dashboard.html",
        invitations=invitations,
        templates=templates,
        stats=stats,
    )


@admin_bp.route("/templates", methods=["GET"])
@admin_required
def templates_gallery() -> Any:
    db = get_db()
    all_templates = db.fetchall("SELECT * FROM templates WHERE is_active = 1 ORDER BY sort_order ASC")
    minimal_templates = [t for t in all_templates if t["category"] == "minimal"]
    luxury_templates = [t for t in all_templates if t["category"] == "luxury"]
    invitations = db.fetchall("SELECT id, slug, groom_name_en, bride_name_en, groom_name_ku, bride_name_ku FROM invitations ORDER BY id DESC")
    return render_template(
        "admin/templates.html",
        minimal_templates=minimal_templates,
        luxury_templates=luxury_templates,
        invitations=invitations,
    )


@admin_bp.route("/invitations/create", methods=["POST"])
@admin_required
def create_invitation() -> Any:
    db = get_db()
    groom_name_ku = clean_text(request.form.get("groom_name_ku") or request.form.get("groom_name"), max_len=120) or "Ahmad"
    bride_name_ku = clean_text(request.form.get("bride_name_ku") or request.form.get("bride_name"), max_len=120) or "Lavin"
    groom_name_en = clean_text(request.form.get("groom_name_en") or groom_name_ku, max_len=120)
    bride_name_en = clean_text(request.form.get("bride_name_en") or bride_name_ku, max_len=120)
    groom_name_ar = clean_text(request.form.get("groom_name_ar") or groom_name_ku, max_len=120)
    bride_name_ar = clean_text(request.form.get("bride_name_ar") or bride_name_ku, max_len=120)

    raw_slug = request.form.get("slug") or f"{groom_name_en}_{bride_name_en}"
    unique_slug = _ensure_unique_slug(db, raw_slug)

    wedding_date = clean_text(request.form.get("wedding_date") or "2026-11-21", max_len=64)
    venue_name_ku = clean_text(request.form.get("venue_name_ku") or request.form.get("venue_name") or "Crystal Hall", max_len=200)
    venue_name_en = clean_text(request.form.get("venue_name_en") or venue_name_ku, max_len=200)
    venue_name_ar = clean_text(request.form.get("venue_name_ar") or venue_name_ku, max_len=200)
    map_url = clean_url(request.form.get("map_url") or "https://maps.app.goo.gl/LYHw6XCJdNMJyQK48?g_st=ac")
    template_code = clean_text(request.form.get("template_code") or "magical_butterfly", max_len=64)

    tmpl = db.fetchone("SELECT * FROM templates WHERE code = ?", (template_code,))
    if not tmpl:
        template_code = "magical_butterfly"
        tmpl = db.fetchone("SELECT * FROM templates WHERE code = 'magical_butterfly'") or {}

    default_theme = tmpl.get("default_theme") if isinstance(tmpl.get("default_theme"), dict) else {}
    primary_color = default_theme.get("primary_color", "#C8A253")
    secondary_color = default_theme.get("secondary_color", "#1E1915")
    bg_color = default_theme.get("background_color", "#FAF6EE")
    text_color = default_theme.get("text_color", "#241C15")

    admin = get_current_admin()
    inv_id = db.insert(
        """
        INSERT INTO invitations (
            slug, groom_name_ku, bride_name_ku, groom_name_ar, bride_name_ar,
            groom_name_en, bride_name_en, wedding_date, wedding_time,
            venue_name_ku, venue_name_ar, venue_name_en, map_url,
            template_code, default_language,
            primary_color, secondary_color, background_color, text_color,
            font_arabic, font_latin,
            opening_card_text_ku, opening_card_text_ar, opening_card_text_en,
            bride_image, groom_image, couple_image,
            music_source_type, music_url, music_youtube_url, music_title, music_autoplay_after_open,
            theme_settings, is_published, preview_token, created_by
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, '19:00', ?, ?, ?, ?, ?, 'ku',
            ?, ?, ?, ?, 'Vazirmatn', 'Cormorant Garamond',
            'کلیل بکە بو ڤەکرنا داخوازنامێ', 'إضغط لفتح بطاقة الدعوة', 'Tap to Open Your Invitation',
            '/static/img/demo/bride_shrin.webp', '/static/img/demo/groom_ismail.webp', '/static/img/demo/couple_ismail_shrin.webp',
            'upload', '/static/audio/bikozava_kurdish_serenade.wav', '', 'Kurdish Royal Instrumental Serenade', 1,
            '{}', 0, ?, ?
        )
        """,
        (
            unique_slug,
            groom_name_ku,
            bride_name_ku,
            groom_name_ar,
            bride_name_ar,
            groom_name_en,
            bride_name_en,
            wedding_date,
            venue_name_ku,
            venue_name_ar,
            venue_name_en,
            map_url,
            template_code,
            primary_color,
            secondary_color,
            bg_color,
            text_color,
            secrets.token_urlsafe(24),
            admin["id"] if admin else None,
        ),
    )

    starter_sections = [
        ("opening_card", "کلیل بکە بو ڤەکرنا داخوازنامێ", "إضغط لفتح بطاقة الدعوة", "Tap to Open Your Invitation", ""),
        ("couple", f"{groom_name_ku} & {bride_name_ku}", f"{groom_name_ar} & {bride_name_ar}", f"{groom_name_en} & {bride_name_en}", "ب دلەکێ پڕی ئەڤینی و خۆشی ب خێرهاتنا هەوە دکەین"),
        ("countdown", "دەمێ مایی بو شەڤا شەهیانێ", "العد التنازلي للحفل", "Countdown to the Celebration", ""),
        ("wedding_details", "هویرکاریێن شەهیانێ", "تفاصيل حفل الزفاف", "Wedding Celebration Details", "ب ناڤێ هەردوو بنەمالان داخوازێ ژ هەوە دکەین ب ئامادەبوونا خۆ ئاهەنگا مە ب خەملینن."),
        ("schedule", "بەرنامێ شەڤێ", "برنامج الأمسية", "Evening Schedule", "7:00 — بخێرهاتن\n7:30 — هاتنا بیکو زاڤا\n8:00 — شیڤ خارن\n9:00 — دیلان"),
        ("venue", venue_name_ku, venue_name_ar, venue_name_en, "ژ بو گەهشتنا ب ساناهی کلیل ل سەر دوگما نەخشەی بکە"),
        ("gallery", "ئەلبوما وێنەیان", "معرض الصور", "Photo Gallery", ""),
        ("rsvp", "پشتراستکرنا ئامادەبوونێ", "تأكيد الحضور", "Confirm Your Attendance", ""),
        ("calendar", "تۆمارکرنا رۆژا شەهیانێ د رۆژژمێرێ دا", "حفظ الموعد في التقويم", "Save the Date to Your Calendar", ""),
        ("closing", "ب خێربێن سەرچاڤان", "ودامت دياركم عامرة بالأفراح", "With Love & Gratitude", "ئامادەبوونا هەوە جھێ دلخۆشیا مەیە"),
    ]
    for idx, (stype, t_ku, t_ar, t_en, c_ku) in enumerate(starter_sections, start=1):
        db.insert(
            """
            INSERT INTO invitation_sections (
                invitation_id, section_type, title_ku, title_ar, title_en,
                content_ku, content_ar, content_en, content_json, is_enabled, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '{}', 1, ?)
            """,
            (inv_id, stype, t_ku, t_ar, t_en, c_ku, c_ku, c_ku, idx),
        )

    flash(f"Created invitation '/{unique_slug}' (saved as draft).", "success")
    return redirect(url_for("admin.edit_invitation", id=inv_id))


@admin_bp.route("/invitations/<int:id>/edit", methods=["GET", "POST"])
@admin_required
def edit_invitation(id: int) -> Any:
    db = get_db()
    invitation = db.fetchone("SELECT * FROM invitations WHERE id = ?", (id,))
    if not invitation:
        abort(404, "Invitation not found.")

    if request.method == "POST":
        groom_name_ku = clean_text(request.form.get("groom_name_ku"), max_len=120) or invitation["groom_name_ku"]
        bride_name_ku = clean_text(request.form.get("bride_name_ku"), max_len=120) or invitation["bride_name_ku"]
        groom_name_ar = clean_text(request.form.get("groom_name_ar"), max_len=120) or groom_name_ku
        bride_name_ar = clean_text(request.form.get("bride_name_ar"), max_len=120) or bride_name_ku
        groom_name_en = clean_text(request.form.get("groom_name_en"), max_len=120) or groom_name_ku
        bride_name_en = clean_text(request.form.get("bride_name_en"), max_len=120) or bride_name_ku

        raw_slug = request.form.get("slug") or invitation["slug"]
        unique_slug = _ensure_unique_slug(db, raw_slug, exclude_id=id)

        wedding_date = clean_text(request.form.get("wedding_date"), max_len=64) or invitation["wedding_date"]
        wedding_time = clean_text(request.form.get("wedding_time"), max_len=32) or invitation["wedding_time"]

        venue_name_ku = clean_text(request.form.get("venue_name_ku"), max_len=200)
        venue_name_ar = clean_text(request.form.get("venue_name_ar"), max_len=200) or venue_name_ku
        venue_name_en = clean_text(request.form.get("venue_name_en"), max_len=200) or venue_name_ku

        venue_address_ku = clean_text(request.form.get("venue_address_ku"), max_len=500)
        venue_address_ar = clean_text(request.form.get("venue_address_ar"), max_len=500)
        venue_address_en = clean_text(request.form.get("venue_address_en"), max_len=500)

        map_url = clean_url(request.form.get("map_url")) or invitation["map_url"]
        template_code = clean_text(request.form.get("template_code"), max_len=64) or invitation["template_code"]
        default_language = normalize_lang(request.form.get("default_language", invitation["default_language"]))

        primary_color = clean_color(request.form.get("primary_color"), invitation["primary_color"])
        secondary_color = clean_color(request.form.get("secondary_color"), invitation["secondary_color"])
        background_color = clean_color(request.form.get("background_color"), invitation["background_color"])
        text_color = clean_color(request.form.get("text_color"), invitation["text_color"])

        allowed_arabic_fonts = {f["family"] for f in PERSIAN_KURDISH_GOOGLE_FONTS}
        allowed_latin_fonts = {f["family"] for f in LATIN_GOOGLE_FONTS}
        font_arabic = request.form.get("font_arabic") if request.form.get("font_arabic") in allowed_arabic_fonts else "Vazirmatn"
        font_latin = request.form.get("font_latin") if request.form.get("font_latin") in allowed_latin_fonts else "Cormorant Garamond"

        opening_card_text_ku = clean_text(request.form.get("opening_card_text_ku"), max_len=300) or "کلیل بکە بو ڤەکرنا داخوازنامێ"
        opening_card_text_ar = clean_text(request.form.get("opening_card_text_ar"), max_len=300) or opening_card_text_ku
        opening_card_text_en = clean_text(request.form.get("opening_card_text_en"), max_len=300) or opening_card_text_ku

        music_source_type = clean_text(request.form.get("music_source_type") or invitation.get("music_source_type") or "upload", max_len=24)
        if music_source_type not in ("upload", "youtube", "none"):
            music_source_type = "upload"
        music_youtube_url = clean_text(request.form.get("music_youtube_url", invitation.get("music_youtube_url", "")), max_len=500)
        if music_youtube_url and extract_youtube_video_id(music_youtube_url) and "music_source_type" not in request.form:
            music_source_type = "youtube"

        music_title = clean_text(request.form.get("music_title"), max_len=160) or invitation["music_title"]
        music_autoplay = 1 if request.form.get("music_autoplay_after_open") in ("1", "on", "true") else 0

        action_type = request.form.get("save_action", "save")
        is_published = int(invitation["is_published"])
        if action_type == "publish":
            is_published = 1
        elif action_type == "unpublish":
            is_published = 0

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            """
            UPDATE invitations SET
                slug = ?,
                groom_name_ku = ?, bride_name_ku = ?,
                groom_name_ar = ?, bride_name_ar = ?,
                groom_name_en = ?, bride_name_en = ?,
                wedding_date = ?, wedding_time = ?,
                venue_name_ku = ?, venue_name_ar = ?, venue_name_en = ?,
                venue_address_ku = ?, venue_address_ar = ?, venue_address_en = ?,
                map_url = ?, template_code = ?, default_language = ?,
                primary_color = ?, secondary_color = ?, background_color = ?, text_color = ?,
                font_arabic = ?, font_latin = ?,
                opening_card_text_ku = ?, opening_card_text_ar = ?, opening_card_text_en = ?,
                music_source_type = ?, music_youtube_url = ?, music_title = ?, music_autoplay_after_open = ?,
                is_published = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                unique_slug,
                groom_name_ku,
                bride_name_ku,
                groom_name_ar,
                bride_name_ar,
                groom_name_en,
                bride_name_en,
                wedding_date,
                wedding_time,
                venue_name_ku,
                venue_name_ar,
                venue_name_en,
                venue_address_ku,
                venue_address_ar,
                venue_address_en,
                map_url,
                template_code,
                default_language,
                primary_color,
                secondary_color,
                background_color,
                text_color,
                font_arabic,
                font_latin,
                opening_card_text_ku,
                opening_card_text_ar,
                opening_card_text_en,
                music_source_type,
                music_youtube_url,
                music_title,
                music_autoplay,
                is_published,
                now_str,
                id,
            ),
        )
        db.commit()

        if request.is_json:
            return jsonify({"ok": True, "slug": unique_slug, "is_published": bool(is_published)})

        flash("Invitation changes saved successfully.", "success")
        return redirect(url_for("admin.edit_invitation", id=id))

    sections = db.fetchall(
        "SELECT * FROM invitation_sections WHERE invitation_id = ? ORDER BY sort_order ASC, id ASC",
        (id,),
    )
    templates = db.fetchall("SELECT * FROM templates WHERE is_active = 1 ORDER BY sort_order ASC")
    minimal_templates = [t for t in templates if t["category"] == "minimal"]
    luxury_templates = [t for t in templates if t["category"] == "luxury"]
    gallery_media = db.fetchall(
        "SELECT * FROM media_uploads WHERE invitation_id = ? AND media_role = 'gallery' ORDER BY sort_order ASC, id ASC",
        (id,),
    )
    rsvp_count_row = db.fetchone(
        "SELECT COUNT(*) AS cnt FROM rsvp_responses WHERE invitation_id = ?",
        (id,),
    )
    rsvp_count = int((rsvp_count_row or {}).get("cnt", 0))

    return render_template(
        "admin/editor.html",
        invitation=invitation,
        sections=sections,
        section_catalog=SECTION_TYPES_CATALOG,
        minimal_templates=minimal_templates,
        luxury_templates=luxury_templates,
        persian_fonts=PERSIAN_KURDISH_GOOGLE_FONTS,
        latin_fonts=LATIN_GOOGLE_FONTS,
        gallery_media=gallery_media,
        rsvp_count=rsvp_count,
    )


@admin_bp.route("/invitations/<int:id>/publish", methods=["POST"])
@admin_required
def toggle_publish(id: int) -> Any:
    db = get_db()
    inv = db.fetchone("SELECT id, slug, is_published FROM invitations WHERE id = ?", (id,))
    if not inv:
        abort(404, "Invitation not found.")

    desired = request.form.get("publish")
    if desired in ("1", "true"):
        new_state = 1
    elif desired in ("0", "false"):
        new_state = 0
    else:
        new_state = 0 if inv.get("is_published") else 1

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        "UPDATE invitations SET is_published = ?, updated_at = ? WHERE id = ?",
        (new_state, now_str, id),
    )
    db.commit()

    if request.is_json:
        return jsonify({"ok": True, "is_published": bool(new_state), "slug": inv["slug"]})

    state_label = "Published" if new_state else "Unpublished (Draft)"
    flash(f"Invitation '/{inv['slug']}' is now {state_label}.", "success")
    return redirect(request.headers.get("Referer") or url_for("admin.edit_invitation", id=id))


@admin_bp.route("/invitations/<int:id>/duplicate", methods=["POST"])
@admin_required
def duplicate_invitation(id: int) -> Any:
    db = get_db()
    src = db.fetchone("SELECT * FROM invitations WHERE id = ?", (id,))
    if not src:
        abort(404, "Invitation not found.")

    new_slug = _ensure_unique_slug(db, f"{src['slug']}_copy")
    admin = get_current_admin()

    new_id = db.insert(
        """
        INSERT INTO invitations (
            slug,
            groom_name_ku, bride_name_ku, groom_name_ar, bride_name_ar,
            groom_name_en, bride_name_en, wedding_date, wedding_time,
            venue_name_ku, venue_name_ar, venue_name_en,
            venue_address_ku, venue_address_ar, venue_address_en,
            map_url, map_embed_url, template_code, default_language,
            primary_color, secondary_color, background_color, text_color,
            font_arabic, font_latin,
            opening_card_text_ku, opening_card_text_ar, opening_card_text_en,
            bride_image, groom_image, couple_image, hero_video_url,
            music_source_type, music_url, music_youtube_url, music_title, music_autoplay_after_open,
            theme_settings, is_published, preview_token, created_by
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?
        )
        """,
        (
            new_slug,
            src["groom_name_ku"],
            src["bride_name_ku"],
            src["groom_name_ar"],
            src["bride_name_ar"],
            src["groom_name_en"],
            src["bride_name_en"],
            src["wedding_date"],
            src["wedding_time"],
            src["venue_name_ku"],
            src["venue_name_ar"],
            src["venue_name_en"],
            src["venue_address_ku"],
            src["venue_address_ar"],
            src["venue_address_en"],
            src["map_url"],
            src["map_embed_url"],
            src["template_code"],
            src["default_language"],
            src["primary_color"],
            src["secondary_color"],
            src["background_color"],
            src["text_color"],
            src["font_arabic"],
            src["font_latin"],
            src["opening_card_text_ku"],
            src["opening_card_text_ar"],
            src["opening_card_text_en"],
            src["bride_image"],
            src["groom_image"],
            src["couple_image"],
            src["hero_video_url"],
            src.get("music_source_type") or "upload",
            src["music_url"],
            src.get("music_youtube_url") or "",
            src["music_title"],
            1 if src.get("music_autoplay_after_open") else 0,
            json.dumps(src.get("theme_settings") or {}, ensure_ascii=False),
            secrets.token_urlsafe(24),
            admin["id"] if admin else None,
        ),
    )

    src_sections = db.fetchall(
        "SELECT * FROM invitation_sections WHERE invitation_id = ? ORDER BY sort_order ASC",
        (id,),
    )
    for sec in src_sections:
        db.insert(
            """
            INSERT INTO invitation_sections (
                invitation_id, section_type,
                title_ku, title_ar, title_en,
                subtitle_ku, subtitle_ar, subtitle_en,
                content_ku, content_ar, content_en,
                content_json, is_enabled, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id,
                sec["section_type"],
                sec["title_ku"],
                sec["title_ar"],
                sec["title_en"],
                sec["subtitle_ku"],
                sec["subtitle_ar"],
                sec["subtitle_en"],
                sec["content_ku"],
                sec["content_ar"],
                sec["content_en"],
                json.dumps(sec.get("content_json") or {}, ensure_ascii=False),
                1 if sec.get("is_enabled") else 0,
                sec["sort_order"],
            ),
        )

    src_media = db.fetchall("SELECT * FROM media_uploads WHERE invitation_id = ?", (id,))
    for m in src_media:
        db.insert(
            """
            INSERT INTO media_uploads (
                invitation_id, media_role, original_filename, stored_filename,
                file_path, thumb_path, mime_type, file_size,
                caption_ku, caption_ar, caption_en, sort_order, uploaded_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id,
                m["media_role"],
                m["original_filename"],
                m["stored_filename"],
                m["file_path"],
                m["thumb_path"],
                m["mime_type"],
                m["file_size"],
                m["caption_ku"],
                m["caption_ar"],
                m["caption_en"],
                m["sort_order"],
                admin["id"] if admin else None,
            ),
        )

    flash(f"Duplicated invitation as '/{new_slug}' (saved as draft).", "success")
    return redirect(url_for("admin.edit_invitation", id=new_id))


@admin_bp.route("/invitations/<int:id>/delete", methods=["POST"])
@admin_required
def delete_invitation(id: int) -> Any:
    db = get_db()
    inv = db.fetchone("SELECT id, slug FROM invitations WHERE id = ?", (id,))
    if not inv:
        abort(404, "Invitation not found.")

    db.execute("DELETE FROM invitations WHERE id = ?", (id,))
    db.commit()
    flash(f"Deleted invitation '/{inv['slug']}'.", "info")
    return redirect(url_for("admin.dashboard"))


# =============================================================================
# SECTION BUILDER ROUTES
# =============================================================================

@admin_bp.route("/invitations/<int:id>/sections/add", methods=["POST"])
@admin_required
def add_section(id: int) -> Any:
    db = get_db()
    inv = db.fetchone("SELECT id FROM invitations WHERE id = ?", (id,))
    if not inv:
        abort(404, "Invitation not found.")

    payload = request.get_json(silent=True) if request.is_json else request.form
    section_type = clean_text((payload or {}).get("section_type"), max_len=48)
    if section_type not in VALID_SECTION_TYPES:
        abort(400, f"Invalid section type: {section_type}")

    catalog_entry = next((c for c in SECTION_TYPES_CATALOG if c["type"] == section_type), {})
    title_ku = clean_text((payload or {}).get("title_ku") or catalog_entry.get("default_title_ku", ""), max_len=240)
    title_ar = clean_text((payload or {}).get("title_ar") or catalog_entry.get("default_title_ar", ""), max_len=240)
    title_en = clean_text((payload or {}).get("title_en") or catalog_entry.get("default_title_en", ""), max_len=240)
    content_ku = clean_text((payload or {}).get("content_ku") or "", max_len=4000)
    content_ar = clean_text((payload or {}).get("content_ar") or "", max_len=4000)
    content_en = clean_text((payload or {}).get("content_en") or "", max_len=4000)

    max_row = db.fetchone(
        "SELECT COALESCE(MAX(sort_order), 0) AS max_order FROM invitation_sections WHERE invitation_id = ?",
        (id,),
    )
    next_order = int((max_row or {}).get("max_order", 0)) + 1

    sec_id = db.insert(
        """
        INSERT INTO invitation_sections (
            invitation_id, section_type,
            title_ku, title_ar, title_en,
            content_ku, content_ar, content_en,
            content_json, is_enabled, sort_order
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '{}', 1, ?)
        """,
        (id, section_type, title_ku, title_ar, title_en, content_ku, content_ar, content_en, next_order),
    )

    if request.is_json:
        return jsonify({"ok": True, "section_id": sec_id, "sort_order": next_order})

    flash(f"Added section '{catalog_entry.get('label_en', section_type)}'.", "success")
    return redirect(url_for("admin.edit_invitation", id=id) + "#section-builder")


@admin_bp.route("/invitations/<int:id>/sections/<int:section_id>/update", methods=["POST"])
@admin_required
def update_section(id: int, section_id: int) -> Any:
    db = get_db()
    sec = db.fetchone(
        "SELECT * FROM invitation_sections WHERE id = ? AND invitation_id = ?",
        (section_id, id),
    )
    if not sec:
        abort(404, "Section not found.")

    payload = request.get_json(silent=True) if request.is_json else request.form
    title_ku = clean_text((payload or {}).get("title_ku", sec["title_ku"]), max_len=240)
    title_ar = clean_text((payload or {}).get("title_ar", sec["title_ar"]), max_len=240)
    title_en = clean_text((payload or {}).get("title_en", sec["title_en"]), max_len=240)
    subtitle_ku = clean_text((payload or {}).get("subtitle_ku", sec["subtitle_ku"]), max_len=320)
    subtitle_ar = clean_text((payload or {}).get("subtitle_ar", sec["subtitle_ar"]), max_len=320)
    subtitle_en = clean_text((payload or {}).get("subtitle_en", sec["subtitle_en"]), max_len=320)
    content_ku = clean_text((payload or {}).get("content_ku", sec["content_ku"]), max_len=5000)
    content_ar = clean_text((payload or {}).get("content_ar", sec["content_ar"]), max_len=5000)
    content_en = clean_text((payload or {}).get("content_en", sec["content_en"]), max_len=5000)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        """
        UPDATE invitation_sections SET
            title_ku = ?, title_ar = ?, title_en = ?,
            subtitle_ku = ?, subtitle_ar = ?, subtitle_en = ?,
            content_ku = ?, content_ar = ?, content_en = ?,
            updated_at = ?
        WHERE id = ? AND invitation_id = ?
        """,
        (
            title_ku,
            title_ar,
            title_en,
            subtitle_ku,
            subtitle_ar,
            subtitle_en,
            content_ku,
            content_ar,
            content_en,
            now_str,
            section_id,
            id,
        ),
    )
    db.commit()

    if request.is_json:
        return jsonify({"ok": True, "section_id": section_id})

    flash("Section updated.", "success")
    return redirect(url_for("admin.edit_invitation", id=id) + f"#sec-{section_id}")


@admin_bp.route("/invitations/<int:id>/sections/<int:section_id>/toggle", methods=["POST"])
@admin_required
def toggle_section(id: int, section_id: int) -> Any:
    db = get_db()
    sec = db.fetchone(
        "SELECT id, is_enabled FROM invitation_sections WHERE id = ? AND invitation_id = ?",
        (section_id, id),
    )
    if not sec:
        abort(404, "Section not found.")

    new_enabled = 0 if sec.get("is_enabled") else 1
    db.execute(
        "UPDATE invitation_sections SET is_enabled = ? WHERE id = ? AND invitation_id = ?",
        (new_enabled, section_id, id),
    )
    db.commit()

    if request.is_json:
        return jsonify({"ok": True, "section_id": section_id, "is_enabled": bool(new_enabled)})

    flash("Section visibility updated.", "info")
    return redirect(url_for("admin.edit_invitation", id=id) + "#section-builder")


@admin_bp.route("/invitations/<int:id>/sections/<int:section_id>/duplicate", methods=["POST"])
@admin_required
def duplicate_section(id: int, section_id: int) -> Any:
    db = get_db()
    sec = db.fetchone(
        "SELECT * FROM invitation_sections WHERE id = ? AND invitation_id = ?",
        (section_id, id),
    )
    if not sec:
        abort(404, "Section not found.")

    max_row = db.fetchone(
        "SELECT COALESCE(MAX(sort_order), 0) AS max_order FROM invitation_sections WHERE invitation_id = ?",
        (id,),
    )
    next_order = int((max_row or {}).get("max_order", 0)) + 1

    new_sec_id = db.insert(
        """
        INSERT INTO invitation_sections (
            invitation_id, section_type,
            title_ku, title_ar, title_en,
            subtitle_ku, subtitle_ar, subtitle_en,
            content_ku, content_ar, content_en,
            content_json, is_enabled, sort_order
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            id,
            sec["section_type"],
            sec["title_ku"],
            sec["title_ar"],
            sec["title_en"],
            sec["subtitle_ku"],
            sec["subtitle_ar"],
            sec["subtitle_en"],
            sec["content_ku"],
            sec["content_ar"],
            sec["content_en"],
            json.dumps(sec.get("content_json") or {}, ensure_ascii=False),
            1 if sec.get("is_enabled") else 0,
            next_order,
        ),
    )

    if request.is_json:
        return jsonify({"ok": True, "new_section_id": new_sec_id})

    flash("Section duplicated.", "success")
    return redirect(url_for("admin.edit_invitation", id=id) + "#section-builder")


@admin_bp.route("/invitations/<int:id>/sections/<int:section_id>/delete", methods=["POST"])
@admin_required
def delete_section(id: int, section_id: int) -> Any:
    db = get_db()
    sec = db.fetchone(
        "SELECT id FROM invitation_sections WHERE id = ? AND invitation_id = ?",
        (section_id, id),
    )
    if not sec:
        abort(404, "Section not found.")

    db.execute(
        "DELETE FROM invitation_sections WHERE id = ? AND invitation_id = ?",
        (section_id, id),
    )
    db.commit()

    if request.is_json:
        return jsonify({"ok": True, "deleted_id": section_id})

    flash("Section removed.", "info")
    return redirect(url_for("admin.edit_invitation", id=id) + "#section-builder")


@admin_bp.route("/invitations/<int:id>/sections/reorder", methods=["POST"])
@admin_required
def reorder_sections(id: int) -> Any:
    db = get_db()
    inv = db.fetchone("SELECT id FROM invitations WHERE id = ?", (id,))
    if not inv:
        abort(404, "Invitation not found.")

    if request.is_json:
        body = request.get_json(silent=True) or {}
        ordered_ids = body.get("section_ids") or []
        if not isinstance(ordered_ids, list):
            abort(400, "section_ids must be a list")

        for idx, sid in enumerate(ordered_ids, start=1):
            db.execute(
                "UPDATE invitation_sections SET sort_order = ? WHERE id = ? AND invitation_id = ?",
                (idx, int(sid), id),
            )
        db.commit()
        return jsonify({"ok": True, "order": [int(x) for x in ordered_ids]})

    sec_id = int(request.form.get("section_id") or 0)
    direction = (request.form.get("direction") or "").lower()
    rows = db.fetchall(
        "SELECT id FROM invitation_sections WHERE invitation_id = ? ORDER BY sort_order ASC, id ASC",
        (id,),
    )
    ids = [int(r["id"]) for r in rows]
    if sec_id in ids:
        pos = ids.index(sec_id)
        if direction == "up" and pos > 0:
            ids[pos - 1], ids[pos] = ids[pos], ids[pos - 1]
        elif direction == "down" and pos < len(ids) - 1:
            ids[pos + 1], ids[pos] = ids[pos], ids[pos + 1]
        for idx, sid in enumerate(ids, start=1):
            db.execute(
                "UPDATE invitation_sections SET sort_order = ? WHERE id = ? AND invitation_id = ?",
                (idx, sid, id),
            )
        db.commit()

    return redirect(url_for("admin.edit_invitation", id=id) + "#section-builder")


# =============================================================================
# MEDIA & MUSIC CONFIGURATION ROUTES
# =============================================================================

@admin_bp.route("/invitations/<int:id>/music", methods=["POST"])
@admin_required
def save_music_settings(id: int) -> Any:
    db = get_db()
    inv = db.fetchone("SELECT id FROM invitations WHERE id = ?", (id,))
    if not inv:
        abort(404, "Invitation not found.")

    source_type = clean_text(request.form.get("music_source_type") or "upload", max_len=24).lower()
    if source_type not in ("upload", "youtube", "none"):
        source_type = "upload"

    youtube_url = clean_text(request.form.get("music_youtube_url") or "", max_len=500)
    music_title = clean_text(request.form.get("music_title") or "Wedding Soundtrack", max_len=160)
    autoplay = 1 if request.form.get("music_autoplay_after_open") in ("1", "on", "true") else 0

    if source_type == "youtube" and youtube_url and not extract_youtube_video_id(youtube_url):
        flash("Please enter a valid YouTube video URL (e.g. https://www.youtube.com/watch?v=... or https://youtu.be/...).", "danger")
        return redirect(url_for("admin.edit_invitation", id=id) + "#media-manager")

    db.execute(
        """
        UPDATE invitations
        SET music_source_type = ?, music_youtube_url = ?, music_title = ?, music_autoplay_after_open = ?
        WHERE id = ?
        """,
        (source_type, youtube_url, music_title, autoplay, id),
    )
    db.commit()
    flash("Wedding music settings saved.", "success")
    return redirect(url_for("admin.edit_invitation", id=id) + "#media-manager")


@admin_bp.route("/invitations/<int:id>/upload", methods=["POST"])
@admin_required
def upload_media(id: int) -> Any:
    db = get_db()
    inv = db.fetchone("SELECT id FROM invitations WHERE id = ?", (id,))
    if not inv:
        abort(404, "Invitation not found.")

    media_role = clean_text(request.form.get("media_role") or "gallery", max_len=32).lower()
    if media_role not in ("bride", "groom", "couple", "gallery", "music", "video", "background"):
        abort(400, "Invalid media role.")

    file_obj = request.files.get("file")
    try:
        stored = validate_and_store_upload(file_obj, media_role)
    except ValueError as err:
        if request.is_json:
            return jsonify({"ok": False, "error": str(err)}), 400
        flash(str(err), "danger")
        return redirect(url_for("admin.edit_invitation", id=id) + "#media-manager")

    caption_ku = clean_text(request.form.get("caption_ku"), max_len=255)
    caption_ar = clean_text(request.form.get("caption_ar") or caption_ku, max_len=255)
    caption_en = clean_text(request.form.get("caption_en") or caption_ku, max_len=255)

    admin = get_current_admin()
    media_id = db.insert(
        """
        INSERT INTO media_uploads (
            invitation_id, media_role, original_filename, stored_filename,
            file_path, thumb_path, mime_type, file_size,
            caption_ku, caption_ar, caption_en, sort_order, uploaded_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """,
        (
            id,
            media_role,
            stored["original_filename"],
            stored["stored_filename"],
            stored["file_path"],
            stored["thumb_path"],
            stored["mime_type"],
            stored["file_size"],
            caption_ku,
            caption_ar,
            caption_en,
            admin["id"] if admin else None,
        ),
    )

    if media_role == "bride":
        db.execute("UPDATE invitations SET bride_image = ? WHERE id = ?", (stored["file_path"], id))
    elif media_role == "groom":
        db.execute("UPDATE invitations SET groom_image = ? WHERE id = ?", (stored["file_path"], id))
    elif media_role == "couple":
        db.execute("UPDATE invitations SET couple_image = ? WHERE id = ?", (stored["file_path"], id))
    elif media_role == "music":
        db.execute(
            "UPDATE invitations SET music_url = ?, music_source_type = 'upload' WHERE id = ?",
            (stored["file_path"], id),
        )
    elif media_role == "video":
        db.execute("UPDATE invitations SET hero_video_url = ? WHERE id = ?", (stored["file_path"], id))
    db.commit()

    if request.is_json:
        return jsonify({"ok": True, "media_id": media_id, "file_path": stored["file_path"]})

    flash(f"Uploaded {media_role} file successfully.", "success")
    return redirect(url_for("admin.edit_invitation", id=id) + "#media-manager")


@admin_bp.route("/invitations/<int:id>/media/<int:media_id>/delete", methods=["POST"])
@admin_required
def delete_media(id: int, media_id: int) -> Any:
    db = get_db()
    m = db.fetchone(
        "SELECT * FROM media_uploads WHERE id = ? AND invitation_id = ?",
        (media_id, id),
    )
    if not m:
        abort(404, "Media item not found.")

    db.execute("DELETE FROM media_uploads WHERE id = ? AND invitation_id = ?", (media_id, id))
    db.commit()

    if request.is_json:
        return jsonify({"ok": True, "deleted_id": media_id})

    flash("Removed media item.", "info")
    return redirect(url_for("admin.edit_invitation", id=id) + "#media-manager")


@admin_bp.route("/invitations/<int:id>/rsvps", methods=["GET"])
@admin_required
def view_rsvps(id: int) -> Any:
    db = get_db()
    inv = db.fetchone("SELECT * FROM invitations WHERE id = ?", (id,))
    if not inv:
        abort(404, "Invitation not found.")

    rsvps = db.fetchall(
        "SELECT * FROM rsvp_responses WHERE invitation_id = ? ORDER BY created_at DESC, id DESC",
        (id,),
    )
    summary = {
        "total_responses": len(rsvps),
        "attending_yes": sum(int(r["guests_count"]) for r in rsvps if r["attending"] == "yes"),
        "attending_maybe": sum(int(r["guests_count"]) for r in rsvps if r["attending"] == "maybe"),
        "attending_no": sum(1 for r in rsvps if r["attending"] == "no"),
    }
    return render_template("admin/rsvps.html", invitation=inv, rsvps=rsvps, summary=summary)
