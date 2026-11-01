"""
Bikozava — Database Seeding & Demo Assets Generator (`app/seed.py`)

Seeds:
1. Default Admin Account (configured via `.env`, automatically synchronizes password
   hash if `.env` was updated so login never fails due to stale hashes).
2. 24 Extensible Templates across 2 categories:
   - MINIMAL (5): Minimal Ivory, Minimal Champagne, Modern White, Editorial, Soft Floral
   - COMPLEX / LUXURY & INTERACTIVE EXPERIENCES (19):
     * ✨ Champagne Envelope & Gold Foil (`champagne_envelope_foil`) — Your uploaded luxury cream & champagne-gold envelope template with floating canvas butterflies/blossoms, interactive touch-sparkle bursts, vertical timeline, and admin-controlled MP3/YouTube music
     * 📸 Champagne Envelope & Gold Foil (With Photos) (`champagne_envelope_photos`) — Identical to `champagne_envelope_foil` plus Bride, Groom & Couple portraits and the interactive Photo Gallery
     * 🦋 Magical Butterfly (`magical_butterfly`)
     * 🎬 9:16 Vertical Cinema Reel (`vertical_cinema_reel`)
     * 🪙 Golden Scratch-Off Reveal (`golden_scratch_reveal`)
     * 🏮 Tap-to-Glow Sky Lanterns (`starlight_lantern_glow`)
     * 🌙 Moonlit Lake (`moonlit_lake`)
     * 🚂 The Wedding Train (`wedding_train`)
     * 🏰 Floating Castle (`floating_castle`)
     * 🌊 Message in a Bottle (`message_in_a_bottle`)
     * Royal Luxury (`royal_luxury`)
     * Golden Palace (`golden_palace`)
     * Cinematic Garden (`cinematic_garden`)
     * Luxury Floral (`luxury_floral`)
     * Traditional Kurdish Luxury (`traditional_kurdish_luxury`)
     * Black & Gold (`black_and_gold`)
     * Romantic Crystal (`romantic_crystal`)
"""

from __future__ import annotations

import json
import math
import secrets
import struct
import wave
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image, ImageDraw

from .database import get_db
from .flask_compat import current_app
from .security import hash_password, verify_password


