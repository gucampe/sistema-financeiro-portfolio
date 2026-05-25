/** Depende de static/js/icon_combobox.js (window.initIconCombobox), carregado antes deste arquivo. */

document.addEventListener("DOMContentLoaded", () => {
  const initIconCombobox = window.initIconCombobox;
  const params = new URLSearchParams(window.location.search);
  const preCartao = params.get("pre_cartao");

  const btnAbrir = document.getElementById("btn-adicionar");
  const btnFechar = document.getElementById("btn-fechar");
  const overlay = document.getElementById("overlay-adicionar");
  const form = document.getElementById("form-adicionar");
  const selectTipo = document.getElementById("tipo");
  const selectCategoria = document.getElementById("categoria");
  const selectUnified = document.getElementById("id_conta_cartao");
  const hiddenConta = document.getElementById("id_conta");
  const hiddenCartao = document.getElementById("id_cartao");
  const hintCartao = document.getElementById("conta-cartao-hint-cartao");
  const modalHeader = overlay?.querySelector("h2");
  const btnExcluirModal = document.getElementById("btn-excluir-transacao-modal");

  let contaCombobox = null;
  let categoriaCombobox = null;

  function syncHiddensFromUnified() {
    if (!hiddenConta || !hiddenCartao || !selectUnified) return;
    const v = selectUnified.value || "";
    if (!v) {
      hiddenConta.value = "";
      hiddenCartao.value = "";
    } else if (v.startsWith("c:")) {
      hiddenConta.value = v.slice(2);
      hiddenCartao.value = "";
    } else if (v.startsWith("k:")) {
      hiddenCartao.value = v.slice(2);
      const opt = selectUnified.options[selectUnified.selectedIndex];
      const pid = opt?.dataset?.contaPadraoId;
      hiddenConta.value = pid ? String(pid) : "";
    }
    updateContaCartaoHint();
  }

  function updateContaCartaoHint() {
    if (!hintCartao || !selectUnified) return;
    const opt = selectUnified.options[selectUnified.selectedIndex];
    if (opt?.dataset?.kind === "cartao" && opt.dataset.contaPadraoNome) {
      hintCartao.textContent = `Conta utilizada neste lançamento: ${opt.dataset.contaPadraoNome}`;
      hintCartao.classList.remove("hidden");
    } else {
      hintCartao.textContent = "";
      hintCartao.classList.add("hidden");
    }
  }

  function syncUnifiedFromHiddensInicial() {
    if (!selectUnified || !hiddenConta || !hiddenCartao) return;
    const kv = (hiddenCartao.value || "").trim();
    const cv = (hiddenConta.value || "").trim();
    if (kv && [...selectUnified.options].some((o) => o.value === `k:${kv}`)) {
      selectUnified.value = `k:${kv}`;
    } else if (cv && [...selectUnified.options].some((o) => o.value === `c:${cv}`)) {
      selectUnified.value = `c:${cv}`;
    }
    syncHiddensFromUnified();
  }

  function aplicarCartaoPreSelecionado() {
    if (!selectUnified || !hiddenConta || !hiddenCartao) return;
    if (preCartao) {
      selectUnified.value = `k:${preCartao}`;
      syncHiddensFromUnified();
      return;
    }
    if (
      typeof window.__PRESELECT_CARTAO_MODAL !== "undefined" &&
      window.__PRESELECT_CARTAO_MODAL !== null &&
      window.__PRESELECT_CARTAO_MODAL !== ""
    ) {
      selectUnified.value = `k:${String(window.__PRESELECT_CARTAO_MODAL)}`;
      syncHiddensFromUnified();
      return;
    }
    syncUnifiedFromHiddensInicial();
  }

  window.applyUnifiedContaCartaoParaEdicao = function (data) {
    if (!selectUnified || !hiddenConta || !hiddenCartao) return;
    const kId = data.cartao && data.cartao.id;
    const cId = data.conta && data.conta.id;
    if (kId && [...selectUnified.options].some((o) => o.value === `k:${kId}`)) {
      selectUnified.value = `k:${kId}`;
    } else if (cId && [...selectUnified.options].some((o) => o.value === `c:${cId}`)) {
      selectUnified.value = `c:${cId}`;
    } else {
      selectUnified.value = "";
    }
    syncHiddensFromUnified();
    contaCombobox?.sync();
  };

  if (selectUnified && initIconCombobox) {
    contaCombobox = initIconCombobox(selectUnified, "account");
    window.__unifiedContaCartaoCombobox = contaCombobox;
  }
  if (selectCategoria && initIconCombobox) categoriaCombobox = initIconCombobox(selectCategoria, "category");

  selectUnified?.addEventListener("change", () => {
    syncHiddensFromUnified();
  });

  aplicarCartaoPreSelecionado();
  contaCombobox?.sync();

  const rootContaCartao = selectUnified?.closest("[data-combobox-root]");
  const rootCategoria = selectCategoria?.closest("[data-combobox-root]");

  if (!overlay) return;

  function popularCategorias(tipo, selecionadaId = null) {
    if (!selectCategoria) return;
    fetch(`/categorias/listar-ativas/?tipo=${tipo || "despesa"}`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then((r) => r.json())
      .then((data) => {
        selectCategoria.innerHTML = '<option value="">Selecione uma categoria</option>';
        if (data.status === "ok" && data.categorias?.length) {
          data.categorias.forEach((c) => {
            const opt = document.createElement("option");
            opt.value = c.id;
            opt.textContent = c.nome;
            if (c.icone != null) opt.dataset.icone = c.icone;
            if (c.cor != null) opt.dataset.cor = c.cor;
            if (selecionadaId && c.id == selecionadaId) opt.selected = true;
            selectCategoria.appendChild(opt);
          });
        }
        categoriaCombobox?.refresh();
      })
      .catch(() => {});
  }

  function limparErroContaAjax() {
    const el = document.getElementById("erro-conta-ajax");
    if (el) {
      el.textContent = "";
      el.classList.add("hidden");
    }
  }

  function fecharComboboxes() {
    contaCombobox?.close();
    categoriaCombobox?.close();
  }

  document.addEventListener("click", (e) => {
    const inContaCartao = rootContaCartao?.contains(e.target);
    const inCategoria = rootCategoria?.contains(e.target);
    if (inContaCartao) {
      categoriaCombobox?.close();
      return;
    }
    if (inCategoria) {
      contaCombobox?.close();
      return;
    }
    fecharComboboxes();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") fecharComboboxes();
  });

  function atualizarBotaoExcluirModal(editandoId) {
    if (!btnExcluirModal) return;
    if (editandoId) {
      btnExcluirModal.classList.remove("hidden");
    } else {
      btnExcluirModal.classList.add("hidden");
    }
  }

  function abrirModalEditar(id) {
    if (!id) return;
    fetch(`/transacoes/${id}/editar/?ajax=1`)
      .then((r) => r.json())
      .then((data) => {
        overlay.dataset.editando = id;
        if (modalHeader) modalHeader.textContent = "Editar Transação";
        selectTipo.value = data.tipo;
        document.getElementById("valor").value = data.valor;
        document.getElementById("descricao").value = data.descricao;
        document.getElementById("data").value = data.data;
        window.applyUnifiedContaCartaoParaEdicao?.(data);
        popularCategorias(data.tipo, data.categoria.id);
        limparErroContaAjax();
        atualizarBotaoExcluirModal(id);
        overlay.classList.remove("hidden");
        setTimeout(() => overlay.classList.remove("opacity-0"), 10);
      })
      .catch((err) => console.error("Erro ao carregar transação:", err));
  }

  window.abrirModalEditarTransacao = abrirModalEditar;

  btnAbrir?.addEventListener("click", () => {
    overlay.dataset.editando = "";
    atualizarBotaoExcluirModal("");
    if (modalHeader) modalHeader.textContent = "Nova Transação";
    const tipo = selectTipo?.value || "despesa";
    if (!tipo) return;
    limparErroContaAjax();
    popularCategorias(tipo);
    overlay.classList.remove("hidden");
    setTimeout(() => overlay.classList.remove("opacity-0"), 10);
  });

  const fecharModal = () => {
    overlay.classList.add("opacity-0");
    setTimeout(() => overlay.classList.add("hidden"), 300);
    overlay.dataset.editando = "";
    atualizarBotaoExcluirModal("");
    fecharComboboxes();
    form.reset();
    aplicarCartaoPreSelecionado();
    contaCombobox?.sync();
    categoriaCombobox?.sync();
  };

  btnFechar?.addEventListener("click", fecharModal);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) fecharModal();
  });

  btnExcluirModal?.addEventListener("click", () => {
    const id = overlay.dataset.editando;
    if (!id) return;
    fecharModal();
    if (typeof window.solicitarExclusaoTransacao === "function") {
      window.solicitarExclusaoTransacao(id);
    }
  });

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    syncHiddensFromUnified();
    const editandoId = overlay.dataset.editando;
    const actionAttr = form.getAttribute("action") || "";
    const url = editandoId
      ? new URL(`/transacoes/${editandoId}/editar/`, window.location.origin).href
      : new URL(actionAttr || "/transacoes/adicionar/", window.location.origin).href;

    const formData = new FormData(form);
    const csrfInput = form.querySelector("[name=csrfmiddlewaretoken]");
    const csrfToken = csrfInput?.value || formData.get("csrfmiddlewaretoken") || "";

    try {
      const response = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": csrfToken,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: formData,
      });

      const raw = await response.text();
      let data;
      try {
        data = raw ? JSON.parse(raw) : {};
      } catch {
        alert(
          `Resposta inválida do servidor (HTTP ${response.status}). ` +
            "Se o problema persistir, verifique o login e recarregue a página."
        );
        return;
      }

      if (data.status === "ok") {
        limparErroContaAjax();
        fecharModal();
        window.location.reload();
        return;
      }

      const erroContaEl = document.getElementById("erro-conta-ajax");
      if (erroContaEl && data.errors && data.errors.conta && data.errors.conta.length) {
        erroContaEl.textContent = data.errors.conta[0];
        erroContaEl.classList.remove("hidden");
      }
      if (data.errors && Object.keys(data.errors).length) {
        alert("Erro ao salvar: " + JSON.stringify(data.errors));
      } else if (!response.ok) {
        alert(`Não foi possível salvar (HTTP ${response.status}).`);
      }
    } catch (error) {
      console.error(error);
      alert("Erro de comunicação. Verifique a conexão e tente de novo.");
    }
  });

  selectTipo?.addEventListener("change", () => {
    const tipo = selectTipo.value || "despesa";
    popularCategorias(tipo);
  });
});
