(function () {
  "use strict";

  var COOKIE_KEY = "granago_cookie_consent";
  var DISMISS_KEY = "granago_pwa_install_dismissed_at";
  var STANDALONE_SESSION_KEY = "granago_pwa_opened_standalone";
  var COOLDOWN_MS = 14 * 24 * 60 * 60 * 1000;
  var SHOWN_SESSION_KEY = "granago_pwa_prompt_shown";

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function isStandalone() {
    try {
      if (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) {
        return true;
      }
    } catch (e) {}
    return Boolean(window.navigator.standalone);
  }

  function isIos() {
    var ua = window.navigator.userAgent || "";
    return /iPad|iPhone|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  }

  function isIosSafari() {
    if (!isIos()) return false;
    var ua = window.navigator.userAgent || "";
    var isCriOS = /CriOS/.test(ua);
    var isFxiOS = /FxiOS/.test(ua);
    var isEdgiOS = /EdgiOS/.test(ua);
    return !isCriOS && !isFxiOS && !isEdgiOS;
  }

  function cookiesOk() {
    try {
      var v = localStorage.getItem(COOKIE_KEY);
      return v === "1" || v === "essential" || v === "marketing";
    } catch (e) {
      return true;
    }
  }

  function cookieBannerVisible() {
    var el = document.getElementById("cookie-consent-banner");
    return Boolean(el && !el.classList.contains("hidden"));
  }

  function inCooldown() {
    try {
      var raw = localStorage.getItem(DISMISS_KEY);
      if (!raw) return false;
      var ts = parseInt(raw, 10);
      if (!ts) return false;
      return Date.now() - ts < COOLDOWN_MS;
    } catch (e) {
      return false;
    }
  }

  function csrfToken() {
    var match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function eventoUrl() {
    return document.documentElement.getAttribute("data-pwa-evento-url") || "/produto-evento/";
  }

  function canSendEvent() {
    return document.documentElement.getAttribute("data-pwa-auth") === "1";
  }

  function sendEvent(evento, origem) {
    if (!canSendEvent()) return;
    try {
      fetch(eventoUrl(), {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({
          evento: evento,
          payload: origem ? { origem: origem } : {},
        }),
      }).catch(function () {});
    } catch (e) {}
  }

  function markDismissed() {
    try {
      localStorage.setItem(DISMISS_KEY, String(Date.now()));
    } catch (e) {}
  }

  function applyMode(root) {
    if (!root) return;
    var mode = "unsupported";
    if (isStandalone()) mode = "installed";
    else if (isIos() && !isIosSafari()) mode = "ios-other";
    else if (isIosSafari()) mode = "ios-safari";
    else if (window.__granagoDeferredPrompt) mode = "chromium";
    else mode = "chromium-wait";
    root.setAttribute("data-pwa-mode", mode);
    return mode;
  }

  function shouldShowCta() {
    if (!canSendEvent()) return false;
    if (isStandalone()) return false;
    if (inCooldown()) return false;
    if (!cookiesOk() || cookieBannerVisible()) return false;
    if (isIos()) return true;
    return Boolean(window.__granagoDeferredPrompt);
  }

  function showBannerIfNeeded() {
    var banner = qs("[data-pwa-banner]");
    if (!banner) return;
    applyMode(banner);
    if (!shouldShowCta()) {
      banner.classList.add("hidden");
      banner.setAttribute("hidden", "");
      return;
    }
    var already = false;
    try {
      already = sessionStorage.getItem(SHOWN_SESSION_KEY) === "1";
    } catch (e) {}
    banner.classList.remove("hidden");
    banner.removeAttribute("hidden");
    if (!already) {
      try {
        sessionStorage.setItem(SHOWN_SESSION_KEY, "1");
      } catch (e) {}
      sendEvent("pwa_install_prompt_shown", applyMode(banner));
    }
  }

  function hideBanner() {
    var banner = qs("[data-pwa-banner]");
    if (!banner) return;
    banner.classList.add("hidden");
    banner.setAttribute("hidden", "");
  }

  function bindInstallButtons(root) {
    if (!root) return;
    root.querySelectorAll("[data-pwa-install]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        sendEvent("pwa_install_clicked", "chromium");
        var deferred = window.__granagoDeferredPrompt;
        if (!deferred) return;
        deferred.prompt();
        Promise.resolve(deferred.userChoice)
          .then(function (choice) {
            window.__granagoDeferredPrompt = null;
            if (choice && choice.outcome === "accepted") {
              sendEvent("pwa_installed", "chromium");
              hideBanner();
            }
            applyMode(qs("[data-pwa-banner]"));
            applyMode(qs("[data-pwa-settings]"));
            showBannerIfNeeded();
          })
          .catch(function () {
            window.__granagoDeferredPrompt = null;
            showBannerIfNeeded();
          });
      });
    });
    root.querySelectorAll("[data-pwa-dismiss]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        markDismissed();
        sendEvent("pwa_install_dismissed", "cta");
        hideBanner();
      });
    });
  }

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function () {});
    });
  }

  window.addEventListener("beforeinstallprompt", function (event) {
    event.preventDefault();
    window.__granagoDeferredPrompt = event;
    applyMode(qs("[data-pwa-banner]"));
    applyMode(qs("[data-pwa-settings]"));
    showBannerIfNeeded();
  });

  window.addEventListener("appinstalled", function () {
    window.__granagoDeferredPrompt = null;
    sendEvent("pwa_installed", "appinstalled");
    hideBanner();
    applyMode(qs("[data-pwa-settings]"));
  });

  function boot() {
    if (document.documentElement) {
      if (isStandalone()) {
        document.documentElement.classList.add("pwa-standalone");
      }
    }
    applyMode(qs("[data-pwa-banner]"));
    applyMode(qs("[data-pwa-settings]"));
    bindInstallButtons(qs("[data-pwa-banner]"));
    bindInstallButtons(qs("[data-pwa-settings]"));
    showBannerIfNeeded();

    if (isStandalone() && canSendEvent()) {
      var already = false;
      try {
        already = sessionStorage.getItem(STANDALONE_SESSION_KEY) === "1";
      } catch (e) {}
      if (!already) {
        try {
          sessionStorage.setItem(STANDALONE_SESSION_KEY, "1");
        } catch (e) {}
        sendEvent("pwa_opened_standalone", "standalone");
      }
    }

    var cookieBtn = document.getElementById("cookie-consent-accept");
    if (cookieBtn) {
      cookieBtn.addEventListener("click", function () {
        window.setTimeout(showBannerIfNeeded, 0);
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
