(function () {
  const KEY = "granago_cookie_consent";
  const banner = document.getElementById("cookie-consent-banner");
  const btn = document.getElementById("cookie-consent-accept");
  if (!banner || !btn) return;
  try {
    if (localStorage.getItem(KEY) === "1") return;
    banner.classList.remove("hidden");
    btn.addEventListener("click", function () {
      localStorage.setItem(KEY, "1");
      banner.classList.add("hidden");
    });
  } catch (e) {
    banner.classList.add("hidden");
  }
})();
