/** Depende de static/js/icon_combobox.js (window.initIconCombobox), carregado antes deste arquivo. */

document.addEventListener("DOMContentLoaded", () => {
  const initIconCombobox = window.initIconCombobox;
  const params = new URLSearchParams(window.location.search);
  const preCartao = params.get("pre_cartao");

  const btnAbrir = document.getElementById("btn-adicionar");
  const btnSidebarAbrir = document.getElementById("sidebar-btn-adicionar");
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

  function algumComboboxAberto() {
    const roots = [rootContaCartao, rootCategoria].filter(Boolean);
    return roots.some((root) => {
      const list = root.querySelector("[data-combobox-list]");
      return list && !list.classList.contains("hidden");
    });
  }

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
        const valorEl = document.getElementById("valor");
        if (valorEl && window.MoedaInput) {
          window.MoedaInput.setValueFromDecimal(valorEl, data.valor);
        } else if (valorEl) {
          valorEl.value = data.valor;
        }
        document.getElementById("descricao").value = data.descricao;
        document.getElementById("data").value = data.data;
        window.applyUnifiedContaCartaoParaEdicao?.(data);
        popularCategorias(data.tipo, data.categoria.id);
        limparErroContaAjax();
        atualizarBotaoExcluirModal(id);
        globalThis.GranaGoModal?.open(overlay);
      })
      .catch((err) => console.error("Erro ao carregar transação:", err));
  }

  window.abrirModalEditarTransacao = abrirModalEditar;

  function abrirModalNovaTransacao(triggerEl, { tipo: tipoOverride, titulo } = {}) {
    overlay.dataset.editando = "";
    atualizarBotaoExcluirModal("");
    if (tipoOverride && selectTipo) {
      selectTipo.value = tipoOverride;
      selectTipo.dispatchEvent(new Event("change", { bubbles: true }));
    }
    if (modalHeader) {
      modalHeader.textContent =
        titulo || (tipoOverride === "receita" ? "Nova Receita" : tipoOverride === "despesa" ? "Nova Despesa" : "Nova Transação");
    }
    const tipo = selectTipo?.value || "despesa";
    if (!tipo) return;
    limparErroContaAjax();
    popularCategorias(tipo);
    globalThis.GranaGoModal?.open(overlay, { trigger: triggerEl || undefined });
  }

  [btnAbrir, btnSidebarAbrir].filter(Boolean).forEach((btn) => {
    btn.addEventListener("click", () => abrirModalNovaTransacao(btn));
  });

  document.querySelectorAll("[data-abrir-transacao]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tipo = btn.getAttribute("data-abrir-transacao") || "despesa";
      abrirModalNovaTransacao(btn, {
        tipo,
        titulo: tipo === "receita" ? "Nova Receita" : "Nova Despesa",
      });
    });
  });

  const inputDescricao = document.getElementById("descricao");
  const chipSugestao = document.getElementById("categorizacao-sugestao-chip");
  const hidSugId = document.getElementById("categorizacao_sugerida_id");
  const hidConf = document.getElementById("categorizacao_confianca");
  const hidFonte = document.getElementById("categorizacao_fonte");
  const hidMerchant = document.getElementById("categorizacao_merchant_key");
  let sugestaoTimer = null;

  function limparSugestaoCategoria() {
    if (hidSugId) hidSugId.value = "";
    if (hidConf) hidConf.value = "";
    if (hidFonte) hidFonte.value = "";
    if (hidMerchant) hidMerchant.value = "";
    if (chipSugestao) {
      chipSugestao.innerHTML = "";
      chipSugestao.classList.add("hidden");
    }
  }

  function aplicarSugestaoNoChip(sug) {
    if (!chipSugestao || !sug) return;
    if (hidSugId) hidSugId.value = String(sug.categoria_id);
    if (hidConf) hidConf.value = String(sug.confianca);
    if (hidFonte) hidFonte.value = sug.fonte || "";
    if (hidMerchant) hidMerchant.value = sug.merchant_key || "";

    const btn = document.createElement("button");
    btn.type = "button";
    const isLlm = (sug.fonte || "") === "llm_gemini" && sug.mostrar_badge_ia !== false;
    btn.className = isLlm
      ? "inline-flex items-center gap-1 rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-xs font-medium text-violet-900 hover:bg-violet-100"
      : "inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800 hover:bg-emerald-100";
    btn.textContent = `Sugerido: ${sug.categoria_nome}`;
    btn.title = sug.explicacao || "";
    if (isLlm) {
      const iaBadge = document.createElement("span");
      iaBadge.className = "rounded-full bg-violet-200 px-1.5 py-0.5 text-[10px] font-bold uppercase text-violet-900";
      iaBadge.textContent = "IA";
      iaBadge.title = "Sugestão por inteligência artificial (Gemini)";
      btn.appendChild(iaBadge);
    }
    btn.addEventListener("click", () => {
      if (selectCategoria) {
        selectCategoria.value = String(sug.categoria_id);
        categoriaCombobox?.sync();
      }
    });
    chipSugestao.innerHTML = "";
    chipSugestao.appendChild(btn);
    chipSugestao.classList.remove("hidden");
  }

  async function buscarSugestaoCategoria() {
    const descricao = (inputDescricao?.value || "").trim();
    const tipo = selectTipo?.value || "despesa";
    if (descricao.length < 3) {
      limparSugestaoCategoria();
      return;
    }
    try {
      const params = new URLSearchParams({ descricao, tipo });
      const res = await fetch(`/categorizacao/sugerir/?${params.toString()}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const data = await res.json();
      if (data.status === "ok" && data.sugestao) {
        aplicarSugestaoNoChip(data.sugestao);
      } else {
        limparSugestaoCategoria();
      }
    } catch {
      limparSugestaoCategoria();
    }
  }

  const fecharModal = () => {
    limparSugestaoCategoria();
    overlay.dataset.editando = "";
    atualizarBotaoExcluirModal("");
    fecharComboboxes();
    form.reset();
    aplicarCartaoPreSelecionado();
    contaCombobox?.sync();
    categoriaCombobox?.sync();
  };

  if (globalThis.GranaGoModal) {
    GranaGoModal.bind(overlay, {
      onClose: fecharModal,
      onEscape: () => {
        if (algumComboboxAberto()) {
          fecharComboboxes();
          return false;
        }
      },
    });
  }

  btnExcluirModal?.addEventListener("click", () => {
    const id = overlay.dataset.editando;
    if (!id) return;
    globalThis.GranaGoModal?.close(overlay);
    if (typeof window.solicitarExclusaoTransacao === "function") {
      window.solicitarExclusaoTransacao(id);
    }
  });

  let salvando = false;

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (salvando) return;
    salvando = true;
    const btnSalvar = document.getElementById("btn-salvar-transacao");
    if (btnSalvar) btnSalvar.disabled = true;
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
        globalThis.GranaGoModal?.close(overlay);
        window.location.reload();
        return;
      }

      salvando = false;
      if (btnSalvar) btnSalvar.disabled = false;

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
      salvando = false;
      if (btnSalvar) btnSalvar.disabled = false;
    }
  });

  selectTipo?.addEventListener("change", () => {
    const tipo = selectTipo.value || "despesa";
    popularCategorias(tipo);
    limparSugestaoCategoria();
  });

  inputDescricao?.addEventListener("input", () => {
    window.clearTimeout(sugestaoTimer);
    sugestaoTimer = window.setTimeout(buscarSugestaoCategoria, 350);
  });
});
