(function () {
  var cfg = window.GRANAGO_META;
  if (!cfg || !cfg.pixelId) return;

  var KEY = "granago_cookie_consent";
  var loaded = false;

  function marketingOk() {
    try {
      return localStorage.getItem(KEY) === "marketing";
    } catch (e) {
      return false;
    }
  }

  function loadPixel() {
    if (loaded || !marketingOk()) return;
    loaded = true;

    var f = window;
    var b = document;
    var e = "script";
    var v = "https://connect.facebook.net/en_US/fbevents.js";
    var n;
    var t;
    var s;
    if (f.fbq) {
      n = f.fbq;
    } else {
      n = f.fbq = function () {
        n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
      };
      if (!f._fbq) f._fbq = n;
      n.push = n;
      n.loaded = true;
      n.version = "2.0";
      n.queue = [];
      t = b.createElement(e);
      t.async = true;
      t.src = v;
      s = b.getElementsByTagName(e)[0];
      s.parentNode.insertBefore(t, s);
    }

    var am = cfg.advancedMatching && typeof cfg.advancedMatching === "object" ? cfg.advancedMatching : {};
    if (Object.keys(am).length) {
      window.fbq("init", cfg.pixelId, am);
    } else {
      window.fbq("init", cfg.pixelId);
    }
    window.fbq("track", "PageView");
    if (cfg.completeRegistrationEventId) {
      window.fbq(
        "track",
        "CompleteRegistration",
        {},
        { eventID: cfg.completeRegistrationEventId }
      );
    }
  }

  document.addEventListener("granago:marketing-consent", loadPixel);
  loadPixel();
})();
