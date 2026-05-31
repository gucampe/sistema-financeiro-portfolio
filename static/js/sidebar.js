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
      sidebar.classList.contains("collapsed") || document.body.classList.contains("sidebar-init-collapsed")
    );
  }

  function syncCollapseUi(sidebar, collapseBtn) {
    if (!collapseBtn || !sidebar) {
      return;
    }
    var collapsed = isCollapsedState(sidebar);
    collapseBtn.setAttribute("aria-pressed", collapsed ? "true" : "false");
    var expandLabel = collapseBtn.getAttribute("data-label-expand") || "Expandir menu";
    var collapseLabel = collapseBtn.getAttribute("data-label-collapse") || "Recolher menu";
    collapseBtn.setAttribute("title", collapsed ? expandLabel : collapseLabel);
    try {
      localStorage.setItem(STORAGE_COLLAPSED, collapsed ? "1" : "0");
    } catch (e) {
      /* ignore */
    }
  }

  function applyStoredCollapsed(sidebar, collapseBtn) {
    if (!sidebar || !isDesktop()) {
      document.body.classList.remove("sidebar-init-collapsed");
      return;
    }
    document.body.classList.remove("sidebar-init-collapsed");
    try {
      if (localStorage.getItem(STORAGE_COLLAPSED) === "1") {
        sidebar.classList.add("collapsed");
      } else {
        sidebar.classList.remove("collapsed");
      }
    } catch (e) {
      /* ignore */
    }
    syncCollapseUi(sidebar, collapseBtn);
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

    if (collapseBtn) {
      collapseBtn.addEventListener("click", function () {
        if (!isDesktop()) {
          return;
        }
        sidebar.classList.toggle("collapsed");
        syncCollapseUi(sidebar, collapseBtn);
      });
    }

    window.matchMedia(MQ).addEventListener("change", function (e) {
      if (e.matches) {
        setOpen(false);
        applyStoredCollapsed(sidebar, collapseBtn);
      } else {
        document.body.classList.remove("sidebar-init-collapsed");
        sidebar.classList.remove("collapsed");
        syncCollapseUi(sidebar, collapseBtn);
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
