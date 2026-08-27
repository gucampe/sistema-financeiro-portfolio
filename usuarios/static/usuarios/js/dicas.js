(function () {
  "use strict";

  var banner = document.querySelector("[data-dica]");
  if (!banner) return;

  var dicaId = banner.getAttribute("data-dica") || "";
  var versao = parseInt(banner.getAttribute("data-dica-versao") || "0", 10) || 0;
  var dispensarUrl = banner.getAttribute("data-dispensar-url") || "/dica-dispensar/";
  var eventoUrl = banner.getAttribute("data-evento-url") || "/produto-evento/";

  function csrfToken() {
    var match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function postJson(url, body) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify(body),
    }).catch(function () {});
  }

  banner.querySelectorAll("[data-dica-abrir]").forEach(function (el) {
    el.addEventListener("click", function () {
      postJson(eventoUrl, {
        evento: "context_tip_opened",
        payload: { dica_id: dicaId, versao: versao },
      });
    });
  });

  banner.querySelectorAll("[data-dica-dispensar]").forEach(function (el) {
    el.addEventListener("click", function () {
      postJson(dispensarUrl, { dica_id: dicaId }).then(function () {
        banner.remove();
      });
    });
  });
})();
