(function () {
  "use strict";

  var overlay = document.getElementById("ajuda-overlay");
  if (!overlay || typeof window.GranaGoModal === "undefined") return;

  var busca = overlay.querySelector("[data-ajuda-busca]");
  var buscaVazia = overlay.querySelector("[data-ajuda-busca-vazia]");
  var home = overlay.querySelector("[data-ajuda-home]");
  var artigoView = overlay.querySelector("[data-ajuda-artigo-view]");
  var artigoTitulo = overlay.querySelector("[data-ajuda-artigo-titulo]");
  var artigoCorpo = overlay.querySelector("[data-ajuda-artigo-corpo]");
  var catalogoEl = document.getElementById("ajuda-catalogo-json");
  var eventoUrl = overlay.getAttribute("data-evento-url") || "/produto-evento/";
  var catalogo = [];
  try {
    catalogo = catalogoEl ? JSON.parse(catalogoEl.textContent || "[]") : [];
  } catch (_err) {
    catalogo = [];
  }

  window.GranaGoModal.bind(overlay, {});

  var buscaTimer = null;
  var ultimaQuery = "";

  function csrfToken() {
    var match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function registrar(evento, payload) {
    fetch(eventoUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({ evento: evento, payload: payload || {} }),
    }).catch(function () {});
  }

  function normalizar(texto) {
    return String(texto || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();
  }

  function artigoPorId(id) {
    for (var i = 0; i < catalogo.length; i += 1) {
      if (catalogo[i].id === id) return catalogo[i];
    }
    return null;
  }

  function artigoCorresponde(artigo, query) {
    var q = normalizar(query).trim();
    if (!q) return true;
    if (!artigo) return false;
    var haystack = normalizar(
      [artigo.titulo, artigo.resumo, artigo.grupo, artigo.tipo]
        .concat(artigo.tags || [])
        .join(" ")
    );
    return haystack.indexOf(q) !== -1;
  }

  function mostrarHome() {
    if (home) home.classList.remove("hidden");
    if (artigoView) artigoView.classList.add("hidden");
    if (artigoCorpo) artigoCorpo.replaceChildren();
    filtrar(busca ? busca.value : "");
  }

  function abrirArtigo(id, origem) {
    var artigo = artigoPorId(id);
    var template = document.getElementById("ajuda-artigo-" + id);
    if (!artigo || !template || !artigoView || !home) return;
    home.classList.add("hidden");
    artigoView.classList.remove("hidden");
    if (artigoTitulo) artigoTitulo.textContent = artigo.titulo;
    if (artigoCorpo) {
      artigoCorpo.replaceChildren();
      artigoCorpo.appendChild(template.content.cloneNode(true));
    }
    registrar("help_article_opened", { article_id: id, origem: origem || "lista" });
  }

  function filtrar(query) {
    var q = String(query || "").trim();
    var cards = home ? home.querySelectorAll("[data-ajuda-abrir]") : [];
    var visiveis = 0;
    cards.forEach(function (card) {
      var id = card.getAttribute("data-ajuda-abrir");
      var show = artigoCorresponde(artigoPorId(id), q);
      card.classList.toggle("hidden", !show);
      if (show) visiveis += 1;
    });
    if (home) {
      home.querySelectorAll("[data-ajuda-grupo]").forEach(function (grupo) {
        var cardsVisiveis = grupo.querySelectorAll("[data-ajuda-abrir]:not(.hidden)");
        grupo.classList.toggle("hidden", Boolean(q) && cardsVisiveis.length === 0);
      });
    }
    if (buscaVazia) buscaVazia.classList.toggle("hidden", visiveis > 0 || !q);
  }

  function limparBusca() {
    if (busca) busca.value = "";
    ultimaQuery = "";
    filtrar("");
  }

  function abrirAjuda(artigoId) {
    if (!artigoId) limparBusca();
    mostrarHome();
    window.GranaGoModal.open(overlay);
    registrar("help_opened", { origem: artigoId ? "deep_link" : "nav" });
    if (artigoId) abrirArtigo(artigoId, "deep_link");
  }

  function artigoDaQuery() {
    try {
      var params = new URLSearchParams(window.location.search);
      var id = params.get("ajuda");
      return artigoPorId(id) ? id : "";
    } catch (_err) {
      return "";
    }
  }

  overlay.addEventListener("click", function (event) {
    var btn = event.target.closest("[data-ajuda-abrir]");
    if (!btn || !overlay.contains(btn)) return;
    var origem =
      artigoView && !artigoView.classList.contains("hidden") ? "relacionado" : "lista";
    abrirArtigo(btn.getAttribute("data-ajuda-abrir"), origem);
  });

  var voltar = overlay.querySelector("[data-ajuda-voltar]");
  if (voltar) {
    voltar.addEventListener("click", mostrarHome);
  }

  if (busca) {
    busca.addEventListener("input", function () {
      var valor = busca.value || "";
      filtrar(valor);
      window.clearTimeout(buscaTimer);
      var q = valor.trim().slice(0, 80);
      if (!q || q === ultimaQuery) return;
      buscaTimer = window.setTimeout(function () {
        ultimaQuery = q;
        registrar("help_search_used", { q: q });
      }, 400);
    });
  }

  document.addEventListener("click", function (event) {
    var trigger = event.target.closest(".js-tutoriais-trigger");
    if (!trigger) return;
    event.preventDefault();
    abrirAjuda("");
  });

  function considerarDeepLink() {
    var id = artigoDaQuery();
    if (id) abrirAjuda(id);
  }

  considerarDeepLink();
  window.addEventListener("popstate", considerarDeepLink);
})();