TEMPLATES_SEED: List[Dict[str, Any]] = [
    # =========================================================================
    # CATEGORY 1: MINIMAL TEMPLATES (5)
    # =========================================================================
    {
        "code": "minimal_ivory",
        "name_ku": "عاجی سادە (Minimal Ivory)",
        "name_ar": "عاجي ناعم (Minimal Ivory)",
        "name_en": "Minimal Ivory",
        "category": "minimal",
        "description_ku": "دیزاینەکا سادە و نازک ب رەنگێ عاجی و فۆنتێ فارسی و کلاسیکی یێ جوان.",
        "description_ar": "تصميم عاجي هادئ وبسيط مع مساحات بيضاء مريحة وخطوط كلاسيكية.",
        "description_en": "Warm ivory paper aesthetics, generous whitespace, fine hairline dividers, and timeless serif typography.",
        "preview_style": {
            "bg": "#FAF7F2",
            "card": "#FFFFFF",
            "accent": "#B89758",
            "text": "#2A2421",
            "badge": "Minimal • Warm Ivory",
        },
        "default_theme": {
            "primary_color": "#B89758",
            "secondary_color": "#2A2421",
            "background_color": "#FAF7F2",
            "text_color": "#2A2421",
            "card_style": "minimal-hairline",
            "particles": "none",
        },
        "has_butterfly_opening": 0,
        "sort_order": 1,
    },
    {
        "code": "minimal_champagne",
        "name_ku": "شامپانی سادە (Minimal Champagne)",
        "name_ar": "شامبانيا هادئ (Minimal Champagne)",
        "name_en": "Minimal Champagne",
        "category": "minimal",
        "description_ku": "رەنگێ شامپانی یێ نەرم دگەل جوولەیێن هێمن و سەرنجراکێش.",
        "description_ar": "درجات الشامبانيا الدافئة مع انتقالات انسيابية هادئة.",
        "description_en": "Soft champagne silk tones with understated metallic accents and airy mobile cards.",
        "preview_style": {
            "bg": "#F7F1E5",
            "card": "#FFFDF9",
            "accent": "#C5A059",
            "text": "#33291F",
            "badge": "Minimal • Champagne",
        },
        "default_theme": {
            "primary_color": "#C5A059",
            "secondary_color": "#33291F",
            "background_color": "#F7F1E5",
            "text_color": "#33291F",
            "card_style": "minimal-soft",
            "particles": "none",
        },
        "has_butterfly_opening": 0,
        "sort_order": 2,
    },
    {
        "code": "modern_white",
        "name_ku": "سپی مۆدێرن (Modern White)",
        "name_ar": "أبيض عصري (Modern White)",
        "name_en": "Modern White",
        "category": "minimal",
        "description_ku": "ستایلێ مۆدێرن و پاقژ بو شەهیانێن هاوچەرخ.",
        "description_ar": "تصميم عصري ناصع البياض بخطوط واضحة وتباين أنيق.",
        "description_en": "Crisp gallery-white surfaces, architectural geometry, and high-contrast monochrome & gold typography.",
        "preview_style": {
            "bg": "#FFFFFF",
            "card": "#F8F9FA",
            "accent": "#9E7B4F",
            "text": "#141414",
            "badge": "Minimal • Pure White",
        },
        "default_theme": {
            "primary_color": "#9E7B4F",
            "secondary_color": "#141414",
            "background_color": "#FFFFFF",
            "text_color": "#141414",
            "card_style": "architectural",
            "particles": "none",
        },
        "has_butterfly_opening": 0,
        "sort_order": 3,
    },
    {
        "code": "editorial",
        "name_ku": "ئێدیتۆریال (Editorial)",
        "name_ar": "إديتوريال مجلات (Editorial)",
        "name_en": "Editorial",
        "category": "minimal",
        "description_ku": "دیزاینا گۆڤارێن جیهانی ب وێنەیێن مەزن و نڤیسینێن هونەری.",
        "description_ar": "مستوحى من مجلات الموضة الفاخرة مع تركيز على الصور الفوتوغرافية.",
        "description_en": "Vogue-inspired magazine layout with dramatic serif numerals, asymmetric framing, and refined photography.",
        "preview_style": {
            "bg": "#F4F1EA",
            "card": "#FAF8F5",
            "accent": "#8C6D46",
            "text": "#191716",
            "badge": "Minimal • Magazine",
        },
        "default_theme": {
            "primary_color": "#8C6D46",
            "secondary_color": "#191716",
            "background_color": "#F4F1EA",
            "text_color": "#191716",
            "card_style": "editorial-frame",
            "particles": "none",
        },
        "has_butterfly_opening": 0,
        "sort_order": 4,
    },
    {
        "code": "soft_floral",
        "name_ku": "گوڵدارێ نەرم (Soft Floral)",
        "name_ar": "زهور ناعمة (Soft Floral)",
        "name_en": "Soft Floral",
        "category": "minimal",
        "description_ku": "نەخشێن گوڵێن ناسک ب رەنگێ پەمبە و زێڕی یێ هێمن.",
        "description_ar": "زخارف نباتية ناعمة بألوان الباستيل الوردية والذهبية.",
        "description_en": "Delicate botanical line-art watermarks paired with blush-cream surfaces and romantic typography.",
        "preview_style": {
            "bg": "#FDF8F6",
            "card": "#FFFFFF",
            "accent": "#C48B71",
            "text": "#362624",
            "badge": "Minimal • Botanical",
        },
        "default_theme": {
            "primary_color": "#C48B71",
            "secondary_color": "#362624",
            "background_color": "#FDF8F6",
            "text_color": "#362624",
            "card_style": "botanical",
            "particles": "petals-subtle",
        },
        "has_butterfly_opening": 0,
        "sort_order": 5,
    },

    # =========================================================================
    # CATEGORY 2: COMPLEX / LUXURY & INTERACTIVE STORY EXPERIENCES (19)
    # =========================================================================
    {
        "code": "champagne_envelope_foil",
        "name_ku": "✨ زەرفا شامپانی و زێڕین (Champagne Envelope Foil)",
        "name_ar": "✨ ظرف الشامبانيا المذهب (Champagne Envelope Foil)",
        "name_en": "✨ Champagne Envelope & Gold Foil",
        "category": "luxury",
        "description_ku": "دیزاینا شاهانە یا زەرفا شامپانی دگەل پەپوولە و گوڵێن فرۆک و هێلا دەمی یا ستوونی (بێ وێنە).",
        "description_ar": "تصميم ظرف الشامبانيا الملكي مع الفراشات والزهور العائمة والجدول الزمني العمودي (نسخة كلاسيكية بدون صور).",
        "description_en": "Your custom luxury cream & champagne-gold envelope design with floating blossoms, flapping golden butterflies, interactive touch-sparkle bursts, vertical timeline, and admin-controlled MP3/YouTube music (pure typography edition).",
        "preview_style": {
            "bg": "#FAF8F5",
            "card": "#FFFFFF",
            "accent": "#B38F48",
            "text": "#141414",
            "badge": "✨ Champagne Envelope",
        },
        "default_theme": {
            "primary_color": "#B38F48",
            "secondary_color": "#141414",
            "background_color": "#FAF8F5",
            "text_color": "#1E1E1E",
            "card_style": "champagne-foil",
            "particles": "flowers-butterflies",
            "opening_mode": "champagne_envelope",
        },
        "has_butterfly_opening": 1,
        "sort_order": 6,
    },
    {
        "code": "champagne_envelope_photos",
        "name_ku": "📸 زەرفا شامپانی یا وێنەدار (Champagne Envelope + Photos)",
        "name_ar": "📸 ظرف الشامبانيا المذهب مع الصور (Champagne Envelope + Photos)",
        "name_en": "📸 Champagne Envelope & Gold Foil (With Photos)",
        "category": "luxury",
        "description_ku": "هەمان دیزاینا نایاب یا زەرفا شامپانی و گوڵێن فرۆک، بەلێ دگەل وێنەیێن بیک و زاڤای و ئەلبوما وێنەیان د ناڤ چوارچێوێن زێڕین دا.",
        "description_ar": "نفس تصميم ظرف الشامبانيا الملكي والفراشات العائمة، مع إضافة صور العروسين ومعرض الصور الفوتوغرافية بإطارات مذهبة.",
        "description_en": "Exact same luxury cream & champagne-gold envelope template with floating blossoms and butterflies, enhanced with gold-framed Bride, Groom & Couple portraits and an interactive Photo Gallery.",
        "preview_style": {
            "bg": "#FAF8F5",
            "card": "#FFFFFF",
            "accent": "#B38F48",
            "text": "#141414",
            "badge": "📸 Envelope + Photos",
        },
        "default_theme": {
            "primary_color": "#B38F48",
            "secondary_color": "#141414",
            "background_color": "#FAF8F5",
            "text_color": "#1E1E1E",
            "card_style": "champagne-foil-photos",
            "particles": "flowers-butterflies",
            "opening_mode": "champagne_envelope",
        },
        "has_butterfly_opening": 1,
        "sort_order": 7,
    },
    {
        "code": "champagne_envelope_dark",
        "name_ku": "🌑 زەرفا شەڤا تاریک و زێڕین (Champagne Envelope Dark Mode)",
        "name_ar": "🌑 ظرف الليل الأسود والذهب (Champagne Envelope Dark Mode)",
        "name_en": "🌑 Midnight Obsidian & Gold Foil (Dark Mode)",
        "category": "luxury",
        "description_ku": "مۆدا تاریک (Dark Mode) یا زەرفا شامپانی ب رەنگێ رەشێ شاهانە و زێڕێ بریقەدار دگەل پەپوولە و گوڵێن فرۆک (بێ وێنە).",
        "description_ar": "الوضع الليلي الملكي لظرف الشامبانيا باللون الأسود الفاخر والذهب اللامع مع الفراشات والزهور العائمة (بدون صور).",
        "description_en": "Dark Mode edition of the Champagne Envelope & Gold Foil template — deep obsidian-charcoal surfaces, luminous 24k gold foil borders, floating blossoms & golden butterflies, touch-sparkles, and admin-controlled music (without photos).",
        "preview_style": {
            "bg": "#0D0C0B",
            "card": "#171513",
            "accent": "#DFCA97",
            "text": "#FAF8F5",
            "badge": "🌑 Dark Mode Envelope",
        },
        "default_theme": {
            "primary_color": "#C8A86B",
            "secondary_color": "#FAF8F5",
            "background_color": "#0D0C0B",
            "text_color": "#FAF8F5",
            "card_style": "champagne-foil-dark",
            "particles": "flowers-butterflies",
            "opening_mode": "champagne_envelope",
        },
        "has_butterfly_opening": 1,
        "sort_order": 8,
    },
    {
        "code": "champagne_envelope_dark_photos",
        "name_ku": "🌙 زەرفا تاریک و زێڕین یا وێنەدار (Dark Envelope + Photos)",
        "name_ar": "🌙 ظرف الليل المذهب مع الصور (Dark Envelope + Photos)",
        "name_en": "🌙 Midnight Obsidian & Gold Foil (Dark Mode + Photos)",
        "category": "luxury",
        "description_ku": "مۆدا تاریک (Dark Mode) یا زەرفا شامپانی و گوڵێن فرۆک، دگەل وێنەیێن بیک و زاڤای و ئەلبوما وێنەیان د ناڤ چوارچێوێن زێڕین دا.",
        "description_ar": "الوضع الليلي الملكي لظرف الشامبانيا المذهب مع صور العروسين ومعرض الصور الفوتوغرافية بإطارات ذهبية مضيئة.",
        "description_en": "Dark Mode edition of Champagne Envelope & Gold Foil complete with gold-framed Bride, Groom & Couple portraits and the interactive Photo Gallery.",
        "preview_style": {
            "bg": "#0D0C0B",
            "card": "#171513",
            "accent": "#C8A86B",
            "text": "#FAF8F5",
            "badge": "🌙 Dark + Photos",
        },
        "default_theme": {
            "primary_color": "#C8A86B",
            "secondary_color": "#FAF8F5",
            "background_color": "#0D0C0B",
            "text_color": "#FAF8F5",
            "card_style": "champagne-foil-dark-photos",
            "particles": "flowers-butterflies",
            "opening_mode": "champagne_envelope",
        },
        "has_butterfly_opening": 1,
        "sort_order": 9,
    },
    {
        "code": "magical_butterfly",
        "name_ku": "🦋 پەپوولەیا جادوویی (Magical Butterfly)",
        "name_ar": "🦋 الفراشة الساحرة (Magical Butterfly)",
        "name_en": "🦋 Magical Butterfly",
        "category": "luxury",
        "description_ku": "کارتا داخوازناما شاهانە ب پەپوولەیا سێ-رەهەندی (3D)، تۆزا زێڕین و ڤەبوونا سینەمایی.",
        "description_ar": "بطاقة دعوة ملكية ثلاثية الأبعاد مع فراشة ذهبية متحركة وذرات الذهب المضيئة.",
        "description_en": "Signature 3D embossed ivory & champagne-gold card with a living 3D butterfly that unfolds the card and flies toward the camera in golden light.",
        "preview_style": {
            "bg": "#FAF6EE",
            "card": "#FFFDF7",
            "accent": "#C8A253",
            "text": "#241C15",
            "badge": "3D Butterfly Card",
        },
        "default_theme": {
            "primary_color": "#C8A253",
            "secondary_color": "#1E1915",
            "background_color": "#FAF6EE",
            "text_color": "#241C15",
            "card_style": "embossed-gold",
            "particles": "gold-dust",
            "opening_mode": "butterfly",
        },
        "has_butterfly_opening": 1,
        "sort_order": 8,
    },
    {
        "code": "vertical_cinema_reel",
        "name_ku": "🎬 ڤیدیۆیا ستوونی 9:16 (Vertical Cinema Reel)",
        "name_ar": "🎬 فيديو سينمائي عمودي 9:16 (Vertical Cinema Reel)",
        "name_en": "🎬 9:16 Vertical Cinema Reel",
        "category": "luxury",
        "description_ku": "پشتی ڤەکرنا کارتا داخوازنامێ، ئێکسەر ڤیدیۆیا ستوونی (9:16) یا تایبەت دەستپێدکەت و ناڤێن بیک و زاڤای ب شێوەیەکێ ئۆتۆماتیکی ل سەری و نیڤەکا ڤیدیۆیێ دیار دبن.",
        "description_ar": "بعد فتح بطاقة الدعوة يظهر فوراً فيديو عمودي 9:16 مرفوع من الإدارة كأول شريحة مع ظهور أسماء العروسين تلقائياً في أعلى منتصف الفيديو.",
        "description_en": "Opens with the luxury 3D card and immediately reveals a full-screen 9:16 vertical video uploaded by the admin as the first slide, with Bride & Groom names automatically overlaid at the top-middle of the video.",
        "preview_style": {
            "bg": "#110E0C",
            "card": "#1C1613",
            "accent": "#E5C168",
            "text": "#FAF6EE",
            "badge": "🎬 9:16 Video Hero",
        },
        "default_theme": {
            "primary_color": "#E5C168",
            "secondary_color": "#FAF6EE",
            "background_color": "#110E0C",
            "text_color": "#FAF6EE",
            "card_style": "cinema-9-16",
            "particles": "gold-dust",
            "opening_mode": "butterfly",
        },
        "has_butterfly_opening": 1,
        "sort_order": 9,
    },
    {
        "code": "golden_scratch_reveal",
        "name_ku": "🪙 کارتێ زێڕین بڕەنە (Golden Scratch-Off)",
        "name_ar": "🪙 امسح الذهب للكشف (Golden Scratch-Off)",
        "name_en": "🪙 Golden Scratch-Off Reveal",
        "category": "luxury",
        "description_ku": "مێهڤان ب تلیا خۆ تەبەقا زێڕی ل سەر شاشێ دڕەنیت (Scratch) دا ناڤێن بیک و زاڤای و رۆژا شەهیانێ ب شێوەیەکێ سەرنجراکێش دیار ببن.",
        "description_ar": "يمسح الضيف طبقة الذهب اللامعة بإصبعه على الشاشة ليكشف عن أسماء العروسين وموعد الزفاف بطريقة تفاعلية ممتعة.",
        "description_en": "Interactive tactile metallic 24k gold foil scratch card! Guests rub the shimmering gold foil with their finger or mouse to reveal the couple's names and unlock the invitation.",
        "preview_style": {
            "bg": "#1C1610",
            "card": "#FFFDF7",
            "accent": "#D4AF37",
            "text": "#241C15",
            "badge": "🪙 Scratch to Reveal",
        },
        "default_theme": {
            "primary_color": "#D4AF37",
            "secondary_color": "#241C15",
            "background_color": "#FAF6EE",
            "text_color": "#241C15",
            "card_style": "embossed-gold",
            "particles": "gold-sparkles",
            "opening_mode": "golden_scratch_reveal",
        },
        "has_butterfly_opening": 1,
        "sort_order": 10,
    },
    {
        "code": "starlight_lantern_glow",
        "name_ku": "🏮 هەلکرنا فەنەرێن ئاسمانی (Tap-to-Glow Lanterns)",
        "name_ar": "🏮 إضاءة الفوانيس السماوية (Tap-to-Glow Lanterns)",
        "name_en": "🏮 Tap-to-Glow Sky Lanterns",
        "category": "luxury",
        "description_ku": "مێهڤان کلیل ل سەر فەنەرێن شەڤێ دکەت دا رووناهیا زێڕین تێدا هەلببیت و بەرەڤ ئاسمانی بفڕن و داخوازنامە ڤەببیت.",
        "description_ar": "يضغط الضيف على الفوانيس الملكية لإضاءتها بنور ذهبي دافئ لتعلو في السماء وتكشف عن دعوة الزفاف.",
        "description_en": "Interactive Tap-to-Glow night festival! Guests tap unlit royal lanterns to ignite them with warm golden fire; once lit, the lanterns float skyward and illuminate the wedding invitation.",
        "preview_style": {
            "bg": "#0F0C1D",
            "card": "#1A1530",
            "accent": "#F59E0B",
            "text": "#FFFBEB",
            "badge": "🏮 Tap to Light Up",
        },
        "default_theme": {
            "primary_color": "#F5B041",
            "secondary_color": "#FDE68A",
            "background_color": "#0F0C1D",
            "text_color": "#FFFBEB",
            "card_style": "lantern-glow",
            "particles": "fireflies",
            "opening_mode": "starlight_lantern_glow",
        },
        "has_butterfly_opening": 1,
        "sort_order": 11,
    },
    {
        "code": "moonlit_lake",
        "name_ku": "🌙 دەریاچەیا بەر هەیڤێ (Moonlit Lake)",
        "name_ar": "🌙 بحيرة ضوء القمر (Moonlit Lake)",
        "name_en": "🌙 Moonlit Lake",
        "category": "luxury",
        "description_ku": "شەڤەکا رۆمانسی ل سەر دەریاچەیێ، بیک و زاڤا ل سەر پێلێن ئاڤێ، مێشێن ئاگرین و ناڤێن وان د ناڤ شەوقا هەیڤێ دا.",
        "description_ar": "ليلة ساحرة على ضفاف البحيرة مع انعكاس القمر العملاق على الماء المتراقص واليراعات المضيئة وظهور أسماء العروسين في الماء.",
        "description_en": "Enchanted night lake with a giant glowing full moon, couple silhouette on a wooden dock, drifting fireflies, rippling water, and names shimmering inside the moon reflection.",
        "preview_style": {
            "bg": "#071126",
            "card": "#0D1D3A",
            "accent": "#F3D382",
            "text": "#F4F7FC",
            "badge": "🌙 Moon Reflection",
        },
        "default_theme": {
            "primary_color": "#F3D382",
            "secondary_color": "#9CC0F9",
            "background_color": "#071126",
            "text_color": "#F4F7FC",
            "card_style": "moonlit-water",
            "particles": "fireflies",
            "opening_mode": "moonlit_lake",
        },
        "has_butterfly_opening": 1,
        "sort_order": 12,
    },
    {
        "code": "wedding_train",
        "name_ku": "🚂 شەمەندەفەرا شەهیانێ (The Wedding Train)",
        "name_ar": "🚂 قطار الزفاف الملكي (The Wedding Train)",
        "name_en": "🚂 The Wedding Train",
        "category": "luxury",
        "description_ku": "شەمەندەفەرا شاهانە د ناڤ چیایان را دچیت؛ هەر فارگۆنەک پشکەکێ ڤەدکەت هەتا دگەهیتە وێستگەها ئاهەنگێ.",
        "description_ar": "قطار ملكي فاخر يسير بين الجبال، تكشف كل مقصورة منه قسماً جديداً حتى يصل في النهاية إلى محطة قاعة الزفاف.",
        "description_en": "Luxury Orient-Express style train traveling through scenic mountains. Camera follows the locomotive while each carriage reveals Couple → Date → Schedule → Venue → Gallery, arriving at the Grand Wedding Venue Station.",
        "preview_style": {
            "bg": "#141D24",
            "card": "#1E2B36",
            "accent": "#DFB25B",
            "text": "#F8F3E6",
            "badge": "🚂 Mountain Express",
        },
        "default_theme": {
            "primary_color": "#DFB25B",
            "secondary_color": "#F8F3E6",
            "background_color": "#141D24",
            "text_color": "#F8F3E6",
            "card_style": "train-carriage",
            "particles": "steam-sparks",
            "opening_mode": "wedding_train",
        },
        "has_butterfly_opening": 1,
        "sort_order": 13,
    },
    {
        "code": "floating_castle",
        "name_ku": "🏰 قەسرا ل سەر هەوران (Floating Castle)",
        "name_ar": "🏰 القلعة العائمة فوق السحاب (Floating Castle)",
        "name_en": "🏰 Floating Castle",
        "category": "luxury",
        "description_ku": "قەسرەکا ئەفسانەیی ل سەر هەورێن زێڕین؛ داخوازنامە وەکی نامەیەکا کەڤنار بەرەڤ قەسرێ دفڕیت.",
        "description_ar": "قلعة خيالية فاخرة تطفو فوق السحب المتحركة، وتظهر الدعوة كرسالة ملكية قديمة تطير تدريجياً نحو القلعة.",
        "description_en": "Fantasy luxury palace floating above drifting celestial clouds. The invitation appears as an ancient royal wax-sealed scroll that unfurls and flies gracefully into the castle gates.",
        "preview_style": {
            "bg": "#1D1636",
            "card": "#2A204B",
            "accent": "#F1C876",
            "text": "#FAF6FF",
            "badge": "🏰 Celestial Scroll",
        },
        "default_theme": {
            "primary_color": "#F1C876",
            "secondary_color": "#E6D8FF",
            "background_color": "#1D1636",
            "text_color": "#FAF6FF",
            "card_style": "celestial-scroll",
            "particles": "starlight",
            "opening_mode": "floating_castle",
        },
        "has_butterfly_opening": 1,
        "sort_order": 14,
    },
    {
        "code": "message_in_a_bottle",
        "name_ku": "🌊 نامە د ناڤ شووشەیێ دا (Message in a Bottle)",
        "name_ar": "🌊 رسالة في زجاجة البحر (Message in a Bottle)",
        "name_en": "🌊 Message in a Bottle",
        "category": "luxury",
        "description_ku": "دەریا ل دەمێ خۆرئاڤابوونێ؛ شووشەیەکا کریستالی بەرەڤ تە دهێت و ب لێدانەکێ ڤەدبیت و داخوازنامە ژێ دەردکەڤیت.",
        "description_ar": "محيط ساحر وقت الغروب، تطفو زجاجة كريستالية نحو الكاميرا وعند لمسها تُفتح وتخرج منها دعوة الزفاف.",
        "description_en": "Golden sunset ocean waves where a glowing crystal bottle floats toward the camera. When tapped, the cork pops open in golden sparkles and the rolled wedding scroll emerges.",
        "preview_style": {
            "bg": "#1E293B",
            "card": "#283548",
            "accent": "#F59E0B",
            "text": "#FFFBEB",
            "badge": "🌊 Sunset Bottle",
        },
        "default_theme": {
            "primary_color": "#F5B041",
            "secondary_color": "#FDE68A",
            "background_color": "#182538",
            "text_color": "#FFFBEB",
            "card_style": "sunset-ocean",
            "particles": "sea-sparkles",
            "opening_mode": "message_in_a_bottle",
        },
        "has_butterfly_opening": 1,
        "sort_order": 15,
    },
    {
        "code": "royal_luxury",
        "name_ku": "👑 شاهانەیا لوکس (Royal Luxury)",
        "name_ar": "👑 الفخامة الملكية (Royal Luxury)",
        "name_en": "👑 Royal Luxury",
        "category": "luxury",
        "description_ku": "نەخشێن شاهانە و چوارچێوێن زێڕین بو شەهیانێن مەزن.",
        "description_ar": "إطارات ملكية مذهبة وتفاصيل معمارية فخمة تليق بالليالي الكبرى.",
        "description_en": "Ornate royal crests, double-embossed gold borders, velvety depth shadows, and luminous shimmer.",
        "preview_style": {
            "bg": "#15121E",
            "card": "#1F1A2C",
            "accent": "#D4AF37",
            "text": "#F9F4E8",
            "badge": "Luxury • Royal Crest",
        },
        "default_theme": {
            "primary_color": "#D4AF37",
            "secondary_color": "#F9F4E8",
            "background_color": "#15121E",
            "text_color": "#F9F4E8",
            "card_style": "royal-velvet",
            "particles": "gold-dust",
        },
        "has_butterfly_opening": 1,
        "sort_order": 16,
    },
    {
        "code": "golden_palace",
        "name_ku": "🏛 کۆچکا زێڕین (Golden Palace)",
        "name_ar": "🏛 القصر الذهبي (Golden Palace)",
        "name_en": "🏛 Golden Palace",
        "category": "luxury",
        "description_ku": "درەوشانا کۆچکێن زێڕین ب کەوانەیێن رۆژهەلاتی و رووناهیا گەرم.",
        "description_ar": "أقواس القصور الشرقية المذهبة مع إضاءة دافئة وتفاصيل فاخرة.",
        "description_en": "Palatial arched domes, warm amber chandeliers, and intricate filigree corners with layered depth.",
        "preview_style": {
            "bg": "#F9F3E3",
            "card": "#FFFDF8",
            "accent": "#C99A2E",
            "text": "#2A1F14",
            "badge": "Luxury • Palatial Arch",
        },
        "default_theme": {
            "primary_color": "#C99A2E",
            "secondary_color": "#2A1F14",
            "background_color": "#F9F3E3",
            "text_color": "#2A1F14",
            "card_style": "palace-arch",
            "particles": "gold-sparkles",
        },
        "has_butterfly_opening": 1,
        "sort_order": 17,
    },
    {
        "code": "cinematic_garden",
        "name_ku": "🌿 باخچێ سینەمایی (Cinematic Garden)",
        "name_ar": "🌿 الحديقة السينمائية (Cinematic Garden)",
        "name_en": "🌿 Cinematic Garden",
        "category": "luxury",
        "description_ku": "سرۆشتێ سەوز و زێڕین ب پەلکێن گوڵان و رووناهیا خۆرئاڤابوونێ.",
        "description_ar": "أجواء الحدائق المسحورة عند الغروب مع بتلات مضيئة متطايرة.",
        "description_en": "Enchanted emerald-and-champagne conservatory with floating fireflies, parallax foliage, and golden hour lighting.",
        "preview_style": {
            "bg": "#11221B",
            "card": "#182E25",
            "accent": "#D8B467",
            "text": "#F4F7F4",
            "badge": "Luxury • Emerald Garden",
        },
        "default_theme": {
            "primary_color": "#D8B467",
            "secondary_color": "#F4F7F4",
            "background_color": "#11221B",
            "text_color": "#F4F7F4",
            "card_style": "emerald-glass",
            "particles": "fireflies",
        },
        "has_butterfly_opening": 1,
        "sort_order": 18,
    },
    {
        "code": "luxury_floral",
        "name_ku": "🌸 گوڵزارا شاهانە (Luxury Floral)",
        "name_ar": "🌸 الزهور الملكية (Luxury Floral)",
        "name_en": "🌸 Luxury Floral",
        "category": "luxury",
        "description_ku": "گوڵێن شاهانە یێن سێ-رەهەندی ب چوارچێوێن زێڕی و پەمبە.",
        "description_ar": "تنسيقات زهور ملكية فاخرة مع إطارات ذهبية بارزة.",
        "description_en": "Rich couture floral garlands in rose-gold and ivory with multi-layered paper embossing.",
        "preview_style": {
            "bg": "#FBF4F2",
            "card": "#FFFFFF",
            "accent": "#B97D60",
            "text": "#2D1E1B",
            "badge": "Luxury • Couture Rose",
        },
        "default_theme": {
            "primary_color": "#B97D60",
            "secondary_color": "#2D1E1B",
            "background_color": "#FBF4F2",
            "text_color": "#2D1E1B",
            "card_style": "couture-floral",
            "particles": "gold-dust",
        },
        "has_butterfly_opening": 1,
        "sort_order": 19,
    },
    {
        "code": "traditional_kurdish_luxury",
        "name_ku": "☀️ رەسەنا کوردی یا شاهانە (Kurdish Luxury)",
        "name_ar": "☀️ الأصالة الكردية الملكية (Kurdish Luxury)",
        "name_en": "☀️ Traditional Kurdish Luxury",
        "category": "luxury",
        "description_ku": "نەخش و نیگارێن کەلتۆرێ بادینان و کوردستانێ ب رەنگێ یاقووتی و زێڕێ شاهانە.",
        "description_ar": "مستوحى من التراث الكردي الأصيل في بادينان بألوان الياقوت الأحمر والذهب الخالص.",
        "description_en": "Celebrates Badinan & Kurdish heritage with deep ruby-burgundy velvet, antique gold filigree motifs, and warm lantern glow.",
        "preview_style": {
            "bg": "#2B0E14",
            "card": "#3B141C",
            "accent": "#E2B659",
            "text": "#FDF7EC",
            "badge": "Luxury • Badini Heritage",
        },
        "default_theme": {
            "primary_color": "#E2B659",
            "secondary_color": "#FDF7EC",
            "background_color": "#2B0E14",
            "text_color": "#FDF7EC",
            "card_style": "kurdish-heritage",
            "particles": "gold-dust",
        },
        "has_butterfly_opening": 1,
        "sort_order": 20,
    },
    {
        "code": "black_and_gold",
        "name_ku": "🖤 ڕەش و زێڕین (Black & Gold)",
        "name_ar": "🖤 الأسود والذهبي (Black & Gold)",
        "name_en": "🖤 Black & Gold",
        "category": "luxury",
        "description_ku": "ئەوپەڕێ فەخامەتێ ب تێکەلکرنا رەنگێ ڕەشێ مەخمەلی و زێڕێ درەوشاوە.",
        "description_ar": "قمة الفخامة العصرية بمزيج الأسود المخملي والذهب اللامع.",
        "description_en": "Obsidian black-tie sophistication with brushed 24k gold foil borders and dramatic spotlighting.",
        "preview_style": {
            "bg": "#0D0D0F",
            "card": "#16161A",
            "accent": "#D4AF37",
            "text": "#F5F2EB",
            "badge": "Luxury • Black Tie Gold",
        },
        "default_theme": {
            "primary_color": "#D4AF37",
            "secondary_color": "#F5F2EB",
            "background_color": "#0D0D0F",
            "text_color": "#F5F2EB",
            "card_style": "obsidian-gold",
            "particles": "gold-dust",
        },
        "has_butterfly_opening": 1,
        "sort_order": 21,
    },
    {
        "code": "romantic_crystal",
        "name_ku": "💎 کریستالێ رۆمانسی (Romantic Crystal)",
        "name_ar": "💎 الكريستال الرومانسي (Romantic Crystal)",
        "name_en": "💎 Romantic Crystal",
        "category": "luxury",
        "description_ku": "درەوشانا کریستالی و شووشەیی (Glassmorphism) تایبەت بو شەڤێن هۆلا کریستال.",
        "description_ar": "تأثيرات الكريستال المتلألئ والزجاج المصقول لليلة ساحرة.",
        "description_en": "Prismatic chandelier reflections, frosted crystal glass cards, and shimmering diamond particles.",
        "preview_style": {
            "bg": "#F2F5FA",
            "card": "#FFFFFF",
            "accent": "#B5945B",
            "text": "#1E2430",
            "badge": "Luxury • Frosted Crystal",
        },
        "default_theme": {
            "primary_color": "#B5945B",
            "secondary_color": "#1E2430",
            "background_color": "#F2F5FA",
            "text_color": "#1E2430",
            "card_style": "crystal-glass",
            "particles": "crystal-shimmer",
        },
        "has_butterfly_opening": 1,
        "sort_order": 22,
    },
]


