(function () {
  "use strict";

  var STORAGE_COLLAPSED = "granago_sidebar_collapsed";
  var MQ = "(min-width: 768px)";

  function isDesktop() {
    return window.matchMedia(MQ).matches;
  }

  function setHtmlClass(cls, on) {
    var root = document.documentElement;
    if (on) {
      root.classList.add(cls);
    } else {
      root.classList.remove(cls);
    }
  }

  function setOpen(open) {
    setHtmlClass("sidebar-open", open);
    var openBtn = document.getElementById("openSideBar");
    if (openBtn) {
      openBtn.setAttribute("aria-expanded", open ? "true" : "false");
    }
    var overlay = document.getElementById("sidebarOverlay");
    if (overlay) {
      overlay.setAttribute("aria-hidden", open ? "false" : "true");
    }
  }

  function isCollapsedState(sidebar) {
    if (!sidebar) {
      return false;
    }
    return (
      sidebar.classList.contains("collapsed") ||
      document.documentElement.classList.contains("sidebar-collapsed")
    );
  }

  function persistCollapsed(collapsed) {
    try {
      localStorage.setItem(STORAGE_COLLAPSED, collapsed ? "1" : "0");
    } catch (e) {
      /* ignore */
    }
  }

  function setCollapsed(sidebar, collapsed, collapseBtn) {
    if (!sidebar) {
      return;
    }
    if (collapsed) {
      sidebar.classList.add("collapsed");
      document.documentElement.classList.add("sidebar-collapsed");
    } else {
      sidebar.classList.remove("collapsed");
      document.documentElement.classList.remove("sidebar-collapsed");
    }
    if (collapseBtn) {
      collapseBtn.setAttribute("aria-pressed", collapsed ? "true" : "false");
      var expandLabel = collapseBtn.getAttribute("data-label-expand") || "Expandir menu";
      var collapseLabel = collapseBtn.getAttribute("data-label-collapse") || "Recolher menu";
      collapseBtn.setAttribute("title", collapsed ? expandLabel : collapseLabel);
    }
  }

  function readStoredCollapsed() {
    try {
      return localStorage.getItem(STORAGE_COLLAPSED) === "1";
    } catch (e) {
      return false;
    }
  }

  function applyStoredCollapsed(sidebar, collapseBtn) {
    if (!sidebar) {
      return;
    }
    if (!isDesktop()) {
      // Mobile: drawer fechado; não sobrescreve preferência desktop no localStorage.
      sidebar.classList.remove("collapsed");
      document.documentElement.classList.remove("sidebar-collapsed");
      return;
    }
    setCollapsed(sidebar, readStoredCollapsed(), collapseBtn);
  }

  function markReady() {
    // Após o layout estável, habilita transitions (só para interação do usuário).
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        document.documentElement.classList.add("sidebar-ready");
      });
    });
  }

  function markActiveNavLinks() {
    var path = window.location.pathname;
    var links = document.querySelectorAll(".js-sidebar-nav");
    links.forEach(function (a) {
      var href = a.getAttribute("href");
      if (!href || href.charAt(0) === "#") {
        return;
      }
      try {
        var u = new URL(href, window.location.origin);
        var p = u.pathname;
        var isMatch =
          path === p ||
          (p.length > 1 && p.endsWith("/") && path.startsWith(p)) ||
          (p.length > 1 && !p.endsWith("/") && (path === p || path.startsWith(p + "/")));
        if (isMatch) {
          a.classList.add("is-active");
          a.setAttribute("aria-current", "page");
        }
      } catch (e) {
        /* ignore */
      }
    });
  }

  function closeMobileIfNeeded() {
    if (!isDesktop()) {
      setOpen(false);
    }
  }

  function initAppHeaderScroll() {
    var header = document.getElementById("appHeader");
    if (!header) {
      return;
    }
    var threshold = 10;
    var ticking = false;

    function sync() {
      ticking = false;
      if (window.scrollY > threshold) {
        header.classList.add("scrolled");
      } else {
        header.classList.remove("scrolled");
      }
    }

    function onScroll() {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(sync);
      }
    }

    window.addEventListener("scroll", onScroll, { passive: true });
    sync();
  }

  function initSidebar() {
    var sidebar = document.getElementById("sidebar");
    var overlay = document.getElementById("sidebarOverlay");
    var openBtn = document.getElementById("openSideBar");
    var closeMobile = document.getElementById("sidebarCloseMobile");
    var collapseBtn = document.getElementById("sidebarDesktopCollapse");

    if (!sidebar) {
      return;
    }

    markActiveNavLinks();
    applyStoredCollapsed(sidebar, collapseBtn);
    markReady();

    if (openBtn) {
      openBtn.addEventListener("click", function () {
        var next = !document.documentElement.classList.contains("sidebar-open");
        setOpen(next);
      });
    }

    if (closeMobile) {
      closeMobile.addEventListener("click", function () {
        setOpen(false);
      });
    }

    if (overlay) {
      overlay.addEventListener("click", function () {
        setOpen(false);
      });
    }

    document.querySelectorAll(".js-sidebar-nav, .js-sidebar-tutoriais").forEach(function (link) {
      link.addEventListener("click", function () {
        closeMobileIfNeeded();
      });
    });

    var sidebarAdicionar = document.getElementById("sidebar-btn-adicionar");
    if (sidebarAdicionar) {
      sidebarAdicionar.addEventListener("click", closeMobileIfNeeded);
    }

    if (collapseBtn) {
      collapseBtn.addEventListener("click", function () {
        if (!isDesktop()) {
          return;
        }
        var next = !isCollapsedState(sidebar);
        setCollapsed(sidebar, next, collapseBtn);
        persistCollapsed(next);
      });
    }

    window.matchMedia(MQ).addEventListener("change", function (e) {
      if (e.matches) {
        setOpen(false);
        applyStoredCollapsed(sidebar, collapseBtn);
      } else {
        // Só ajusta visual no mobile — não grava no localStorage.
        sidebar.classList.remove("collapsed");
        document.documentElement.classList.remove("sidebar-collapsed");
      }
    });

    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && document.documentElement.classList.contains("sidebar-open")) {
        setOpen(false);
      }
    });
  }

  function boot() {
    initSidebar();
    initAppHeaderScroll();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
