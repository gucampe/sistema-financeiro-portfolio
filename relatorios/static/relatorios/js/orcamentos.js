(function () {
  const root = document.getElementById("orcamentos-root");
  if (!root) return;

  const overlay = document.getElementById("overlay-orcamento");
  const form = document.getElementById("form-orcamento");
  const erroBox = document.getElementById("erro-orcamento");
  const modalTitulo = document.getElementById("modal-orcamento-titulo");
  const salvarUrl = root.dataset.salvarUrl;
  const toggleTemplate = root.dataset.toggleUrlTemplate || "";

  function getCsrfToken() {
    return document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
  }

  function openModal(trigger) {
    if (!overlay) return;
    if (globalThis.GranaGoModal) {
      globalThis.GranaGoModal.open(overlay, { trigger: trigger || undefined });
    } else {
      overlay.classList.remove("hidden", "opacity-0");
      overlay.classList.add("opacity-100");
      overlay.setAttribute("aria-hidden", "false");
    }
  }

  function closeModal() {
    if (!overlay) return;
    if (globalThis.GranaGoModal) {
      globalThis.GranaGoModal.close(overlay);
    } else {
      overlay.classList.add("hidden", "opacity-0");
      overlay.classList.remove("opacity-100");
      overlay.setAttribute("aria-hidden", "true");
    }
  }

  function initMoeda() {
    if (window.MoedaInput && form) {
      form.querySelectorAll("[data-moeda-input]").forEach((el) => {
        window.MoedaInput.init(el);
      });
    } else if (typeof window.initMoedaInputs === "function" && form) {
      window.initMoedaInputs(form);
    }
  }

  function showErro(msg) {
    if (!erroBox) return;
    erroBox.textContent = msg;
    erroBox.classList.remove("hidden");
  }

  function hideErro() {
    if (!erroBox) return;
    erroBox.classList.add("hidden");
    erroBox.textContent = "";
  }

  function resetForm() {
    if (!form) return;
    form.reset();
    document.getElementById("orcamento_id").value = "";
    document.getElementById("ref_ano").value = root.dataset.ano || "";
    document.getElementById("ref_mes").value = root.dataset.mes || "";
    const cat = document.getElementById("id_categoria");
    if (cat) cat.disabled = false;
    const ativo = document.getElementById("id_ativo");
    if (ativo) ativo.checked = true;
    if (modalTitulo) modalTitulo.textContent = "Novo orçamento";
    initMoeda();
  }

  function openNovo(categoriaId, trigger) {
    resetForm();
    hideErro();
    if (categoriaId) {
      const cat = document.getElementById("id_categoria");
      if (cat) cat.value = String(categoriaId);
    }
    openModal(trigger);
  }

  function openEditar(btn) {
    resetForm();
    hideErro();
    const o = btn.dataset;
    document.getElementById("orcamento_id").value = o.orcamentoId || "";
    document.getElementById("id_categoria").value = o.categoriaId || "";
    document.getElementById("id_categoria").disabled = true;
    const valorField = document.getElementById("id_valor_planejado");
    if (valorField && o.valor) {
      if (window.MoedaInput) {
        window.MoedaInput.setValueFromDecimal(valorField, o.valor);
      } else {
        valorField.value = o.valor;
      }
    }
    document.getElementById("id_inicio_mes").value = o.inicioMes || "";
    document.getElementById("id_inicio_ano").value = o.inicioAno || "";
    document.getElementById("id_fim_mes").value = o.fimMes || "";
    document.getElementById("id_fim_ano").value = o.fimAno || "";
    document.getElementById("id_ativo").checked = o.ativo === "1";
    if (modalTitulo) modalTitulo.textContent = "Editar orçamento";
    initMoeda();
    openModal(btn);
  }

  function fecharModalCleanup() {
    hideErro();
    const cat = document.getElementById("id_categoria");
    if (cat) cat.disabled = false;
  }

  if (overlay && globalThis.GranaGoModal) {
    globalThis.GranaGoModal.bind(overlay, { onClose: fecharModalCleanup });
  }

  document.getElementById("btn-novo-orcamento")?.addEventListener("click", (e) => {
    openNovo(null, e.currentTarget);
  });
  document.getElementById("btn-primeiro-orcamento")?.addEventListener("click", (e) => {
    openNovo(null, e.currentTarget);
  });
  document.getElementById("btn-novo-orcamento-empty")?.addEventListener("click", (e) => {
    openNovo(null, e.currentTarget);
  });

  root.querySelectorAll(".js-criar-orcamento-categoria").forEach((btn) => {
    btn.addEventListener("click", () => openNovo(btn.dataset.categoriaId, btn));
  });

  root.querySelectorAll(".js-editar-orcamento").forEach((btn) => {
    btn.addEventListener("click", () => openEditar(btn));
  });

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideErro();
    const data = new FormData(form);
    data.set("csrfmiddlewaretoken", getCsrfToken());
    try {
      const res = await fetch(salvarUrl, { method: "POST", body: data, credentials: "same-origin" });
      const json = await res.json();
      if (!res.ok || json.status !== "ok") {
        const errs = json.errors || {};
        const msg = Object.values(errs).flat().join(" ") || "Não foi possível salvar.";
        showErro(msg);
        return;
      }
      closeModal();
      window.location.reload();
    } catch {
      showErro("Erro de conexão. Tente novamente.");
    }
  });

  root.querySelectorAll(".js-toggle-orcamento").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.orcamentoId;
      if (!id) return;
      const url = toggleTemplate.replace("/0/", `/${id}/`);
      const data = new FormData();
      data.set("csrfmiddlewaretoken", getCsrfToken());
      try {
        const res = await fetch(url, { method: "POST", body: data, credentials: "same-origin" });
        const json = await res.json();
        if (json.status === "ok") window.location.reload();
      } catch {
        /* noop */
      }
    });
  });

  const mobileCardsMq = window.matchMedia("(max-width: 639px)");

  function setCardExpanded(card, expanded) {
    card.classList.toggle("is-expanded", expanded);
    card.setAttribute("aria-expanded", String(expanded));
    const main = card.querySelector(".orc-cat-card__main");
    if (main) main.setAttribute("aria-expanded", String(expanded));
  }

  function collapseMobileCards(exceptCard) {
    root.querySelectorAll("[data-orcamento-card]").forEach((card) => {
      if (card !== exceptCard) setCardExpanded(card, false);
    });
  }

  function syncMobileCardA11y() {
    root.querySelectorAll("[data-orcamento-card]").forEach((card) => {
      const main = card.querySelector(".orc-cat-card__main");
      const panel = card.querySelector(".orc-cat-actions-panel");
      if (!main) return;

      if (mobileCardsMq.matches) {
        main.setAttribute("role", "button");
        main.setAttribute("tabindex", "0");
        main.setAttribute("aria-expanded", String(card.classList.contains("is-expanded")));
        if (panel?.id) main.setAttribute("aria-controls", panel.id);
      } else {
        main.removeAttribute("role");
        main.removeAttribute("tabindex");
        main.removeAttribute("aria-controls");
        main.removeAttribute("aria-expanded");
        setCardExpanded(card, false);
      }
    });
  }

  function initMobileCardExpand() {
    root.querySelectorAll("[data-orcamento-card]").forEach((card) => {
      const main = card.querySelector(".orc-cat-card__main");
      const history = card.querySelector(".orc-cat-history");
      const actionsPanel = card.querySelector(".orc-cat-actions-panel");

      history?.addEventListener("click", (e) => e.stopPropagation());
      actionsPanel?.addEventListener("click", (e) => e.stopPropagation());

      main?.addEventListener("click", () => {
        if (!mobileCardsMq.matches) return;
        const willExpand = !card.classList.contains("is-expanded");
        setCardExpanded(card, willExpand);
        if (willExpand) collapseMobileCards(card);
      });

      main?.addEventListener("keydown", (e) => {
        if (!mobileCardsMq.matches) return;
        if (e.key !== "Enter" && e.key !== " ") return;
        e.preventDefault();
        main.click();
      });
    });

    syncMobileCardA11y();
    mobileCardsMq.addEventListener("change", syncMobileCardA11y);
  }

  initMobileCardExpand();
})();