def _ensure_demo_audio(static_dir: Path) -> str:
    """
    Generate a serene, legitimate Kurdish/Persian-inspired instrumental wedding melody
    as a real playable WAV audio file so the demo music system works immediately out-of-the-box.
    """
    audio_dir = static_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    wav_path = audio_dir / "bikozava_kurdish_serenade.wav"

    if wav_path.exists() and wav_path.stat().st_size > 10000:
        return "/static/audio/bikozava_kurdish_serenade.wav"

    sample_rate = 22050
    melody = [
        (293.66, 146.83, 2.0),
        (349.23, 174.61, 2.0),
        (392.00, 196.00, 2.0),
        (440.00, 220.00, 2.0),
        (466.16, 233.08, 2.0),
        (440.00, 220.00, 2.0),
        (392.00, 196.00, 2.0),
        (293.66, 146.83, 2.0),
    ]

    frames = bytearray()
    sample_idx = 0
    for lead_freq, bass_freq, note_dur in melody:
        note_samples = int(sample_rate * note_dur)
        for i in range(note_samples):
            t = i / sample_rate
            global_t = sample_idx / sample_rate
            attack = min(1.0, t / 0.12)
            decay = math.exp(-1.35 * t)
            env = attack * decay

            lead = (
                0.55 * math.sin(2.0 * math.pi * lead_freq * global_t)
                + 0.22 * math.sin(2.0 * math.pi * (lead_freq * 2.0) * global_t)
                + 0.08 * math.sin(2.0 * math.pi * (lead_freq * 3.0) * global_t)
            )
            pad_env = math.sin(math.pi * (t / note_dur))
            strings = (
                0.30 * math.sin(2.0 * math.pi * bass_freq * global_t)
                + 0.18 * math.sin(2.0 * math.pi * (bass_freq * 1.5) * global_t)
            ) * pad_env

            val = (lead * env + strings) * 0.38
            pcm = max(-32767, min(32767, int(val * 32767)))
            frames += struct.pack("<h", pcm)
            sample_idx += 1

    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))

    return "/static/audio/bikozava_kurdish_serenade.wav"


