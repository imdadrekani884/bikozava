/**
 * BIKOZAVA — ADMIN STUDIO & SECTION BUILDER SCRIPT (`admin.js`)
 */

(function () {
  "use strict";

  window.showAdminToast = function (msg) {
    const toast = document.getElementById("toast-notification");
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add("show");
    setTimeout(function () {
      toast.classList.remove("show");
    }, 2600);
  };

  window.copyPublicUrl = function (relativeOrFullPath) {
    const fullUrl =
      relativeOrFullPath.indexOf("http") === 0
        ? relativeOrFullPath
        : window.location.origin + relativeOrFullPath;

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(fullUrl).then(function () {
        window.showAdminToast("Copied Public URL: " + fullUrl);
      });
    } else {
      const temp = document.createElement("input");
      document.body.appendChild(temp);
      temp.value = fullUrl;
      temp.select();
      document.execCommand("copy");
      document.body.removeChild(temp);
      window.showAdminToast("Copied Public URL: " + fullUrl);
    }
  };

  window.autoSlug = function () {
    const groomEl = document.getElementById("new_groom");
    const brideEl = document.getElementById("new_bride");
    const slugEl = document.getElementById("new_slug");
    if (!groomEl || !brideEl || !slugEl) return;

    const g = (groomEl.value || "").toLowerCase().replace(/[^a-z0-9]+/g, "").trim();
    const b = (brideEl.value || "").toLowerCase().replace(/[^a-z0-9]+/g, "").trim();
    if (g || b) {
      slugEl.value = [g, b].filter(Boolean).join("_");
    }
  };

  window.generateSlugFromNames = function () {
    const groomEl = document.getElementById("edit_groom_en") || document.getElementById("edit_groom_ku");
    const brideEl = document.getElementById("edit_bride_en") || document.getElementById("edit_bride_ku");
    const slugEl = document.getElementById("edit_slug");
    if (!groomEl || !brideEl || !slugEl) return;

    const g = (groomEl.value || "").toLowerCase().replace(/[^a-z0-9]+/g, "").trim();
    const b = (brideEl.value || "").toLowerCase().replace(/[^a-z0-9]+/g, "").trim();
    if (g || b) {
      slugEl.value = [g, b].filter(Boolean).join("_");
      window.showAdminToast("Generated slug: /" + slugEl.value);
    }
  };

  window.switchStudioTab = function (panelId, btnEl) {
    const panels = document.querySelectorAll(".studio-panel");
    panels.forEach(function (p) {
      p.classList.remove("active");
    });
    const tabs = document.querySelectorAll(".studio-tab");
    tabs.forEach(function (t) {
      t.classList.remove("active");
    });

    const target = document.getElementById(panelId);
    if (target) target.classList.add("active");
    if (btnEl) btnEl.classList.add("active");
  };

  window.toggleSectionDrawer = function (drawerId) {
    const drawer = document.getElementById(drawerId);
    if (!drawer) return;
    drawer.classList.toggle("open");
  };

  window.applyTemplateDefaults = function (primary, secondary, bg, text, radioEl) {
    const cards = document.querySelectorAll(".template-choice-card");
    cards.forEach(function (c) {
      c.classList.remove("selected");
    });
    if (radioEl && radioEl.closest(".template-choice-card")) {
      radioEl.closest(".template-choice-card").classList.add("selected");
    }

    const pInput = document.getElementById("color_primary");
    const sInput = document.getElementById("color_secondary");
    const bInput = document.getElementById("color_bg");
    const tInput = document.getElementById("color_text");
    if (pInput && primary) pInput.value = primary;
    if (sInput && secondary) sInput.value = secondary;
    if (bInput && bg) bInput.value = bg;
    if (tInput && text) tInput.value = text;
  };

  window.setPreviewDevice = function (mode) {
    const frame = document.getElementById("preview-frame-shell");
    const btnMob = document.getElementById("btn-prev-mobile");
    const btnDesk = document.getElementById("btn-prev-desktop");
    if (!frame) return;

    if (mode === "desktop") {
      frame.classList.add("desktop-mode");
      if (btnDesk) btnDesk.classList.add("active");
      if (btnMob) btnMob.classList.remove("active");
    } else {
      frame.classList.remove("desktop-mode");
      if (btnMob) btnMob.classList.add("active");
      if (btnDesk) btnDesk.classList.remove("active");
    }
  };

  window.setPreviewLang = function (langCode, btnEl) {
    const iframe = document.getElementById("live-preview-iframe");
    if (!iframe) return;

    const btns = document.querySelectorAll(".btn-lang-prev");
    btns.forEach(function (b) {
      b.classList.remove("active");
    });
    if (btnEl) btnEl.classList.add("active");

    const url = new URL(iframe.src, window.location.origin);
    url.searchParams.set("lang", langCode);
    iframe.src = url.toString();
  };

  window.reloadPreviewIframe = function () {
    const iframe = document.getElementById("live-preview-iframe");
    if (iframe && iframe.contentWindow) {
      iframe.contentWindow.location.reload();
    }
  };

  // Auto-open sectionbuilder tab if URL hash points to #section-builder or #sec-*
  document.addEventListener("DOMContentLoaded", function () {
    const h = window.location.hash || "";
    const tabs = document.querySelectorAll(".studio-tab");
    if (h.indexOf("#section-builder") === 0 || h.indexOf("#sec-") === 0) {
      if (tabs[1]) window.switchStudioTab("tab-sections", tabs[1]);
    } else if (h.indexOf("#media-manager") === 0) {
      if (tabs[3]) window.switchStudioTab("tab-media", tabs[3]);
    }
  });
})();
