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
  const modalIntro = overlay?.querySelector(".shrink-0 > p.text-sm");
  const btnExcluirModal = document.getElementById("btn-excluir-transacao-modal");
  const textoAjudaModal = document.getElementById("texto-ajuda-modal-transacao");
  const blocoTransferencia = document.getElementById("bloco-transferencia");
  const blocoContaCartao = document.getElementById("bloco-conta-cartao");
  const blocoCategoria = document.getElementById("bloco-categoria");
  const selectContaOrigem = document.getElementById("conta_origem");
  const selectContaDestino = document.getElementById("conta_destino");
  const inputTransferId = document.getElementById("transfer_id");
  const inputDescricao = document.getElementById("descricao");

  let contaCombobox = null;
  let categoriaCombobox = null;
  let contaOrigemCombobox = null;
  let contaDestinoCombobox = null;
  let tipoCombobox = null;

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
  if (selectTipo && initIconCombobox) tipoCombobox = initIconCombobox(selectTipo, "category");
  if (selectContaOrigem && initIconCombobox) {
    contaOrigemCombobox = initIconCombobox(selectContaOrigem, "account");
  }
  if (selectContaDestino && initIconCombobox) {
    contaDestinoCombobox = initIconCombobox(selectContaDestino, "account");
  }

  selectUnified?.addEventListener("change", () => {
    syncHiddensFromUnified();
  });

  aplicarCartaoPreSelecionado();
  contaCombobox?.sync();
  categoriaCombobox?.sync();
  tipoCombobox?.sync();
  contaOrigemCombobox?.sync();
  contaDestinoCombobox?.sync();

  const rootContaCartao = selectUnified?.closest("[data-combobox-root]");
  const rootCategoria = selectCategoria?.closest("[data-combobox-root]");
  const rootTipo = selectTipo?.closest("[data-combobox-root]");
  const rootContaOrigem = selectContaOrigem?.closest("[data-combobox-root]");
  const rootContaDestino = selectContaDestino?.closest("[data-combobox-root]");

  if (!overlay) return;

  function isTransferencia() {
    return (selectTipo?.value || "") === "transferencia";
  }

  function syncModoTransferencia() {
    const on = isTransferencia();
    blocoTransferencia?.classList.toggle("hidden", !on);
    blocoContaCartao?.classList.toggle("hidden", on);
    blocoCategoria?.classList.toggle("hidden", on);
    if (selectCategoria) {
      selectCategoria.required = !on;
      if (on) selectCategoria.value = "";
    }
    if (selectUnified) {
      selectUnified.required = !on;
    }
    if (selectContaOrigem) selectContaOrigem.required = on;
    if (selectContaDestino) selectContaDestino.required = on;
    if (!on && inputTransferId) inputTransferId.value = "";
    if (on && inputDescricao && !(inputDescricao.value || "").trim()) {
      inputDescricao.placeholder = "Transferência";
      inputDescricao.required = false;
    } else if (inputDescricao) {
      inputDescricao.placeholder = "";
      inputDescricao.required = true;
    }
    if (modalIntro) {
      modalIntro.textContent = on
        ? "Mova valor entre duas contas. O patrimônio total não muda."
        : "Adicione ou edite uma transação para controlar melhor suas finanças.";
    }
    if (textoAjudaModal) {
      textoAjudaModal.textContent = on
        ? "Editar ou excluir a transferência atualiza as duas contas juntas."
        : "Você pode editar ou excluir transações depois, quando quiser.";
    }
    if (btnExcluirModal) {
      btnExcluirModal.textContent = on ? "Excluir transferência" : "Excluir transação";
    }
    if (on) {
      contaOrigemCombobox?.sync();
      contaDestinoCombobox?.sync();
    } else {
      categoriaCombobox?.sync();
    }
  }

  function popularCategorias(tipo, selecionadaId = null) {
    if (!selectCategoria) return;
    if (tipo === "transferencia") {
      syncModoTransferencia();
      return;
    }
    fetch(`/categorias/listar-ativas/?tipo=${tipo === "ajuste" ? "receita" : tipo || "despesa"}`, {
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
    tipoCombobox?.close();
    contaOrigemCombobox?.close();
    contaDestinoCombobox?.close();
  }

  function clickDentroDeCombobox(target) {
    const roots = [
      rootContaCartao,
      rootCategoria,
      rootTipo,
      rootContaOrigem,
      rootContaDestino,
    ].filter(Boolean);
    if (roots.some((root) => root.contains(target))) return true;
    const floating = target?.closest?.(".combobox-list--floating, [data-combobox-list]");
    return !!floating;
  }

  document.addEventListener("click", (e) => {
    if (clickDentroDeCombobox(e.target)) {
      if (rootTipo?.contains(e.target)) {
        contaCombobox?.close();
        categoriaCombobox?.close();
        contaOrigemCombobox?.close();
        contaDestinoCombobox?.close();
      } else if (rootContaCartao?.contains(e.target)) {
        categoriaCombobox?.close();
        tipoCombobox?.close();
        contaOrigemCombobox?.close();
        contaDestinoCombobox?.close();
      } else if (rootCategoria?.contains(e.target)) {
        contaCombobox?.close();
        tipoCombobox?.close();
        contaOrigemCombobox?.close();
        contaDestinoCombobox?.close();
      } else if (rootContaOrigem?.contains(e.target)) {
        contaCombobox?.close();
        categoriaCombobox?.close();
        tipoCombobox?.close();
        contaDestinoCombobox?.close();
      } else if (rootContaDestino?.contains(e.target)) {
        contaCombobox?.close();
        categoriaCombobox?.close();
        tipoCombobox?.close();
        contaOrigemCombobox?.close();
      }
      return;
    }
    fecharComboboxes();
  });

  function algumComboboxAberto() {
    const roots = [
      rootContaCartao,
      rootCategoria,
      rootTipo,
      rootContaOrigem,
      rootContaDestino,
    ].filter(Boolean);
    return (
      roots.some((root) => {
        const list = root.querySelector("[data-combobox-list]");
        if (list && !list.classList.contains("hidden")) return true;
        return false;
      }) || !!document.querySelector(".combobox-list--floating:not(.hidden)")
    );
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
        if (modalHeader) {
          modalHeader.textContent =
            data.tipo === "transferencia" ? "Editar Transferência" : "Editar Transação";
        }
        selectTipo.value = data.tipo;
        tipoCombobox?.sync();
        const valorEl = document.getElementById("valor");
        if (valorEl && window.MoedaInput) {
          window.MoedaInput.setValueFromDecimal(valorEl, data.valor);
        } else if (valorEl) {
          valorEl.value = data.valor;
        }
        document.getElementById("descricao").value = data.descricao;
        document.getElementById("data").value = data.data;
        if (data.tipo === "transferencia") {
          if (inputTransferId) inputTransferId.value = data.transfer_id || "";
          if (selectContaOrigem && data.conta_origem) {
            selectContaOrigem.value = String(data.conta_origem.id);
          }
          if (selectContaDestino && data.conta_destino) {
            selectContaDestino.value = String(data.conta_destino.id);
          }
          syncModoTransferencia();
          contaOrigemCombobox?.sync();
          contaDestinoCombobox?.sync();
        } else {
          if (inputTransferId) inputTransferId.value = "";
          window.applyUnifiedContaCartaoParaEdicao?.(data);
          popularCategorias(data.tipo, data.categoria?.id);
          syncModoTransferencia();
        }
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
        titulo ||
        (tipoOverride === "receita"
          ? "Nova Receita"
          : tipoOverride === "despesa"
            ? "Nova Despesa"
            : tipoOverride === "transferencia"
              ? "Nova Transferência"
              : "Nova Transação");
    }
    const tipo = selectTipo?.value || "despesa";
    if (!tipo) return;
    limparErroContaAjax();
    if (inputTransferId) inputTransferId.value = "";
    popularCategorias(tipo);
    syncModoTransferencia();
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

  selectCategoria?.addEventListener("change", () => {
    const sugId = hidSugId?.value;
    if (sugId && selectCategoria?.value && String(selectCategoria.value) !== String(sugId)) {
      limparSugestaoCategoria();
    }
  });

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
    if (inputTransferId) inputTransferId.value = "";
    aplicarCartaoPreSelecionado();
    contaCombobox?.sync();
    categoriaCombobox?.sync();
    tipoCombobox?.sync();
    contaOrigemCombobox?.sync();
    contaDestinoCombobox?.sync();
    syncModoTransferencia();
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

  function mostrarErroFormulario(mensagem) {
    const erroContaEl = document.getElementById("erro-conta-ajax");
    if (!erroContaEl) return;
    erroContaEl.textContent = mensagem || "Não foi possível salvar.";
    erroContaEl.classList.remove("hidden");
  }

  function primeiraMensagemErro(errors) {
    if (!errors || typeof errors !== "object") return null;
    const preferidos = [
      "conta_destino",
      "conta_origem",
      "conta",
      "valor",
      "data",
      "descricao",
      "__all__",
    ];
    for (const key of preferidos) {
      const msgs = errors[key];
      if (Array.isArray(msgs) && msgs.length) return String(msgs[0]);
      if (typeof msgs === "string" && msgs) return msgs;
    }
    for (const msgs of Object.values(errors)) {
      if (Array.isArray(msgs) && msgs.length) return String(msgs[0]);
      if (typeof msgs === "string" && msgs) return msgs;
    }
    return null;
  }

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (salvando) return;
    salvando = true;
    const btnSalvar = document.getElementById("btn-salvar-transacao");
    if (btnSalvar) btnSalvar.disabled = true;
    limparErroContaAjax();
    syncHiddensFromUnified();
    const editandoId = overlay.dataset.editando;
    const transferencia = isTransferencia();
    const actionAttr = form.getAttribute("action") || "";
    let url;
    if (transferencia) {
      url = new URL("/transacoes/transferir/", window.location.origin).href;
    } else if (editandoId) {
      url = new URL(`/transacoes/${editandoId}/editar/`, window.location.origin).href;
    } else {
      url = new URL(actionAttr || "/transacoes/adicionar/", window.location.origin).href;
    }

    const formData = new FormData(form);
    if (transferencia) {
      // Evita validação de categoria/conta unificada no backend de transferência.
      formData.delete("categoria");
      formData.delete("conta");
      formData.delete("cartao");
      if (!(formData.get("descricao") || "").toString().trim()) {
        formData.set("descricao", "Transferência");
      }
    }
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
        salvando = false;
        if (btnSalvar) btnSalvar.disabled = false;
        mostrarErroFormulario(
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

      const msg =
        primeiraMensagemErro(data.errors) ||
        (!response.ok ? `Não foi possível salvar (HTTP ${response.status}).` : null) ||
        "Não foi possível salvar. Verifique os dados e tente de novo.";
      mostrarErroFormulario(msg);
    } catch (error) {
      console.error(error);
      salvando = false;
      if (btnSalvar) btnSalvar.disabled = false;
      mostrarErroFormulario("Erro de comunicação. Verifique a conexão e tente de novo.");
    }
  });

  selectTipo?.addEventListener("change", () => {
    const tipo = selectTipo.value || "despesa";
    popularCategorias(tipo);
    limparSugestaoCategoria();
    syncModoTransferencia();
    if (modalHeader && !overlay.dataset.editando) {
      modalHeader.textContent =
        tipo === "receita"
          ? "Nova Receita"
          : tipo === "despesa"
            ? "Nova Despesa"
            : tipo === "transferencia"
              ? "Nova Transferência"
              : tipo === "ajuste"
                ? "Novo Ajuste"
                : "Nova Transação";
    }
  });

  inputDescricao?.addEventListener("input", () => {
    window.clearTimeout(sugestaoTimer);
    sugestaoTimer = window.setTimeout(buscarSugestaoCategoria, 350);
  });
});
