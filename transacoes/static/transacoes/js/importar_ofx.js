/**
 * Modal importação OFX: pré-visualização (multipart) + confirmação (JSON).
 */
document.addEventListener("DOMContentLoaded", () => {
  const btnAbrir = document.getElementById("btn-importar-ofx");
  const overlay = document.getElementById("overlay-importar-ofx");
  const btnFechar = document.getElementById("btn-fechar-import-ofx");
  const stepUpload = document.getElementById("import-ofx-step-upload");
  const stepPreview = document.getElementById("import-ofx-step-preview");
  const selectConta = document.getElementById("import-ofx-conta");
  const inputArquivo = document.getElementById("import-ofx-arquivo");
  const btnPreview = document.getElementById("btn-import-ofx-preview");
  const btnVoltar = document.getElementById("btn-import-ofx-voltar");
  const btnConfirmar = document.getElementById("btn-import-ofx-confirmar");
  const feedContainer = document.getElementById("import-ofx-feed");
  const stickyToolbar = document.getElementById("import-ofx-sticky-toolbar");
  const cbToggleAll = document.getElementById("import-ofx-toggle-all");
  const errUpload = document.getElementById("import-ofx-erro-upload");
  const errPreview = document.getElementById("import-ofx-erro-preview");
  const loading = document.getElementById("import-ofx-loading");
  const formCsrf = document.getElementById("form-csrf-import-ofx");
  const panel = document.getElementById("import-ofx-panel");
  const stepLoading = document.getElementById("import-ofx-step-loading");
  const loadingMsg = document.getElementById("import-ofx-loading-msg");
  const btnPreviewWrap = btnPreview?.closest(".import-preview-btn-wrap");
  const btnCategorizar = document.getElementById("btn-import-ofx-categorizar-ia");
  const catProcessing = document.getElementById("import-ofx-cat-processing");
  const catMsg = document.getElementById("import-ofx-cat-msg");
  const catMicro = document.getElementById("import-ofx-cat-micro");

  if (!overlay) return;

  /* Overlay dentro de #mainContent herda largura “estreita” (viewport − sidebar); fixed + 100% nesse
     contexto estoura a página. Ancorar no body alinha largura ao viewport real. */
  if (overlay.parentNode !== document.body) {
    document.body.appendChild(overlay);
  }

  if (!btnAbrir) return;

  const previewUrl = overlay.dataset.previewUrl;
  const confirmUrl = overlay.dataset.confirmUrl;
  const categorizarUrl = overlay.dataset.categorizarUrl;
  const categorizarCancelUrl = overlay.dataset.categorizarCancelUrl;

  let catAbort = null;

  const rootImportConta = selectConta?.closest("[data-combobox-root]");
  let contaComboboxOfx = null;
  if (selectConta && typeof window.initIconCombobox === "function") {
    contaComboboxOfx = window.initIconCombobox(selectConta, "account");
  }

  document.addEventListener("click", (e) => {
    if (overlay.classList.contains("hidden")) return;
    if (rootImportConta?.contains(e.target)) return;
    if (
      e.target instanceof Element &&
      e.target.closest("[data-combobox-list].combobox-list--floating")
    ) {
      return;
    }
    contaComboboxOfx?.close();
  });

  let state = {
    contaId: null,
    categorias: null,
    chavePorTipo: null,
    linhas: [],
    categorizado: false,
  };

  function csrfToken() {
    return formCsrf?.querySelector('input[name="csrfmiddlewaretoken"]')?.value || "";
  }

  function showLoading(on) {
    loading?.classList.toggle("hidden", !on);
  }

  function showErrUpload(msg) {
    if (!errUpload) return;
    if (msg) {
      errUpload.textContent = msg;
      errUpload.classList.remove("hidden");
    } else {
      errUpload.textContent = "";
      errUpload.classList.add("hidden");
    }
  }

  function showErrPreview(msg) {
    if (!errPreview) return;
    if (msg) {
      errPreview.textContent = msg;
      errPreview.classList.remove("hidden");
    } else {
      errPreview.textContent = "";
      errPreview.classList.add("hidden");
    }
  }

  function fecharModal() {
    contaComboboxOfx?.close();
    resetModal();
  }

  function abrirModal() {
    resetModal();
    globalThis.GranaGoModal?.open(overlay, { trigger: btnAbrir });
  }

  /** Tempo do fade “leave” antes da troca de passo (alinha ao opacity ~0,65s no CSS + folga). */
  const OFX_FADE_MS = 700;
  const UPLOAD_LEAVE_MS = 320;
  let stepAnimTimer = null;

  function clearStepAnimTimer() {
    if (stepAnimTimer != null) {
      window.clearTimeout(stepAnimTimer);
      stepAnimTimer = null;
    }
  }

  function limparClassesPasso() {
    stepUpload?.classList.remove("import-ofx-step-leaving", "import-ofx-step-enter-from", "import-upload--leaving");
    stepPreview?.classList.remove("import-ofx-step-leaving", "import-ofx-step-enter-from");
    btnPreviewWrap?.classList.remove("is-hidden");
    if (btnPreview) btnPreview.disabled = false;
  }

  function beginPreviewLoading(message = "Lendo seu extrato…") {
    btnPreview.disabled = true;
    btnPreviewWrap?.classList.add("is-hidden");
    stepUpload?.classList.add("import-upload--leaving");
    if (loadingMsg) loadingMsg.textContent = message;

    return new Promise((resolve) => {
      window.setTimeout(() => {
        stepUpload?.classList.add("hidden");
        stepUpload?.classList.remove("import-upload--leaving");
        if (panel) panel.dataset.ofxStep = "preview";
        stepLoading?.classList.remove("hidden");
        resolve();
      }, UPLOAD_LEAVE_MS);
    });
  }

  function cancelPreviewLoading() {
    stepLoading?.classList.add("hidden");
    if (panel) panel.dataset.ofxStep = "upload";
    stepUpload?.classList.remove("hidden", "import-upload--leaving");
    btnPreviewWrap?.classList.remove("is-hidden");
    if (btnPreview) btnPreview.disabled = false;
  }

  function resetModal() {
    contaComboboxOfx?.close();
    clearStepAnimTimer();
    limparClassesPasso();
    if (panel) panel.dataset.ofxStep = "upload";
    state = { contaId: null, categorias: null, chavePorTipo: null, linhas: [], categorizado: false };
    stepUpload?.classList.remove("hidden");
    stepLoading?.classList.add("hidden");
    stepPreview?.classList.add("hidden");
    if (inputArquivo) inputArquivo.value = "";
    if (feedContainer) feedContainer.innerHTML = "";
    stickyToolbar?.classList.add("hidden");
    if (stickyToolbar) stickyToolbar.hidden = true;
    if (catAbort) {
      catAbort.abort();
      catAbort = null;
    }
    window.CategorizacaoImportWow?.hideOverlay(catProcessing);
    if (cbToggleAll) {
      cbToggleAll.checked = false;
      cbToggleAll.indeterminate = false;
    }
    showErrUpload("");
    showErrPreview("");
    showLoading(false);
  }

  /** Crossfade no passo preview (upload já foi substituído pelo loading). */
  function irParaPreview() {
    if (!stepPreview || !panel) {
      stepPreview?.classList.remove("hidden");
      return;
    }
    clearStepAnimTimer();
    limparClassesPasso();
    stepLoading?.classList.add("hidden");
    if (panel) panel.dataset.ofxStep = "preview";
    stepUpload?.classList.add("hidden");
    stepPreview.classList.remove("hidden");

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }

    stepPreview.classList.add("import-ofx-step-enter-from");
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        stepPreview.classList.remove("import-ofx-step-enter-from");
      });
    });
  }

  function irParaUpload() {
    if (catAbort) {
      catAbort.abort();
      catAbort = null;
    }
    window.CategorizacaoImportWow?.hideOverlay(catProcessing);
    stepLoading?.classList.add("hidden");
    if (!stepUpload || !stepPreview || !panel) {
      stepPreview?.classList.add("hidden");
      stepUpload?.classList.remove("hidden");
      showErrPreview("");
      if (feedContainer) feedContainer.innerHTML = "";
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      limparClassesPasso();
      panel.dataset.ofxStep = "upload";
      stepPreview.classList.add("hidden");
      showErrPreview("");
      if (feedContainer) feedContainer.innerHTML = "";
      stepUpload.classList.remove("hidden");
      return;
    }

    clearStepAnimTimer();
    limparClassesPasso();
    stepPreview.classList.add("import-ofx-step-leaving");

    stepAnimTimer = window.setTimeout(() => {
      stepAnimTimer = null;
      stepPreview.classList.remove("import-ofx-step-leaving");
      stepPreview.classList.add("hidden");
      showErrPreview("");
      if (feedContainer) feedContainer.innerHTML = "";
      panel.dataset.ofxStep = "upload";
      stepUpload.classList.remove("hidden");
      stepUpload.classList.add("import-ofx-step-enter-from");
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          stepUpload.classList.remove("import-ofx-step-enter-from");
        });
      });
    }, OFX_FADE_MS);
  }

  function labelTipo(t) {
    if (t === "receita") return "Receita";
    if (t === "despesa") return "Despesa";
    if (t === "ajuste") return "Ajuste";
    return t;
  }

  function parseValorDigitado(raw) {
    if (raw instanceof HTMLInputElement) {
      const dec =
        window.MoedaInput && typeof window.MoedaInput.parseToDecimalString === "function"
          ? window.MoedaInput.parseToDecimalString(raw)
          : "0.00";
      const n = Number.parseFloat(dec);
      return n <= 0 ? Number.NaN : n;
    }
    if (!String(raw || "").replace(/\D/g, "")) return Number.NaN;
    const dec =
      window.MoedaInput && typeof window.MoedaInput.parseToDecimalString === "function"
        ? window.MoedaInput.parseToDecimalString(raw)
        : String(raw).trim().replace(/\s/g, "").replace(",", ".");
    const n = Number.parseFloat(dec);
    return Number.isNaN(n) ? Number.NaN : n;
  }

  function valorParaBackend(raw) {
    if (
      raw instanceof HTMLInputElement &&
      window.MoedaInput &&
      typeof window.MoedaInput.parseToDecimalString === "function"
    ) {
      return window.MoedaInput.parseToDecimalString(raw);
    }
    if (window.MoedaInput && typeof window.MoedaInput.parseToDecimalString === "function") {
      return window.MoedaInput.parseToDecimalString(raw);
    }
    return String(raw || "")
      .trim()
      .replace(/\s/g, "")
      .replace(",", ".");
  }

  const PREFIX = "import-ofx";

  function atualizarToolbarFeed(categorizado = false) {
    if (!stickyToolbar || !state.linhas.length) return;
    const stats = window.ImportFeedUI?.calcularStatsLinhas(state.linhas) || {};
    window.ImportFeedUI?.atualizarToolbar(stickyToolbar, {
      total: state.linhas.length,
      categorizadas: stats.categorizadas,
      aprendidas: stats.aprendidas,
      categorizado: categorizado || state.categorizado,
    });
  }

  function atualizarEstadoToggleAll() {
    if (!cbToggleAll || !feedContainer) return;
    const checkboxes = [...feedContainer.querySelectorAll(`.${PREFIX}-incluir`)];
    if (!checkboxes.length) {
      cbToggleAll.checked = false;
      cbToggleAll.indeterminate = false;
      return;
    }
    const marcados = checkboxes.filter((cb) => cb.checked).length;
    cbToggleAll.checked = marcados === checkboxes.length;
    cbToggleAll.indeterminate = marcados > 0 && marcados < checkboxes.length;
    atualizarToolbarFeed(state.categorizado);
  }

  function montarTabela(data) {
    if (!feedContainer) return;
    window.ImportFeedUI?.montarFeed({
      container: feedContainer,
      data,
      prefix: PREFIX,
      labelTipoFn: labelTipo,
    });
    state.categorizado = false;
    atualizarToolbarFeed(false);
    atualizarEstadoToggleAll();
  }

  function linhasParaCategorizacao() {
    return (
      window.ImportFeedUI?.coletarLinhasParaCategorizacao(feedContainer, state.linhas, PREFIX) || []
    );
  }

  btnCategorizar?.addEventListener("click", async () => {
    if (!categorizarUrl || !state.linhas.length) return;
    showErrPreview("");
    const linhasPayload = linhasParaCategorizacao();
    if (!linhasPayload.length) return;

    catAbort = new AbortController();
    btnCategorizar.disabled = true;
    btnConfirmar.disabled = true;

    try {
      const data = await window.CategorizacaoImportWow.categorizarBatch({
        url: categorizarUrl,
        cancelUrl: categorizarCancelUrl,
        csrfToken: csrfToken(),
        linhas: linhasPayload,
        contexto: "import_ofx",
        overlayEl: catProcessing,
        msgEl: catMsg,
        microEl: catMicro,
        signal: catAbort.signal,
      });

      const porIndice = new Map((data.linhas || []).map((l) => [String(l.indice), l]));
      state.linhas = state.linhas.map((l) => ({ ...l, ...(porIndice.get(String(l.indice)) || {}) }));

      await window.CategorizacaoImportWow.revelarSugestoes({
        container: feedContainer,
        linhasAtualizadas: data.linhas,
        selectClass: ".import-ofx-categoria",
      });

      state.categorizado = true;
      atualizarToolbarFeed(true);
    } catch (err) {
      if (err?.name !== "AbortError") {
        showErrPreview(err?.message || "Não foi possível categorizar. Tente novamente.");
      }
    } finally {
      btnConfirmar.disabled = false;
      btnCategorizar.disabled = !state.categorizado;
      catAbort = null;
    }
  });

  btnAbrir.addEventListener("click", () => abrirModal());

  if (globalThis.GranaGoModal) {
    GranaGoModal.bind(overlay, { onClose: fecharModal });
  }

  btnVoltar?.addEventListener("click", irParaUpload);

  cbToggleAll?.addEventListener("change", () => {
    if (!feedContainer) return;
    const marcar = cbToggleAll.checked;
    feedContainer.querySelectorAll(`.${PREFIX}-incluir`).forEach((cb) => {
      cb.checked = marcar;
    });
    cbToggleAll.indeterminate = false;
    atualizarToolbarFeed(state.categorizado);
  });

  feedContainer?.addEventListener("change", (e) => {
    const alvo = e.target;
    if (!(alvo instanceof HTMLInputElement)) return;
    if (!alvo.classList.contains(`${PREFIX}-incluir`)) return;
    atualizarEstadoToggleAll();
  });

  btnPreview?.addEventListener("click", async () => {
    showErrUpload("");
    const contaId = selectConta?.value;
    const file = inputArquivo?.files?.[0];
    if (!contaId) {
      showErrUpload("Selecione a conta.");
      return;
    }
    if (!file) {
      showErrUpload("Selecione um arquivo OFX.");
      return;
    }

    const fd = new FormData();
    fd.append("conta_id", contaId);
    fd.append("arquivo", file);

    await beginPreviewLoading("Lendo seu extrato…");
    try {
      const res = await fetch(previewUrl, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrfToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: fd,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.status !== "ok") {
        cancelPreviewLoading();
        showErrUpload(data.message || `Erro ao ler o arquivo (${res.status}).`);
        return;
      }
      if (!data.linhas?.length) {
        cancelPreviewLoading();
        showErrUpload("Nenhuma transação encontrada neste OFX.");
        return;
      }
      state.contaId = Number(data.conta_id);
      state.categorias = data.categorias;
      state.chavePorTipo = data.categorias_chave_por_tipo_transacao;
      state.linhas = data.linhas;
      montarTabela(data);
      irParaPreview();
    } catch {
      cancelPreviewLoading();
      showErrUpload("Falha de rede. Tente novamente.");
    }
  });

  btnConfirmar?.addEventListener("click", async () => {
    showErrPreview("");
    if (!state.contaId || !state.linhas.length) {
      showErrPreview("Nada para importar. Volte e pré-visualize novamente.");
      return;
    }

    const linhasPayload = [];
    const rows = window.ImportFeedUI?.getItems(feedContainer) || [];

    for (const item of rows) {
      const indice = item.dataset.indice;
      const cb = item.querySelector(`.${PREFIX}-incluir`);
      const sel = item.querySelector(`.${PREFIX}-categoria`);
      if (!cb?.checked) continue;

      const linha = state.linhas.find((l) => String(l.indice) === indice);
      if (!linha) continue;

      const inpDesc = item.querySelector(`.${PREFIX}-descricao`);
      const descricao = (inpDesc instanceof HTMLInputElement ? inpDesc.value : linha.descricao ?? "")
        .trim();
      if (!descricao) {
        showErrPreview("Preencha a descrição em todas as linhas marcadas.");
        return;
      }

      const inpData = item.querySelector(`.${PREFIX}-data`);
      const dataStr =
        inpData instanceof HTMLInputElement ? inpData.value.trim() : String(linha.data || "").slice(0, 10);
      if (!dataStr) {
        showErrPreview("Preencha a data em todas as linhas marcadas.");
        return;
      }
      if (!/^\d{4}-\d{2}-\d{2}$/.test(dataStr)) {
        showErrPreview("Use uma data válida em todas as linhas marcadas.");
        return;
      }

      const inpValor = item.querySelector(`.${PREFIX}-valor`);
      const valorDigitado =
        inpValor instanceof HTMLInputElement ? inpValor : String(linha.valor ?? "");
      const valorNorm = valorParaBackend(valorDigitado);
      const vNum = parseValorDigitado(valorDigitado);
      if (Number.isNaN(vNum)) {
        showErrPreview("Preencha um valor numérico válido em todas as linhas marcadas.");
        return;
      }
      if (vNum < 0) {
        showErrPreview("O valor não pode ser negativo.");
        return;
      }

      const linhaPayload = {
        indice: linha.indice,
        data: dataStr,
        valor: valorNorm,
        tipo: linha.tipo,
        descricao,
        ofx_fitid: linha.ofx_fitid,
      };
      const catId = sel?.value?.trim();
      if (catId) linhaPayload.categoria_id = Number(catId);
      Object.assign(linhaPayload, window.CategorizacaoImport?.metadadosSugestaoFromSelect(sel) || {});
      linhasPayload.push(linhaPayload);
    }

    if (!linhasPayload.length) {
      showErrPreview("Marque pelo menos uma linha para importar.");
      return;
    }

    const revisao = window.ImportFeedUI?.analisarRevisaoPendente(feedContainer, PREFIX);
    if (revisao?.needsConfirm) {
      const prosseguir = await window.ImportFeedUI.solicitarConfirmacaoRevisao(revisao);
      if (!prosseguir) return;
    }

    btnConfirmar.disabled = true;
    showLoading(true);
    try {
      const res = await fetch(confirmUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({
          conta_id: state.contaId,
          linhas: linhasPayload,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.status !== "ok") {
        if (data.erros && typeof data.erros === "object") {
          const primeiro = Object.entries(data.erros)[0];
          const detalhe = primeiro
            ? ` (linha ${primeiro[0]}: ${JSON.stringify(primeiro[1])})`
            : "";
          showErrPreview((data.message || "Erro de validação.") + detalhe);
        } else {
          showErrPreview(data.message || `Erro ao importar (${res.status}).`);
        }
        return;
      }
      window.location.reload();
    } catch {
      showErrPreview("Falha de rede. Tente novamente.");
    } finally {
      btnConfirmar.disabled = false;
      showLoading(false);
    }
  });
});
