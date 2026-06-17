document.addEventListener("DOMContentLoaded", () => {
  const dropdownMeses = document.getElementById("dropdown-meses");
  const dropdownPersonalizado = document.getElementById("dropdown-personalizado");
  const listRoot =
    document.getElementById("historico-linhas") ||
    document.getElementById("lista-historico-transacoes") ||
    document.querySelector("[data-bank-icon-fallback]");
  const fallbackUrl = listRoot?.dataset.bankIconFallback;

  document.addEventListener("click", (e) => {
    if (dropdownMeses && !dropdownMeses.contains(e.target)) {
      dropdownMeses.removeAttribute("open");
    }
    if (dropdownPersonalizado && !dropdownPersonalizado.contains(e.target)) {
      dropdownPersonalizado.removeAttribute("open");
    }
  });

  if (fallbackUrl) {
    document.addEventListener(
      "error",
      (e) => {
        const el = e.target;
        if (el.tagName !== "IMG" || !el.classList.contains("conta-icone-dinamico")) {
          return;
        }
        el.src = fallbackUrl;
      },
      true
    );
  }

  if (!listRoot || !globalThis.ListaContextual) return;
  if (!listRoot.id && !listRoot.querySelector(".lista-contextual-item")) return;

  function isFaturaRow(item) {
    return item.classList.contains("historico-lancamento-fatura");
  }

  function getTitulo(item) {
    return item.dataset.transacaoDescricao || item.getAttribute("aria-label") || "";
  }

  ListaContextual.create({
    root: listRoot,
    itemSelector: ".lista-contextual-item",
    getPayload: (item) => ({
      el: item,
      transacaoId: item.dataset.transacaoId,
      faturaUrl: item.dataset.faturaUrl,
    }),
    getTitulo,
    getMeta: (item) => {
      const meta = item.querySelector("p.text-gray-500, p.text-\\[12px\\].text-gray-500");
      return meta?.textContent?.trim() || "";
    },
    getActions: (item) => {
      if (isFaturaRow(item)) {
        return [
          {
            id: "fatura",
            label: "Ver fatura",
            icon: "fa-solid fa-file-invoice",
          },
        ];
      }
      return [
        {
          id: "editar",
          label: "Editar transação",
          icon: "fa-solid fa-pen-to-square",
        },
        {
          id: "excluir",
          label: "Excluir transação",
          icon: "fa-solid fa-trash",
          danger: true,
        },
      ];
    },
    onAction: (actionId, payload) => {
      if (actionId === "fatura" && payload?.faturaUrl) {
        window.location.assign(payload.faturaUrl);
        return;
      }
      if (actionId === "editar" && payload?.transacaoId) {
        if (typeof window.abrirModalEditarTransacao === "function") {
          window.abrirModalEditarTransacao(payload.transacaoId);
        }
        return;
      }
      if (actionId === "excluir" && payload?.transacaoId) {
        if (typeof window.solicitarExclusaoTransacao === "function") {
          window.solicitarExclusaoTransacao(payload.transacaoId);
        }
      }
    },
  });

  document.body.addEventListener("htmx:afterSwap", (event) => {
    if (!event.detail?.target?.id?.includes("historico-linhas")) return;
    const start = event.detail.requestConfig?.perfStart;
    if (start && performance.measure) {
      try {
        performance.measure("htmx-historico-swap", { start, end: performance.now() });
      } catch (_) {
        /* ignore duplicate measure */
      }
    }
  });

  document.body.addEventListener("htmx:beforeRequest", (event) => {
    if (event.detail?.target?.id?.includes("historico-linhas")) {
      event.detail.requestConfig.perfStart = performance.now();
    }
  });
});
