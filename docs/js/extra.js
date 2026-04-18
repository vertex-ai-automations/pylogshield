/**
 * PyLogShield Documentation — Terminal Noir Theme
 * Interactive enhancements
 */

(function () {
  "use strict";

  /* ── Wait for MkDocs Material to finish rendering ── */
  function onReady(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  /* ── Re-init on Material instant navigation ── */
  function onPageChange(fn) {
    fn();
    document.addEventListener("DOMContentLoaded", fn);

    // Material uses a custom event after SPA navigation
    document$.subscribe(fn);
  }

  /* ============================================================
     1. SCROLL REVEAL — feature cards fade up on enter
     ============================================================ */
  function initScrollReveal() {
    const cards = document.querySelectorAll(".feature-item");
    if (!cards.length) return;

    // Add reveal class
    cards.forEach(function (card, i) {
      card.classList.add("pls-reveal");
      card.style.transitionDelay = (i % 3) * 80 + "ms";
    });

    if (!("IntersectionObserver" in window)) {
      // Fallback: show all immediately
      cards.forEach(function (c) { c.classList.add("pls-visible"); });
      return;
    }

    const observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("pls-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
    );

    cards.forEach(function (card) { observer.observe(card); });
  }

  /* ============================================================
     2. TERMINAL TYPING ANIMATION
        Replays the typed lines in .pls-terminal__body if present
     ============================================================ */
  function initTerminalAnimation() {
    var terminal = document.querySelector(".pls-terminal__body");
    if (!terminal) return;

    var lines = Array.from(terminal.querySelectorAll(".pls-terminal__line"));
    if (!lines.length) return;

    // Hide all lines, then reveal with staggered delay
    lines.forEach(function (line) {
      line.style.opacity = "0";
      line.style.transform = "translateX(-4px)";
      line.style.transition = "opacity 0.3s ease, transform 0.3s ease";
    });

    var delay = 200;
    lines.forEach(function (line, i) {
      var isBlank = line.classList.contains("pls-terminal__line--blank");
      setTimeout(function () {
        line.style.opacity = "1";
        line.style.transform = "translateX(0)";
      }, delay);
      delay += isBlank ? 80 : 180;
    });
  }

  /* ============================================================
     3. HEADER MOUSE-PARALLAX GLOW
        Subtle glow follows cursor in the header
     ============================================================ */
  function initHeaderGlow() {
    var header = document.querySelector(".md-header");
    if (!header) return;

    var glowEl = document.createElement("div");
    glowEl.style.cssText = [
      "position:absolute",
      "top:0", "left:0", "right:0", "bottom:0",
      "pointer-events:none",
      "z-index:0",
      "opacity:0",
      "transition:opacity 0.4s",
      "background:radial-gradient(300px circle at 50% 50%, rgba(0,229,160,0.06), transparent 70%)",
    ].join(";");

    header.style.overflow = "hidden";
    header.appendChild(glowEl);

    header.addEventListener("mousemove", function (e) {
      var rect = header.getBoundingClientRect();
      var x = e.clientX - rect.left;
      var y = e.clientY - rect.top;
      glowEl.style.opacity = "1";
      glowEl.style.background =
        "radial-gradient(300px circle at " + x + "px " + y + "px, rgba(0,229,160,0.08), transparent 70%)";
    });

    header.addEventListener("mouseleave", function () {
      glowEl.style.opacity = "0";
    });
  }

  /* ============================================================
     4. ACTIVE NAV HIGHLIGHT PULSE
        One-shot glow on the active nav item
     ============================================================ */
  function initNavActivePulse() {
    var active = document.querySelector(
      ".md-nav__item--active > .md-nav__link"
    );
    if (!active) return;

    active.animate(
      [
        { textShadow: "none" },
        { textShadow: "0 0 10px rgba(0,229,160,0.5)" },
        { textShadow: "none" },
      ],
      { duration: 1200, easing: "ease-in-out" }
    );
  }

  /* ============================================================
     5. CODE BLOCK LANGUAGE BADGE
        Adds a subtle lang label to code blocks that have one
     ============================================================ */
  function initCodeBadges() {
    document.querySelectorAll(".highlight").forEach(function (block) {
      // Material injects class like language-python on the code element
      var code = block.querySelector("code[class*='language-']");
      if (!code) return;

      var match = code.className.match(/language-([a-zA-Z0-9_+-]+)/);
      if (!match) return;

      var lang = match[1].toLowerCase();
      if (lang === "text" || lang === "plain") return;

      // Don't double-add
      if (block.querySelector(".pls-lang-badge")) return;

      var badge = document.createElement("span");
      badge.className = "pls-lang-badge";
      badge.textContent = lang;
      badge.style.cssText = [
        "position:absolute",
        "top:8px", "right:40px",
        "font-family:var(--pls-heading-font,monospace)",
        "font-size:0.6rem",
        "letter-spacing:0.06em",
        "text-transform:uppercase",
        "color:var(--pls-green,#00e5a0)",
        "opacity:0.45",
        "pointer-events:none",
        "z-index:2",
      ].join(";");

      block.style.position = "relative";
      block.appendChild(badge);
    });
  }

  /* ============================================================
     INIT
     ============================================================ */
  onReady(function () {
    initScrollReveal();
    initTerminalAnimation();
    initHeaderGlow();
    initNavActivePulse();
    initCodeBadges();
  });

  // Re-run lightweight inits after SPA navigation (Material instant)
  try {
    document$.subscribe(function () {
      initScrollReveal();
      initTerminalAnimation();
      initNavActivePulse();
      initCodeBadges();
    });
  } catch (e) {
    // document$ not available (non-Material build), ignore
  }
})();
