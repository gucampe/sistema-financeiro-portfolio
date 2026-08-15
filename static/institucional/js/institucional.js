(function () {
  "use strict";

  function initMobileNav() {
    var header = document.getElementById("lp-header");
    var button = document.getElementById("inst-menu-btn");
    var panel = document.getElementById("inst-mobile-nav");
    if (!header || !button || !panel) return;

    function setOpen(open) {
      button.setAttribute("aria-expanded", open ? "true" : "false");
      button.setAttribute("aria-label", open ? "Fechar menu" : "Abrir menu");
      panel.classList.toggle("is-open", open);
      if (open) {
        panel.removeAttribute("hidden");
      } else {
        panel.setAttribute("hidden", "");
      }
    }

    button.addEventListener("click", function () {
      setOpen(button.getAttribute("aria-expanded") !== "true");
    });

    panel.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        setOpen(false);
      });
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") setOpen(false);
    });

    document.addEventListener("click", function (event) {
      if (!header.contains(event.target)) setOpen(false);
    });

    if (typeof window.matchMedia === "function") {
      var mq = window.matchMedia("(min-width: 1024px)");
      function onChange() {
        if (mq.matches) setOpen(false);
      }
      if (typeof mq.addEventListener === "function") {
        mq.addEventListener("change", onChange);
      } else if (typeof mq.addListener === "function") {
        mq.addListener(onChange);
      }
    }
  }

  function init() {
    initMobileNav();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