def _ensure_demo_images(static_dir: Path) -> Dict[str, str]:
    """
    Generate refined, artistic luxury wedding placeholder photography (WebP)
    for Ismail & Shrin's demo invitation.
    """
    img_dir = static_dir / "img" / "demo"
    img_dir.mkdir(parents=True, exist_ok=True)

    specs = {
        "couple": ("couple_ismail_shrin.webp", (900, 1100), (248, 241, 229), (196, 154, 78)),
        "groom": ("groom_ismail.webp", (700, 850), (242, 235, 222), (175, 138, 68)),
        "bride": ("bride_shrin.webp", (700, 850), (250, 242, 236), (198, 152, 116)),
        "gallery_1": ("gallery_crystal_hall.webp", (900, 680), (246, 238, 224), (200, 162, 83)),
        "gallery_2": ("gallery_rings.webp", (900, 680), (251, 246, 237), (186, 146, 72)),
        "gallery_3": ("gallery_celebration.webp", (900, 680), (243, 234, 220), (170, 130, 62)),
    }

    paths: Dict[str, str] = {}
    for key, (fname, (w, h), bg_rgb, gold_rgb) in specs.items():
        fpath = img_dir / fname
        paths[key] = f"/static/img/demo/{fname}"
        if fpath.exists() and fpath.stat().st_size > 1000:
            continue

        base = Image.new("RGB", (w, h), bg_rgb)
        draw = ImageDraw.Draw(base, "RGBA")

        for step in range(12, 0, -1):
            alpha = int(14 * (13 - step) / 12)
            inset = step * 18
            draw.ellipse(
                [inset, inset, w - inset, h - inset],
                fill=(gold_rgb[0], gold_rgb[1], gold_rgb[2], alpha),
            )

        pad = 36
        draw.rectangle([pad, pad, w - pad, h - pad], outline=gold_rgb + (210,), width=3)
        draw.rectangle([pad + 12, pad + 12, w - pad - 12, h - pad - 12], outline=gold_rgb + (130,), width=1)

        arch_margin = 90
        draw.arc(
            [arch_margin, arch_margin, w - arch_margin, h - arch_margin],
            start=180,
            end=360,
            fill=gold_rgb + (180,),
            width=3,
        )

        cx, cy = w // 2, h // 2
        r = min(w, h) // 5
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 253, 248, 235), outline=gold_rgb + (220,), width=3)
        draw.ellipse([cx - r + 10, cy - r + 10, cx + r - 10, cy + r - 10], outline=gold_rgb + (120,), width=1)

        base.save(fpath, format="WEBP", quality=88)

    return paths


