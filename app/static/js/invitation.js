/**
 * BIKOZAVA — PUBLIC INVITATION INTERACTIVE ENGINE (`invitation.js`)
 *
 * Implements:
 * 1. Multi-Experience Opening Choreography:
 *    - ✨ `champagne_envelope_foil` & `champagne_envelope_photos`:
 *      Luxury Champagne Envelope & Gold Foil Card + Continuous Full-Page Ambient Canvas
 *      (Floating 5-Petal Blossoms, Rose Petals, Flapping Golden/Blush Butterflies, Gold Dust,
 *      and Interactive Touch/Click Sparkle Bursts)
 *    - 🦋 `magical_butterfly` & `vertical_cinema_reel`: 13-Step 3D Card & Butterfly Opening
 *      (and for `vertical_cinema_reel`, automatically starts the 9:16 vertical video hero slide
 *      with Bride & Groom names overlaid at the top-middle!)
 *    - 🪙 `golden_scratch_reveal`: Interactive 24k Gold Foil Scratch-Off Canvas
 *    - 🏮 `starlight_lantern_glow`: Interactive Tap-to-Glow Sky Lanterns
 *    - 🌙 `moonlit_lake`: Rippling moonlit lake & firefly swirl zoom
 *    - 🚂 `wedding_train`: Luxury mountain express departure & steam whistle reveal
 *    - 🏰 `floating_castle`: Ancient wax-sealed scroll flying into the floating castle gates
 *    - 🌊 `message_in_a_bottle`: Cork popping open & wedding scroll emerging from the bottle
 * 2. Dual Post-Interaction Wedding Audio Controller (Admin Uploaded MP3/WAV + YouTube IFrame API)
 * 3. Live Wedding Countdown Timer
 * 4. Async RSVP Form Submission & Gallery Lightbox
 */

