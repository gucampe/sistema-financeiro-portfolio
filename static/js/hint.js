/**
 * Popover ⓘ — abre no clique/toque, fecha com Escape ou clique fora.
 * Sem hover. Um painel aberto por vez. Respeita prefers-reduced-motion.
 */
(function () {
  const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let aberto = null;

  function painel(root) {
    return root.querySelector(".app-hint__panel");
  }

  function botao(root) {
    return root.querySelector(".app-hint__btn");
  }

  function fechar(root) {
    if (!root) return;
    const panel = painel(root);
    const btn = botao(root);
    if (panel) {
      panel.hidden = true;
      panel.classList.add("invisible", "pointer-events-none");
      panel.classList.remove("visible");
    }
    if (btn) btn.setAttribute("aria-expanded", "false");
    if (aberto === root) aberto = null;
  }

  function abrir(root) {
    if (aberto && aberto !== root) fechar(aberto);
    const panel = painel(root);
    const btn = botao(root);
    if (!panel || !btn) return;
    panel.hidden = false;
    panel.classList.remove("invisible", "pointer-events-none");
    panel.classList.add("visible");
    btn.setAttribute("aria-expanded", "true");
    aberto = root;
    if (!REDUCED) {
      panel.style.transition = "opacity 150ms ease";
    }
  }

  function toggle(root) {
    if (aberto === root) fechar(root);
    else abrir(root);
  }

  document.addEventListener("click", function (e) {
    const btn = e.target instanceof Element ? e.target.closest("[data-hint] .app-hint__btn") : null;
    if (btn) {
      e.preventDefault();
      const root = btn.closest("[data-hint]");
      if (root) toggle(root);
      return;
    }
    if (aberto && e.target instanceof Element && !aberto.contains(e.target)) {
      fechar(aberto);
    }
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && aberto) {
      const btn = botao(aberto);
      fechar(aberto);
      btn?.focus();
    }
  });
})();