def seed_database() -> None:
    """
    Idempotently seed admin user, all 22 templates (including `champagne_envelope_foil`
    and `champagne_envelope_photos`), and the Ismail & Shrin demo wedding.
    """
    db = get_db()
    static_dir = Path(current_app.static_folder)

    admin_username = current_app.config["ADMIN_INITIAL_USERNAME"]
    admin_email = current_app.config["ADMIN_INITIAL_EMAIL"]
    admin_password = current_app.config["ADMIN_INITIAL_PASSWORD"]

    existing_admin = db.fetchone(
        "SELECT id, password_hash FROM users WHERE username = ? OR email = ?",
        (admin_username, admin_email),
    )
    if not existing_admin:
        admin_id = db.insert(
            """
            INSERT INTO users (username, email, password_hash, role, is_active)
            VALUES (?, ?, ?, 'admin', 1)
            """,
            (
                admin_username,
                admin_email,
                hash_password(admin_password),
            ),
        )
    else:
        admin_id = int(existing_admin["id"])
        if not verify_password(admin_password, existing_admin["password_hash"]):
            db.execute(
                "UPDATE users SET username = ?, email = ?, password_hash = ?, is_active = 1 WHERE id = ?",
                (admin_username, admin_email, hash_password(admin_password), admin_id),
            )
            db.commit()

    for tmpl in TEMPLATES_SEED:
        existing_t = db.fetchone("SELECT id FROM templates WHERE code = ?", (tmpl["code"],))
        if not existing_t:
            db.insert(
                """
                INSERT INTO templates (
                    code, name_ku, name_ar, name_en, category,
                    description_ku, description_ar, description_en,
                    preview_style, default_theme, has_butterfly_opening,
                    is_active, sort_order
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    tmpl["code"],
                    tmpl["name_ku"],
                    tmpl["name_ar"],
                    tmpl["name_en"],
                    tmpl["category"],
                    tmpl["description_ku"],
                    tmpl["description_ar"],
                    tmpl["description_en"],
                    json.dumps(tmpl["preview_style"], ensure_ascii=False),
                    json.dumps(tmpl["default_theme"], ensure_ascii=False),
                    int(tmpl["has_butterfly_opening"]),
                    int(tmpl["sort_order"]),
                ),
            )
        else:
            db.execute(
                """
                UPDATE templates SET
                    name_ku = ?, name_ar = ?, name_en = ?, category = ?,
                    description_ku = ?, description_ar = ?, description_en = ?,
                    preview_style = ?, default_theme = ?, has_butterfly_opening = ?, sort_order = ?
                WHERE code = ?
                """,
                (
                    tmpl["name_ku"],
                    tmpl["name_ar"],
                    tmpl["name_en"],
                    tmpl["category"],
                    tmpl["description_ku"],
                    tmpl["description_ar"],
                    tmpl["description_en"],
                    json.dumps(tmpl["preview_style"], ensure_ascii=False),
                    json.dumps(tmpl["default_theme"], ensure_ascii=False),
                    int(tmpl["has_butterfly_opening"]),
                    int(tmpl["sort_order"]),
                    tmpl["code"],
                ),
            )
    db.commit()

    demo_music_url = _ensure_demo_audio(static_dir)
    demo_imgs = _ensure_demo_images(static_dir)
    demo_vertical_video = "/static/video/demo_vertical_9_16.mp4"

    existing_inv = db.fetchone("SELECT id, hero_video_url FROM invitations WHERE slug = ?", ("ismail_shrin",))
    if not existing_inv:
        theme_settings = {
            "card_border_gold": "#C8A253",
            "paper_ivory": "#FAF6EE",
            "butterfly_3d": True,
            "golden_particles": True,
            "luxury_lighting": True,
        }
        inv_id = db.insert(
            """
            INSERT INTO invitations (
                slug,
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
                theme_settings, is_published, preview_token, created_by
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?
            )
            """,
            (
                "ismail_shrin",
                "Ismail",
                "Shrin",
                "إسماعيل",
                "شرين",
                "Ismail",
                "Shrin",
                "2026-11-21",
                "19:00",
                "Crystal Hall",
                "قاعة كريستال (Crystal Hall)",
                "Crystal Hall",
                "هۆلا کریستال — دهۆک، هەرێما کوردستانێ",
                "قاعة كريستال للأفراح — دهوك، إقليم كردستان",
                "Crystal Hall Grand Ballroom — Duhok, Kurdistan Region",
                "https://maps.app.goo.gl/LYHw6XCJdNMJyQK48?g_st=ac",
                "",
                "magical_butterfly",
                "ku",
                "#C8A253",
                "#1E1915",
                "#FAF6EE",
                "#241C15",
                "Vazirmatn",
                "Cormorant Garamond",
                "کلیل بکە بو ڤەکرنا داخوازنامێ",
                "کلیل بکە بو ڤەکرنا داخوازنامێ",
                "کلیل بکە بو ڤەکرنا داخوازنامێ",
                demo_imgs["bride"],
                demo_imgs["groom"],
                demo_imgs["couple"],
                demo_vertical_video,
                "upload",
                demo_music_url,
                "",
                "Kurdish Royal Instrumental Serenade",
                1,
                json.dumps(theme_settings, ensure_ascii=False),
                secrets.token_urlsafe(24),
                admin_id,
            ),
        )

        exact_schedule_items = [
            {
                "time": "7:00",
                "title_ku": "بخێرهاتن",
                "title_ar": "استقبال الضيوف والترحيب",
                "title_en": "Guest Welcome & Reception",
                "icon": "sparkles",
            },
            {
                "time": "7:30",
                "title_ku": "هاتنا بیکو زاڤا",
                "title_ar": "دخول العروسين (زفة العروسين)",
                "title_en": "Grand Entrance of Bride & Groom",
                "icon": "heart",
            },
            {
                "time": "8:00",
                "title_ku": "شیڤ خارن",
                "title_ar": "مأدبة العشاء الفاخرة",
                "title_en": "Royal Wedding Dinner",
                "icon": "utensils",
            },
            {
                "time": "9:00",
                "title_ku": "دیلان",
                "title_ar": "الدبكة الكردية والاحتفال",
                "title_en": "Kurdish Dilan Dance & Celebration",
                "icon": "music",
            },
        ]

        sections_seed = [
            {
                "section_type": "opening_card",
                "title_ku": "کلیل بکە بو ڤەکرنا داخوازنامێ",
                "title_ar": "کلیل بکە بو ڤەکرنا داخوازنامێ",
                "title_en": "کلیل بکە بو ڤەکرنا داخوازنامێ",
                "subtitle_ku": "Ismail & Shrin • 21 November 2026",
                "subtitle_ar": "Ismail & Shrin • 21 November 2026",
                "subtitle_en": "Ismail & Shrin • 21 November 2026",
                "content_ku": "ب ناڤێ خودایێ مەزن و دلۆڤان",
                "content_ar": "بسم الله الرحمن الرحيم",
                "content_en": "In the Name of Love & Unity",
                "content_json": {"card_prompt": "کلیل بکە بو ڤەکرنا داخوازنامێ"},
                "is_enabled": 1,
                "sort_order": 1,
            },
            {
                "section_type": "couple",
                "title_ku": "Ismail & Shrin",
                "title_ar": "إسماعيل & شرين",
                "title_en": "Ismail & Shrin",
                "subtitle_ku": "21 November 2026 • Crystal Hall",
                "subtitle_ar": "21 نوفمبر 2026 • قاعة كريستال",
                "subtitle_en": "21 November 2026 • Crystal Hall",
                "content_ku": "ب دلەکێ پڕی ئەڤینی و وەفاداری، ئەم هەردوو دێ پێنگاڤەکا نوی د ژیانا خۆ دا هاڤێژین.",
                "content_ar": "بقلبين يجمعهما الحب والمودة، نبدأ معاً أجمل فصول حياتنا.",
                "content_en": "Two hearts, one timeless promise. Join us as we celebrate the beginning of our forever.",
                "content_json": {
                    "groom_display": "Ismail",
                    "bride_display": "Shrin",
                    "date_display": "21 November 2026",
                },
                "is_enabled": 1,
                "sort_order": 2,
            },
            {
                "section_type": "countdown",
                "title_ku": "دەمێ مایی بو شەڤا شەهیانێ",
                "title_ar": "العد التنازلي لليلة الزفاف",
                "title_en": "Countdown to the Celebration",
                "subtitle_ku": "21 November 2026 • 7:00 PM",
                "subtitle_ar": "21 نوفمبر 2026 • 7:00 مساءً",
                "subtitle_en": "21 November 2026 • 7:00 PM",
                "content_ku": "چاڤەرێی دیتنا هەوە یێن خۆشتڤی نە د ڤێ شەڤا تایبەت دا",
                "content_ar": "نعدّ الأيام والساعات للقائكم في ليلتنا المميزة",
                "content_en": "Every second brings us closer to celebrating with you",
                "content_json": {"target_iso": "2026-11-21T19:00:00"},
                "is_enabled": 1,
                "sort_order": 3,
            },
            {
                "section_type": "wedding_details",
                "title_ku": "هویرکاریێن شەهیانێ",
                "title_ar": "تفاصيل حفل الزفاف",
                "title_en": "Wedding Celebration Details",
                "subtitle_ku": "ب ناڤێ هەردوو بنەمالان ب خێرهاتنا هەوە دکەین",
                "subtitle_ar": "باسم العائلتين الكريمتين نتشرف بدعوتكم",
                "subtitle_en": "Together with our families, we joyfully invite you",
                "content_ku": (
                    "ب دلەکێ پڕی خۆشی و رێزگرتن داخوازێ ژ هەوە یێن هێژا دکەین "
                    "کو ب ئامادەبوونا خۆ ئاهەنگا شەهیانا مە ل هۆلا کریستال ب خەملینن. "
                    "هاتنا هەوە جھێ شانازی و دلخۆشیا مەیە."
                ),
                "content_ar": (
                    "يسرنا ويشرفنا دعوتكم لحضور حفل زفافنا ومشاركتنا أجمل لحظات العمر في قاعة كريستال. "
                    "حضوركم بيننا يزيد فرحتنا بهجة وسروراً."
                ),
                "content_en": (
                    "We warmly invite you to share in our happiness as we exchange vows and celebrate "
                    "our marriage at Crystal Hall on Saturday, 21 November 2026 at 7:00 PM."
                ),
                "content_json": {
                    "date_display": "21 November 2026",
                    "time_display": "7:00 PM",
                    "venue_display": "Crystal Hall",
                },
                "is_enabled": 1,
                "sort_order": 4,
            },
            {
                "section_type": "schedule",
                "title_ku": "بەرنامێ شەڤێ",
                "title_ar": "برنامج الأمسية",
                "title_en": "Evening Schedule",
                "subtitle_ku": "ڕێڕەوا ئاهەنگا شەڤا شەهیانێ",
                "subtitle_ar": "فقرات حفل الزفاف",
                "subtitle_en": "Order of Events for the Evening",
                "content_ku": "7:00 — بخێرهاتن\n7:30 — هاتنا بیکو زاڤا\n8:00 — شیڤ خارن\n9:00 — دیلان",
                "content_ar": "7:00 — استقبال الضيوف\n7:30 — دخول العروسين\n8:00 — العشاء\n9:00 — الدبكة الكردية (ديلان)",
                "content_en": "7:00 — Welcome Reception\n7:30 — Couple Grand Entrance\n8:00 — Dinner Service\n9:00 — Traditional Dilan Dance",
                "content_json": {"items": exact_schedule_items},
                "is_enabled": 1,
                "sort_order": 5,
            },
            {
                "section_type": "venue",
                "title_ku": "Crystal Hall",
                "title_ar": "Crystal Hall — قاعة كريستال",
                "title_en": "Crystal Hall",
                "subtitle_ku": "جهێ ئاهەنگێ و نەخشێ گەهشتنێ",
                "subtitle_ar": "مكان إقامة الحفل والموقع على الخريطة",
                "subtitle_en": "Grand Wedding Venue & Google Maps Navigation",
                "content_ku": "هۆلا کریستال (Crystal Hall) — ژ بو گەهشتنا ب ساناهی ب مۆبایلێ، کلیل ل سەر دوگما نەخشەی بکە.",
                "content_ar": "قاعة كريستال للأفراح (Crystal Hall) — للوصول السريع عبر الهاتف يرجى الضغط على زر خرائط جوجل أدناه.",
                "content_en": "Crystal Hall — Tap the Google Maps button below for direct mobile turn-by-turn navigation to the venue.",
                "content_json": {
                    "venue_name": "Crystal Hall",
                    "map_url": "https://maps.app.goo.gl/LYHw6XCJdNMJyQK48?g_st=ac",
                },
                "is_enabled": 1,
                "sort_order": 6,
            },
            {
                "section_type": "gallery",
                "title_ku": "ئەلبوما وێنەیان",
                "title_ar": "معرض الصور",
                "title_en": "Photo Gallery",
                "subtitle_ku": "چەند دیمەنەک ژ یادگاریێن مە",
                "subtitle_ar": "لقطات من ذكرياتنا الجميلة",
                "subtitle_en": "Captured Moments of Our Journey",
                "content_ku": "",
                "content_ar": "",
                "content_en": "",
                "content_json": {
                    "images": [
                        {
                            "url": demo_imgs["gallery_1"],
                            "caption_ku": "هۆلا کریستال — شەڤا خەونان",
                            "caption_ar": "قاعة كريستال — ليلة العمر",
                            "caption_en": "Crystal Hall — Our Dream Evening",
                        },
                        {
                            "url": demo_imgs["gallery_2"],
                            "caption_ku": "پەیمانا ئەڤینیێ • 21.11.2026",
                            "caption_ar": "عهد المحبة • 21.11.2026",
                            "caption_en": "Promise of Forever • 21.11.2026",
                        },
                        {
                            "url": demo_imgs["gallery_3"],
                            "caption_ku": "بیکو زاڤا — Ismail & Shrin",
                            "caption_ar": "العروسان — إسماعيل وشرين",
                            "caption_en": "Ismail & Shrin",
                        },
                    ]
                },
                "is_enabled": 1,
                "sort_order": 7,
            },
            {
                "section_type": "rsvp",
                "title_ku": "پشتراستکرنا ئامادەبوونێ",
                "title_ar": "تأكيد الحضور",
                "title_en": "Confirm Your Attendance",
                "subtitle_ku": "تکایە ئامادەبوونا خۆ بو مە دیار بکە",
                "subtitle_ar": "يسعدنا تسجيل حضوركم ومشاركتنا الفرحة",
                "subtitle_en": "Kindly let us know if you will celebrate with us",
                "content_ku": "بەرسڤا هەوە هاریکاریا مە دکەت بو رێکخستنا پێشوازیەکا شایستەی هەوە.",
                "content_ar": "تأكيدكم يساعدنا على خدمتكم واستقبالكم بأفضل صورة.",
                "content_en": "Your response helps us prepare a wonderful evening for all our honored guests.",
                "content_json": {},
                "is_enabled": 1,
                "sort_order": 8,
            },
            {
                "section_type": "calendar",
                "title_ku": "تۆمارکرنا رۆژا شەهیانێ د رۆژژمێرێ دا",
                "title_ar": "حفظ الموعد في التقويم",
                "title_en": "Save the Date to Your Calendar",
                "subtitle_ku": "٢١ێ چریا دووێ ٢٠٢٦ • شەمبی • 7:00 PM",
                "subtitle_ar": "السبت، 21 نوفمبر 2026 • 7:00 مساءً",
                "subtitle_en": "Saturday, 21 November 2026 • 7:00 PM",
                "content_ku": "رۆژا شەهیانێ د رۆژژمێرا مۆبایلا خۆ دا خەزن بکە دا بیرهاتن بو تە بهێت.",
                "content_ar": "أضف موعد الحفل إلى تقويم هاتفك لتذكيرك بليلة الزفاف.",
                "content_en": "Add our wedding evening to Google Calendar or Apple/Outlook Calendar with one tap.",
                "content_json": {"year": 2026, "month": 11, "day": 21},
                "is_enabled": 1,
                "sort_order": 9,
            },
            {
                "section_type": "closing",
                "title_ku": "ب خێربێن سەرچاڤان",
                "title_ar": "ودامت دياركم عامرة بالأفراح",
                "title_en": "With Love & Gratitude",
                "subtitle_ku": "Ismail & Shrin • 21 November 2026",
                "subtitle_ar": "إسماعيل & شرين • 21 نوفمبر 2026",
                "subtitle_en": "Ismail & Shrin • 21 November 2026",
                "content_ku": "ئامادەبوونا هەوە چرایێ شەڤا مە گەشتر لێ دکەت و جھێ شانازی و دلخۆشیا مەیە.",
                "content_ar": "بحضوركم تكتمل فرحتنا وتزدان ليلتنا بهجة وسروراً.",
                "content_en": "Thank you for being part of our lives and sharing in the magic of our wedding night.",
                "content_json": {},
                "is_enabled": 1,
                "sort_order": 10,
            },
        ]

        for sec in sections_seed:
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
                    inv_id,
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
                    json.dumps(sec["content_json"], ensure_ascii=False),
                    sec["is_enabled"],
                    sec["sort_order"],
                ),
            )

        for idx, g_key in enumerate(["gallery_1", "gallery_2", "gallery_3"], start=1):
            db.insert(
                """
                INSERT INTO media_uploads (
                    invitation_id, media_role, original_filename, stored_filename,
                    file_path, thumb_path, mime_type, file_size,
                    caption_ku, caption_ar, caption_en, sort_order, uploaded_by
                ) VALUES (?, 'gallery', ?, ?, ?, ?, 'image/webp', 24000, ?, ?, ?, ?, ?)
                """,
                (
                    inv_id,
                    f"{g_key}.webp",
                    f"{g_key}.webp",
                    demo_imgs[g_key],
                    demo_imgs[g_key],
                    "دیمەنەک ژ ئاهەنگا شەهیانێ",
                    "لقطة من حفل الزفاف",
                    "Wedding Celebration Moment",
                    idx,
                    admin_id,
                ),
            )
    else:
        if not existing_inv.get("hero_video_url"):
            db.execute(
                "UPDATE invitations SET hero_video_url = ? WHERE id = ?",
                (demo_vertical_video, existing_inv["id"]),
            )
            db.commit()