(function () {
  "use strict";

  let isOpeningInProgress = false;
  let hasOpenedCard = false;
  let particleBurstMultiplier = 1;
  let ytPlayer = null;
  let ytReady = false;
  let ytPendingPlay = false;

  const prefersReducedMotion =
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ===========================================================================
  // 1A. CHAMPAGNE ENVELOPE FULL-PAGE AMBIENT CANVAS
  //     (Blossoms, Rose Petals, Flapping Butterflies, Gold Dust & Touch Sparkles)
  // ===========================================================================
  function initChampagneFloralCanvas() {
    const canvas = document.getElementById("champagne-ambient-canvas");
    if (!canvas || prefersReducedMotion) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let cw = (canvas.width = window.innerWidth);
    let ch = (canvas.height = window.innerHeight);

    window.addEventListener("resize", function () {
      cw = canvas.width = window.innerWidth;
      ch = canvas.height = window.innerHeight;
    });

    const goldPalette = ["#DFCA97", "#C8A86B", "#B38F48", "#F4E8CB", "#FFFDF9"];
    const flowerPalettes = [
      { fill: "rgba(255, 240, 243, 0.75)", stroke: "rgba(212, 165, 165, 0.5)", center: "#C8A86B" },
      { fill: "rgba(251, 245, 230, 0.8)", stroke: "rgba(200, 168, 107, 0.55)", center: "#B38F48" },
      { fill: "rgba(244, 232, 203, 0.7)", stroke: "rgba(179, 143, 72, 0.45)", center: "#946E2E" },
      { fill: "rgba(253, 232, 232, 0.7)", stroke: "rgba(200, 168, 107, 0.45)", center: "#DFCA97" },
    ];

    function GoldParticle() {
      this.reset(true);
    }
    GoldParticle.prototype.reset = function (initial) {
      this.x = Math.random() * cw;
      this.y = initial ? Math.random() * ch : ch + 20;
      this.size = Math.random() * 2.2 + 0.8;
      this.speedY = -(Math.random() * 0.4 + 0.15);
      this.speedX = (Math.random() - 0.5) * 0.3;
      this.alpha = Math.random() * 0.55 + 0.15;
      this.alphaChange = Math.random() * 0.008 + 0.003;
      this.color = goldPalette[Math.floor(Math.random() * goldPalette.length)];
    };
    GoldParticle.prototype.update = function () {
      this.y += this.speedY;
      this.x += this.speedX + Math.sin(this.y * 0.015) * 0.2;
      this.alpha += this.alphaChange;
      if (this.alpha > 0.75 || this.alpha < 0.1) this.alphaChange = -this.alphaChange;
      if (this.y < -20) this.reset(false);
    };
    GoldParticle.prototype.draw = function () {
      ctx.save();
      ctx.globalAlpha = Math.max(0, this.alpha);
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
      ctx.fillStyle = this.color;
      ctx.shadowBlur = 6;
      ctx.shadowColor = "#C8A86B";
      ctx.fill();
      ctx.restore();
    };

    function FloatingFlower() {
      this.reset(true);
    }
    FloatingFlower.prototype.reset = function (initial) {
      this.x = Math.random() * cw;
      this.y = initial ? Math.random() * ch : -30;
      this.size = Math.random() * 7 + 5;
      this.speedY = Math.random() * 0.45 + 0.25;
      this.speedX = (Math.random() - 0.5) * 0.4;
      this.rotation = Math.random() * Math.PI * 2;
      this.rotSpeed = (Math.random() - 0.5) * 0.015;
      this.swayPhase = Math.random() * Math.PI * 2;
      this.swaySpeed = Math.random() * 0.02 + 0.01;
      this.type = Math.random() > 0.45 ? "blossom" : "petal";
      this.palette = flowerPalettes[Math.floor(Math.random() * flowerPalettes.length)];
      this.alpha = Math.random() * 0.45 + 0.35;
    };
    FloatingFlower.prototype.update = function () {
      this.swayPhase += this.swaySpeed;
      this.y += this.speedY;
      this.x += this.speedX + Math.sin(this.swayPhase) * 0.45;
      this.rotation += this.rotSpeed;
      if (this.y > ch + 35) this.reset(false);
      if (this.x > cw + 35) this.x = -25;
      if (this.x < -35) this.x = cw + 25;
    };
    FloatingFlower.prototype.draw = function () {
      ctx.save();
      ctx.translate(this.x, this.y);
      ctx.rotate(this.rotation);
      ctx.globalAlpha = this.alpha;
      if (this.type === "blossom") {
        const s = this.size;
        for (let i = 0; i < 5; i++) {
          ctx.save();
          ctx.rotate((i * Math.PI * 2) / 5);
          ctx.beginPath();
          ctx.moveTo(0, 0);
          ctx.bezierCurveTo(-s * 0.55, -s * 0.6, -s * 0.45, -s * 1.35, 0, -s * 1.15);
          ctx.bezierCurveTo(s * 0.45, -s * 1.35, s * 0.55, -s * 0.6, 0, 0);
          ctx.fillStyle = this.palette.fill;
          ctx.fill();
          ctx.lineWidth = 0.6;
          ctx.strokeStyle = this.palette.stroke;
          ctx.stroke();
          ctx.restore();
        }
        ctx.beginPath();
        ctx.arc(0, 0, s * 0.22, 0, Math.PI * 2);
        ctx.fillStyle = this.palette.center;
        ctx.fill();
      } else {
        const s = this.size * 1.1;
        ctx.beginPath();
        ctx.moveTo(0, -s);
        ctx.bezierCurveTo(s * 0.8, -s * 0.8, s * 0.7, s * 0.6, 0, s);
        ctx.bezierCurveTo(-s * 0.7, s * 0.6, -s * 0.8, -s * 0.8, 0, -s);
        ctx.fillStyle = this.palette.fill;
        ctx.fill();
        ctx.lineWidth = 0.6;
        ctx.strokeStyle = this.palette.stroke;
        ctx.stroke();
      }
      ctx.restore();
    };

    function GoldenButterfly() {
      this.reset(true);
    }
    GoldenButterfly.prototype.reset = function (initial) {
      this.x = Math.random() * cw;
      this.y = initial ? Math.random() * ch : ch + 40;
      this.size = Math.random() * 6 + 7;
      this.speedY = -(Math.random() * 0.55 + 0.35);
      this.speedX = (Math.random() - 0.5) * 0.6;
      this.wingPhase = Math.random() * Math.PI * 2;
      this.wingSpeed = Math.random() * 0.09 + 0.08;
      this.wanderPhase = Math.random() * Math.PI * 2;
      this.alpha = Math.random() * 0.4 + 0.45;
      this.tint = Math.random() > 0.4 ? "gold" : "blush";
    };
    GoldenButterfly.prototype.update = function () {
      this.wingPhase += this.wingSpeed;
      this.wanderPhase += 0.02;
      const vx = this.speedX + Math.sin(this.wanderPhase) * 0.65;
      const vy = this.speedY + Math.cos(this.wanderPhase * 0.7) * 0.2;
      this.x += vx;
      this.y += vy;
      this.angle = Math.atan2(vy, vx) + Math.PI / 2;
      if (this.y < -50) this.reset(false);
      if (this.x < -50) this.x = cw + 40;
      if (this.x > cw + 50) this.x = -40;
    };
    GoldenButterfly.prototype.draw = function () {
      ctx.save();
      ctx.translate(this.x, this.y);
      ctx.rotate(this.angle * 0.25);
      ctx.globalAlpha = this.alpha;
      const flap = Math.abs(Math.sin(this.wingPhase)) * 0.82 + 0.18;
      const s = this.size;
      const wingFill =
        this.tint === "gold" ? "rgba(223, 202, 151, 0.65)" : "rgba(255, 232, 236, 0.7)";
      const wingStroke =
        this.tint === "gold" ? "rgba(179, 143, 72, 0.75)" : "rgba(200, 168, 107, 0.65)";

      ctx.shadowBlur = 8;
      ctx.shadowColor = "rgba(200, 168, 107, 0.45)";

      [-1, 1].forEach(function (dir) {
        ctx.save();
        ctx.scale(dir * flap, 1);
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.bezierCurveTo(s * 1.4, -s * 1.3, s * 1.9, -s * 0.1, s * 0.3, s * 0.2);
        ctx.closePath();
        ctx.fillStyle = wingFill;
        ctx.fill();
        ctx.lineWidth = 0.8;
        ctx.strokeStyle = wingStroke;
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(0, s * 0.15);
        ctx.bezierCurveTo(s * 1.2, s * 0.2, s * 1.1, s * 1.3, s * 0.1, s * 0.85);
        ctx.closePath();
        ctx.fillStyle = wingFill;
        ctx.fill();
        ctx.stroke();
        ctx.restore();
      });

      ctx.beginPath();
      ctx.moveTo(0, -s * 0.45);
      ctx.lineTo(0, s * 0.55);
      ctx.strokeStyle = "#946E2E";
      ctx.lineWidth = 1.1;
      ctx.stroke();
      ctx.restore();
    };

    function TouchSparkle(x, y) {
      this.x = x;
      this.y = y;
      const angle = Math.random() * Math.PI * 2;
      const speed = Math.random() * 2.2 + 0.6;
      this.vx = Math.cos(angle) * speed;
      this.vy = Math.sin(angle) * speed - 0.5;
      this.size = Math.random() * 4.5 + 2.5;
      this.alpha = 0.9;
      this.decay = Math.random() * 0.018 + 0.014;
      this.rotation = Math.random() * Math.PI * 2;
      this.rotSpeed = (Math.random() - 0.5) * 0.08;
      this.isPetal = Math.random() > 0.45;
      this.color = goldPalette[Math.floor(Math.random() * goldPalette.length)];
    }
    TouchSparkle.prototype.update = function () {
      this.x += this.vx;
      this.y += this.vy;
      this.vy += 0.03;
      this.rotation += this.rotSpeed;
      this.alpha -= this.decay;
    };
    TouchSparkle.prototype.draw = function () {
      if (this.alpha <= 0) return;
      ctx.save();
      ctx.translate(this.x, this.y);
      ctx.rotate(this.rotation);
      ctx.globalAlpha = Math.max(0, this.alpha);
      if (this.isPetal) {
        const s = this.size;
        ctx.beginPath();
        ctx.moveTo(0, -s);
        ctx.bezierCurveTo(s * 0.7, -s * 0.6, s * 0.7, s * 0.6, 0, s);
        ctx.bezierCurveTo(-s * 0.7, s * 0.6, -s * 0.7, -s * 0.6, 0, -s);
        ctx.fillStyle = "rgba(255, 236, 240, 0.85)";
        ctx.fill();
        ctx.lineWidth = 0.6;
        ctx.strokeStyle = "#C8A86B";
        ctx.stroke();
      } else {
        ctx.beginPath();
        ctx.arc(0, 0, this.size * 0.45, 0, Math.PI * 2);
        ctx.fillStyle = this.color;
        ctx.shadowBlur = 6;
        ctx.shadowColor = "#C8A86B";
        ctx.fill();
      }
      ctx.restore();
    };

    const goldDust = Array.from({ length: 22 }, function () {
      return new GoldParticle();
    });
    const floatingFlowers = Array.from({ length: 16 }, function () {
      return new FloatingFlower();
    });
    const butterflies = Array.from({ length: 6 }, function () {
      return new GoldenButterfly();
    });
    const touchSparkles = [];

    window.addEventListener(
      "pointerdown",
      function (e) {
        for (let i = 0; i < 10; i++) {
          touchSparkles.push(new TouchSparkle(e.clientX, e.clientY));
        }
      },
      { passive: true }
    );

    function animateAmbient() {
      ctx.clearRect(0, 0, cw, ch);
      goldDust.forEach(function (p) {
        p.update();
        p.draw();
      });
      floatingFlowers.forEach(function (f) {
        f.update();
        f.draw();
      });
      butterflies.forEach(function (b) {
        b.update();
        b.draw();
      });
      for (let i = touchSparkles.length - 1; i >= 0; i--) {
        touchSparkles[i].update();
        touchSparkles[i].draw();
        if (touchSparkles[i].alpha <= 0) touchSparkles.splice(i, 1);
      }
      requestAnimationFrame(animateAmbient);
    }

    requestAnimationFrame(animateAmbient);
  }

  // ===========================================================================
  // 1B. GOLDEN PARTICLES & FIREFLIES ENGINE (Canvas 2D for Opening Stage)
  // ===========================================================================
  function initGoldenParticles() {
    const canvas = document.getElementById("gold-particles-canvas");
    if (!canvas || prefersReducedMotion) return;
    if (document.body.classList.contains("is-champagne-envelope-theme")) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    window.addEventListener("resize", function () {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    });

    const isMoonlit =
      document.body.classList.contains("template-moonlit_lake") ||
      document.body.classList.contains("template-starlight_lantern_glow");
    const count = width < 480 ? 45 : 70;
    const particles = [];
    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        r: isMoonlit ? Math.random() * 3.0 + 1.2 : Math.random() * 2.4 + 0.8,
        vx: (Math.random() - 0.5) * 0.55,
        vy: isMoonlit ? (Math.random() - 0.5) * 0.45 : -Math.random() * 0.65 - 0.2,
        alpha: Math.random() * 0.75 + 0.25,
        phase: Math.random() * Math.PI * 2,
      });
    }

    function renderFrame() {
      if (hasOpenedCard) return;
      ctx.clearRect(0, 0, width, height);

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.phase += 0.045 * particleBurstMultiplier;
        p.x += p.vx * particleBurstMultiplier + Math.sin(p.phase) * 0.35;
        p.y += p.vy * particleBurstMultiplier;

        if (p.y < -10) p.y = height + 10;
        if (p.y > height + 10) p.y = -10;
        if (p.x < -10) p.x = width + 10;
        if (p.x > width + 10) p.x = -10;

        const twinkle = (Math.sin(p.phase) + 1) * 0.5;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r * (0.85 + twinkle * 0.45), 0, Math.PI * 2);
        if (isMoonlit) {
          ctx.fillStyle = "rgba(250, 232, 130, " + (p.alpha * (0.4 + twinkle * 0.6)).toFixed(2) + ")";
          ctx.shadowBlur = 12;
          ctx.shadowColor = "rgba(243, 211, 130, 0.95)";
        } else {
          ctx.fillStyle = "rgba(232, 193, 102, " + (p.alpha * (0.5 + twinkle * 0.5)).toFixed(2) + ")";
          ctx.shadowBlur = 8;
          ctx.shadowColor = "rgba(212, 175, 55, 0.8)";
        }
        ctx.fill();
      }
      requestAnimationFrame(renderFrame);
    }

    requestAnimationFrame(renderFrame);
  }

  // ===========================================================================
  // 2A. INTERACTIVE 24K GOLD FOIL SCRATCH-OFF CARD (`golden_scratch_reveal`)
  // ===========================================================================
  function initGoldenScratchCard() {
    const canvas = document.getElementById("scratch-foil-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rect = canvas.parentElement.getBoundingClientRect();
    const w = (canvas.width = Math.max(300, Math.floor(rect.width || 340)));
    const h = (canvas.height = Math.max(380, Math.floor(rect.height || 420)));

    const grad = ctx.createLinearGradient(0, 0, w, h);
    grad.addColorStop(0, "#F6E299");
    grad.addColorStop(0.28, "#D4AF37");
    grad.addColorStop(0.52, "#FFF5CC");
    grad.addColorStop(0.76, "#B68624");
    grad.addColorStop(1, "#E5C168");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);

    ctx.strokeStyle = "rgba(92, 62, 12, 0.55)";
    ctx.lineWidth = 2;
    ctx.strokeRect(16, 16, w - 32, h - 32);

    ctx.fillStyle = "#3B280A";
    ctx.textAlign = "center";
    ctx.font = "bold 42px serif";
    ctx.fillText("🪙", w / 2, h * 0.34);

    const badiniPrompt = canvas.getAttribute("data-prompt-badini") || "کلیل بکە بو ڤەکرنا داخوازنامێ";
    ctx.font = "bold 20px 'Vazirmatn', 'Noto Naskh Arabic', serif";
    ctx.fillText(badiniPrompt, w / 2, h * 0.52);

    const subHint = canvas.getAttribute("data-instruction") || "";
    ctx.font = "600 13px 'Vazirmatn', sans-serif";
    ctx.fillStyle = "#5A3F14";
    ctx.fillText(subHint.slice(0, 42), w / 2, h * 0.64);

    let isDrawing = false;
    let strokeCounter = 0;

    function scratchAt(x, y) {
      ctx.globalCompositeOperation = "destination-out";
      ctx.beginPath();
      ctx.arc(x, y, 30, 0, Math.PI * 2);
      ctx.fill();

      strokeCounter++;
      if (strokeCounter % 5 === 0) {
        checkScratchProgress();
      }
    }

    function checkScratchProgress() {
      try {
        const imgData = ctx.getImageData(0, 0, w, h).data;
        let transparentPixels = 0;
        const totalSampled = imgData.length / (4 * 16);
        for (let i = 3; i < imgData.length; i += 4 * 16) {
          if (imgData[i] < 128) transparentPixels++;
        }
        const pct = Math.min(100, Math.round((transparentPixels / totalSampled) * 100 * 1.9));
        const fillEl = document.getElementById("scratch-progress-fill");
        if (fillEl) fillEl.style.width = pct + "%";

        if (pct >= 62 && !isOpeningInProgress) {
          canvas.classList.add("foil-cleared");
          window.triggerInvitationOpening();
        }
      } catch (e) {}
    }

    function getCoords(ev) {
      const b = canvas.getBoundingClientRect();
      const clientX = ev.touches && ev.touches[0] ? ev.touches[0].clientX : ev.clientX;
      const clientY = ev.touches && ev.touches[0] ? ev.touches[0].clientY : ev.clientY;
      return {
        x: ((clientX - b.left) / b.width) * w,
        y: ((clientY - b.top) / b.height) * h,
      };
    }

    canvas.addEventListener("mousedown", function (ev) {
      isDrawing = true;
      const pt = getCoords(ev);
      scratchAt(pt.x, pt.y);
    });
    window.addEventListener("mousemove", function (ev) {
      if (!isDrawing) return;
      const pt = getCoords(ev);
      scratchAt(pt.x, pt.y);
    });
    window.addEventListener("mouseup", function () {
      isDrawing = false;
    });

    canvas.addEventListener(
      "touchstart",
      function (ev) {
        isDrawing = true;
        const pt = getCoords(ev);
        scratchAt(pt.x, pt.y);
      },
      { passive: true }
    );
    canvas.addEventListener(
      "touchmove",
      function (ev) {
        if (!isDrawing) return;
        const pt = getCoords(ev);
        scratchAt(pt.x, pt.y);
      },
      { passive: true }
    );
    canvas.addEventListener("touchend", function () {
      isDrawing = false;
    });
  }

  // ===========================================================================
  // 2B. INTERACTIVE TAP-TO-GLOW SKY LANTERNS (`starlight_lantern_glow`)
  // ===========================================================================
  let litLanternsCount = 0;

  window.igniteSkyLantern = function (btnEl) {
    if (!btnEl || btnEl.classList.contains("is-lit")) return;
    btnEl.classList.add("is-lit");
    litLanternsCount++;

    const pill = document.getElementById("lantern-counter-pill");
    if (pill) {
      pill.textContent = "🏮 " + litLanternsCount + " / 3";
    }

    if (litLanternsCount >= 3) {
      setTimeout(function () {
        window.triggerInvitationOpening();
      }, 450);
    }
  };

  window.igniteAllLanternsAndOpen = function () {
    const allLanterns = document.querySelectorAll(".sky-lantern-item");
    allLanterns.forEach(function (el) {
      el.classList.add("is-lit");
    });
    const pill = document.getElementById("lantern-counter-pill");
    if (pill) pill.textContent = "🏮 3 / 3";
    setTimeout(function () {
      window.triggerInvitationOpening();
    }, 350);
  };

  // ===========================================================================
  // 2C. MULTI-EXPERIENCE OPENING ANIMATION CONTROLLER
  // ===========================================================================
  window.triggerInvitationOpening = function () {
    if (isOpeningInProgress || hasOpenedCard) return;
    isOpeningInProgress = true;

    const stage = document.getElementById("opening-stage");
    const mainContent = document.getElementById("invitation-main");
    const floatingControls = document.getElementById("floating-controls");

    startMusicAfterInteraction();
    startVerticalHeroVideoIfPresent();

    if (prefersReducedMotion || !stage) {
      completeOpeningReveal(stage, mainContent, floatingControls);
      return;
    }

    particleBurstMultiplier = 3.4;

    const champagneScene = document.getElementById("scene-champagne-envelope");
    if (champagneScene) {
      champagneScene.classList.add("step-activating");
      setTimeout(function () {
        completeOpeningReveal(stage, mainContent, floatingControls);
      }, 950);
      return;
    }

    const bespokeScene = stage.querySelector(".bespoke-stage");
    if (bespokeScene) {
      bespokeScene.classList.add("step-activating");
      setTimeout(function () {
        stage.classList.add("bloom-active");
      }, 1150);
      setTimeout(function () {
        completeOpeningReveal(stage, mainContent, floatingControls);
      }, 1950);
      return;
    }

    const cameraRig = document.getElementById("camera-rig");
    const card = document.getElementById("luxury-card-3d");
    const butterfly = document.getElementById("butterfly-3d-actor");

    if (!card || !butterfly) {
      completeOpeningReveal(stage, mainContent, floatingControls);
      return;
    }

    card.classList.add("step-floating");
    butterfly.classList.add("wings-active");

    setTimeout(function () {
      card.classList.add("step-unfolding");
    }, 380);

    setTimeout(function () {
      butterfly.classList.add("step-lift");
    }, 1050);

    setTimeout(function () {
      butterfly.classList.add("step-toward-camera");
      if (cameraRig) cameraRig.classList.add("camera-follow-butterfly");
    }, 1600);

    setTimeout(function () {
      butterfly.classList.add("step-fly-away");
      if (cameraRig) cameraRig.classList.add("camera-reveal-zoom");
      stage.classList.add("bloom-active");
    }, 2200);

    setTimeout(function () {
      completeOpeningReveal(stage, mainContent, floatingControls);
    }, 2900);
  };

  function startVerticalHeroVideoIfPresent() {
    const v = document.getElementById("hero-vertical-video-player");
    if (v && typeof v.play === "function") {
      v.play().catch(function () {});
    }
  }

  function completeOpeningReveal(stage, mainContent, floatingControls) {
    hasOpenedCard = true;
    document.body.classList.remove("is-locked");
    if (stage) stage.classList.add("stage-completed");
    if (mainContent) mainContent.classList.remove("content-pre-open");
    if (floatingControls) floatingControls.classList.remove("controls-hidden");
    startVerticalHeroVideoIfPresent();
  }

  // ===========================================================================
  // 3. DUAL WEDDING MUSIC CONTROLLER (UPLOADED MP3/WAV OR YOUTUBE)
  // ===========================================================================
  const MUSIC_STORAGE_KEY = "bikozava_music_muted";

  function updateMusicButtonUI(isMuted) {
    const btn = document.getElementById("music-toggle-btn");
    const statusText = document.getElementById("music-status-text");
    if (!btn) return;
    if (isMuted) {
      btn.classList.add("is-muted");
      if (statusText) statusText.textContent = btn.getAttribute("data-label-muted") || "Muted";
    } else {
      btn.classList.remove("is-muted");
      if (statusText) statusText.textContent = btn.getAttribute("data-label-playing") || "Playing";
    }
  }

  function initYouTubePlayerIfNeeded() {
    const btn = document.getElementById("music-toggle-btn");
    if (!btn) return;
    const sourceType = btn.getAttribute("data-music-source");
    const videoId = btn.getAttribute("data-youtube-id");
    if (sourceType !== "youtube" || !videoId) return;

    window.onYouTubeIframeAPIReady = function () {
      ytPlayer = new window.YT.Player("youtube-audio-player", {
        height: "1",
        width: "1",
        videoId: videoId,
        playerVars: {
          autoplay: 0,
          controls: 0,
          loop: 1,
          playlist: videoId,
          playsinline: 1,
          rel: 0,
        },
        events: {
          onReady: function () {
            ytReady = true;
            ytPlayer.setVolume(75);
            if (ytPendingPlay) {
              ytPendingPlay = false;
              ytPlayer.unMute();
              ytPlayer.playVideo();
              updateMusicButtonUI(false);
            }
          },
        },
      });
    };

    const tag = document.createElement("script");
    tag.src = "https://www.youtube.com/iframe_api";
    document.head.appendChild(tag);
  }

  function startMusicAfterInteraction() {
    const btn = document.getElementById("music-toggle-btn");
    if (!btn) return;

    const savedMuted = sessionStorage.getItem(MUSIC_STORAGE_KEY) === "1";
    const shouldAutoplay = btn.getAttribute("data-autoplay-after-open") === "1";
    const sourceType = btn.getAttribute("data-music-source");

    if (savedMuted || !shouldAutoplay) {
      updateMusicButtonUI(true);
      return;
    }

    if (sourceType === "youtube") {
      if (ytReady && ytPlayer && typeof ytPlayer.playVideo === "function") {
        ytPlayer.unMute();
        ytPlayer.playVideo();
        updateMusicButtonUI(false);
      } else {
        ytPendingPlay = true;
        updateMusicButtonUI(false);
      }
      return;
    }

    const audio = document.getElementById("wedding-audio");
    if (!audio) return;

    audio.muted = false;
    audio.volume = 0.75;
    const playPromise = audio.play();
    if (playPromise && typeof playPromise.then === "function") {
      playPromise
        .then(function () {
          updateMusicButtonUI(false);
        })
        .catch(function () {
          updateMusicButtonUI(true);
        });
    }
  }

  window.toggleWeddingMusic = function () {
    const btn = document.getElementById("music-toggle-btn");
    if (!btn) return;
    const sourceType = btn.getAttribute("data-music-source");
    const isCurrentlyMuted = btn.classList.contains("is-muted");

    if (sourceType === "youtube") {
      if (!ytReady || !ytPlayer) return;
      if (isCurrentlyMuted) {
        ytPlayer.unMute();
        ytPlayer.playVideo();
        sessionStorage.setItem(MUSIC_STORAGE_KEY, "0");
        updateMusicButtonUI(false);
      } else {
        ytPlayer.mute();
        ytPlayer.pauseVideo();
        sessionStorage.setItem(MUSIC_STORAGE_KEY, "1");
        updateMusicButtonUI(true);
      }
      return;
    }

    const audio = document.getElementById("wedding-audio");
    if (!audio) return;

    if (audio.paused || audio.muted) {
      audio.muted = false;
      audio.play().catch(function () {});
      sessionStorage.setItem(MUSIC_STORAGE_KEY, "0");
      updateMusicButtonUI(false);
    } else {
      audio.muted = true;
      audio.pause();
      sessionStorage.setItem(MUSIC_STORAGE_KEY, "1");
      updateMusicButtonUI(true);
    }
  };

  // ===========================================================================
  // 4. LIVE WEDDING COUNTDOWN TIMER
  // ===========================================================================
  function initCountdown() {
    const el = document.getElementById("live-countdown");
    if (!el) return;

    const dateStr = el.getAttribute("data-wedding-date") || "2026-11-21";
    const timeStr = el.getAttribute("data-wedding-time") || "19:00";
    const targetIso = dateStr.slice(0, 10) + "T" + (timeStr.length === 5 ? timeStr : "19:00") + ":00";
    const targetTime = new Date(targetIso).getTime();

    const daysEl = document.getElementById("cd-days");
    const hoursEl = document.getElementById("cd-hours");
    const minsEl = document.getElementById("cd-minutes");
    const secsEl = document.getElementById("cd-seconds");

    function tick() {
      const now = Date.now();
      const diff = Math.max(0, targetTime - now);

      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
      const mins = Math.floor((diff / (1000 * 60)) % 60);
      const secs = Math.floor((diff / 1000) % 60);

      if (daysEl) daysEl.textContent = String(days).padStart(2, "0");
      if (hoursEl) hoursEl.textContent = String(hours).padStart(2, "0");
      if (minsEl) minsEl.textContent = String(mins).padStart(2, "0");
      if (secsEl) secsEl.textContent = String(secs).padStart(2, "0");
    }

    tick();
    setInterval(tick, 1000);
  }

  // ===========================================================================
  // 5. GALLERY LIGHTBOX & ASYNC RSVP SUBMISSION
  // ===========================================================================
  window.openGalleryLightbox = function (src, caption) {
    const box = document.getElementById("gallery-lightbox");
    const img = document.getElementById("lightbox-img");
    const cap = document.getElementById("lightbox-caption");
    if (!box || !img) return;
    img.src = src;
    if (cap) cap.textContent = caption || "";
    box.classList.add("open");
  };

  window.closeGalleryLightbox = function () {
    const box = document.getElementById("gallery-lightbox");
    if (box) box.classList.remove("open");
  };

  window.submitGuestRsvp = function (ev) {
    ev.preventDefault();
    const form = ev.target;
    const feedback = document.getElementById("rsvp-feedback");
    const payload = {
      csrf_token: form.querySelector('[name="csrf_token"]').value,
      language: form.querySelector('[name="language"]').value,
      guest_name: form.querySelector('[name="guest_name"]').value,
      guest_phone: form.querySelector('[name="guest_phone"]').value,
      guests_count: form.querySelector('[name="guests_count"]').value,
      attending: form.querySelector('[name="attending"]').value,
      message: form.querySelector('[name="message"]').value,
    };

    fetch(form.action, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": payload.csrf_token,
      },
      body: JSON.stringify(payload),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (data && data.ok) {
          if (feedback) {
            feedback.className = "rsvp-feedback success";
            feedback.textContent = "✦ " + data.message;
          }
          form.reset();
        } else if (feedback) {
          feedback.className = "rsvp-feedback";
          feedback.textContent = (data && data.error) || "Error submitting RSVP.";
        }
      })
      .catch(function () {
        form.submit();
      });

    return false;
  };

  // ===========================================================================
  // 6. LIVE DARK / LIGHT MODE TOGGLE (`toggleInvitationDarkMode`)
  // ===========================================================================
  const THEME_MODE_KEY = "bikozava_theme_mode";

  function applySavedThemeMode() {
    const saved = sessionStorage.getItem(THEME_MODE_KEY);
    const iconEl = document.getElementById("theme-mode-icon");
    if (saved === "dark") {
      document.body.classList.add("is-dark-mode");
      if (iconEl) iconEl.textContent = "☀️";
    } else if (saved === "light") {
      document.body.classList.remove("is-dark-mode");
      if (iconEl) iconEl.textContent = "🌙";
    }
  }

  window.toggleInvitationDarkMode = function () {
    const isNowDark = document.body.classList.toggle("is-dark-mode");
    sessionStorage.setItem(THEME_MODE_KEY, isNowDark ? "dark" : "light");
    const iconEl = document.getElementById("theme-mode-icon");
    if (iconEl) {
      iconEl.textContent = isNowDark ? "☀️" : "🌙";
    }
  };

  document.addEventListener("DOMContentLoaded", function () {
    applySavedThemeMode();
    initChampagneFloralCanvas();
    initGoldenParticles();
    initGoldenScratchCard();
    initCountdown();
    initYouTubePlayerIfNeeded();

    if (window.location.search.indexOf("lang=") !== -1 && sessionStorage.getItem("bikozava_card_opened") === "1") {
      const stage = document.getElementById("opening-stage");
      const mainContent = document.getElementById("invitation-main");
      const floatingControls = document.getElementById("floating-controls");
      completeOpeningReveal(stage, mainContent, floatingControls);
    }

    const origTrigger = window.triggerInvitationOpening;
    window.triggerInvitationOpening = function () {
      sessionStorage.setItem("bikozava_card_opened", "1");
      origTrigger();
    };
  });
})();
