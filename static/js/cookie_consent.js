(function () {
  const KEY = "granago_cookie_consent";
  const banner = document.getElementById("cookie-consent-banner");
  if (!banner) return;

  const btnEssential = document.getElementById("cookie-consent-accept");
  const btnMarketing = document.getElementById("cookie-consent-marketing");
  const needsMarketingChoice = banner.getAttribute("data-marketing-choice") === "1";

  function readConsent() {
    try {
      return localStorage.getItem(KEY);
    } catch (e) {
      return null;
    }
  }

  function writeConsent(value) {
    try {
      localStorage.setItem(KEY, value);
    } catch (e) {
      /* ignore quota / private mode */
    }
  }

  function hide() {
    banner.classList.add("hidden");
  }

  function show() {
    banner.classList.remove("hidden");
  }

  function alreadyDecided(value) {
    if (needsMarketingChoice) {
      return value === "marketing" || value === "essential";
    }
    return value === "1" || value === "essential" || value === "marketing";
  }

  const current = readConsent();
  if (alreadyDecided(current)) {
    if (current === "marketing") {
      document.dispatchEvent(new Event("granago:marketing-consent"));
    }
    return;
  }

  show();

  if (btnEssential) {
    btnEssential.addEventListener("click", function () {
      writeConsent(needsMarketingChoice ? "essential" : "1");
      hide();
    });
  }

  if (btnMarketing) {
    btnMarketing.addEventListener("click", function () {
      writeConsent("marketing");
      hide();
      document.dispatchEvent(new Event("granago:marketing-consent"));
    });
  }
})();
