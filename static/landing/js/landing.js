(function () {
  "use strict";

  var prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function initReveal() {
    var items = document.querySelectorAll(".lp-reveal");
    if (!items.length) return;

    if (prefersReducedMotion || typeof IntersectionObserver === "undefined") {
      items.forEach(function (el) {
        el.classList.add("is-visible");
      });
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      { root: null, rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
    );

    items.forEach(function (el, index) {
      var hasPainStagger =
        el.classList.contains("lp-pain--1") ||
        el.classList.contains("lp-pain--2") ||
        el.classList.contains("lp-pain--3");
      if (
        !hasPainStagger &&
        !el.classList.contains("lp-reveal--delay") &&
        !el.classList.contains("lp-reveal--delay-2")
      ) {
        el.style.transitionDelay = Math.min(index * 0.04, 0.2) + "s";
      }
      observer.observe(el);
    });
  }

  function initHeader() {
    var header = document.getElementById("lp-header");
    if (!header) return;

    function updateHeader() {
      header.classList.toggle("is-scrolled", window.scrollY > 16);
    }

    updateHeader();
    window.addEventListener("scroll", updateHeader, { passive: true });
  }

  function initFaq() {
    var items = document.querySelectorAll(".lp-faq");
    if (!items.length) return;

    items.forEach(function (details) {
      details.addEventListener("toggle", function () {
        if (!details.open) return;
        items.forEach(function (other) {
          if (other !== details) other.open = false;
        });
      });
    });
  }

  function initLegalToc() {
    var details = document.querySelector(".lp-legal-toc__details");
    if (!details || typeof window.matchMedia !== "function") return;

    var mq = window.matchMedia("(min-width: 1024px)");

    function syncOpenState() {
      details.open = mq.matches;
    }

    syncOpenState();

    if (typeof mq.addEventListener === "function") {
      mq.addEventListener("change", syncOpenState);
    } else if (typeof mq.addListener === "function") {
      mq.addListener(syncOpenState);
    }
  }

  function formatWhatsapp(value) {
    var digits = String(value || "").replace(/\D/g, "").slice(0, 11);
    if (!digits.length) return "";
    if (digits.length <= 2) return "(" + digits;
    if (digits.length <= 7) return "(" + digits.slice(0, 2) + ") " + digits.slice(2);
    return "(" + digits.slice(0, 2) + ") " + digits.slice(2, 7) + "-" + digits.slice(7);
  }

  function initCapturaForm() {
    var form = document.getElementById("form-captura");
    if (!form) return;

    var whatsapp = form.querySelector("#id_whatsapp");
    if (whatsapp) {
      whatsapp.addEventListener("input", function () {
        var start = whatsapp.selectionStart;
        var before = whatsapp.value.length;
        whatsapp.value = formatWhatsapp(whatsapp.value);
        var after = whatsapp.value.length;
        if (typeof start === "number") {
          var next = Math.max(0, start + (after - before));
          whatsapp.setSelectionRange(next, next);
        }
      });
    }

    form.addEventListener("submit", function () {
      var btn = form.querySelector("[data-captura-submit]");
      if (!btn || btn.disabled) return;
      btn.disabled = true;
      btn.setAttribute("aria-busy", "true");
      btn.textContent = "Enviando…";
    });
  }

  function initCapturaModal() {
    var overlay = document.getElementById("modal-captura");
    var openButtons = document.querySelectorAll("[data-open-captura]");

    openButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (!overlay || !globalThis.GranaGoModal) {
          window.location.href = btn.getAttribute("data-captura-fallback") || "/#garantir-vaga";
          return;
        }
        GranaGoModal.open(overlay, { trigger: btn });
        var first = overlay.querySelector("#id_nome");
        if (first) {
          window.setTimeout(function () {
            first.focus();
          }, 50);
        }
      });
    });

    if (!overlay || !globalThis.GranaGoModal) return;

    GranaGoModal.bind(overlay);

    if (overlay.getAttribute("data-captura-open-on-load") === "1") {
      GranaGoModal.open(overlay);
    }
  }

  function initHeroPerson() {
    var visual = document.querySelector("[data-hero-visual]");
    var img = document.querySelector("[data-hero-person]");
    if (!visual || !img) return;

    function markReady() {
      img.classList.remove("is-missing");
      // rAF: garante que o estado inicial opacity:0 foi pintado antes do crossfade
      window.requestAnimationFrame(function () {
        window.requestAnimationFrame(function () {
          visual.classList.add("is-ready");
        });
      });
    }

    function markMissing() {
      img.classList.add("is-missing");
      visual.classList.remove("is-ready");
      img.setAttribute("aria-hidden", "true");
      img.alt = "";
    }

    img.addEventListener("load", markReady);
    img.addEventListener("error", markMissing);

    if (img.complete) {
      if (img.naturalWidth > 0) markReady();
      else markMissing();
    }
  }

  function init() {
    initReveal();
    initHeader();
    initFaq();
    initLegalToc();
    initCapturaModal();
    initCapturaForm();
    initHeroPerson();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
