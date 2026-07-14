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
      { root: null, rootMargin: "0px 0px -6% 0px", threshold: 0.06 }
    );

    items.forEach(function (el) {
      observer.observe(el);
    });
  }

  function initHeader() {
    var header = document.getElementById("lp-header");
    if (!header) return;

    function updateHeader() {
      header.classList.toggle("is-scrolled", window.scrollY > 24);
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

  function init() {
    initReveal();
    initHeader();
    initFaq();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
