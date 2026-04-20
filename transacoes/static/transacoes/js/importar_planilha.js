/**
 * Modal importação planilha: pré-visualização (multipart) + confirmação (JSON).
 */
document.addEventListener("DOMContentLoaded", () => {
  const btnAbrir = document.getElementById("btn-importar-planilha");
  const overlay = document.getElementById("overlay-importar-planilha");
  const btnFechar = document.getElementById("btn-fechar-import-planilha");
  const stepUpload = document.getElementById("import-planilha-step-upload");
  const stepPreview = document.getElementById("import-planilha-step-preview");
  const selectConta = document.getElementById("import-planilha-conta");
  const inputArquivo = document.getElementById("import-planilha-arquivo");
  const btnPreview = document.getElementById("btn-import-planilha-preview");
  const btnVoltar = document.getElementById("btn-import-planilha-voltar");
  const btnConfirmar = document.getElementById("btn-import-planilha-confirmar");
  const tbody = document.getElementById("import-planilha-tbody");
  const cbToggleAll = document.getElementById("import-planilha-toggle-all");
  const errUpload = document.getElementById("import-planilha-erro-upload");
  const errPreview = document.getElementById("import-planilha-erro-preview");
  const loading = document.getElementById("import-planilha-loading");
  const formCsrf = document.getElementById("form-csrf-import-planilha");
  const panel = document.getElementById("import-planilha-panel");

  if (!overlay) return;

  /* Overlay dentro de #mainContent herda largura “estreita” (viewport − sidebar); fixed + 100% nesse
     contexto estoura a página. Ancorar no body alinha largura ao viewport real. */
  if (overlay.parentNode !== document.body) {
    document.body.appendChild(overlay);
  }

  if (!btnAbrir) return;

  const previewUrl = overlay.dataset.previewUrl;
  const confirmUrl = overlay.dataset.confirmUrl;

  const rootImportConta = selectConta?.closest("[data-combobox-root]");
  let contaComboboxPlanilha = null;
  if (selectConta && typeof window.initIconCombobox === "function") {
    contaComboboxPlanilha = window.initIconCombobox(selectConta, "account");
  }

  document.addEventListener("click", (e) => {
    if (overlay.classList.contains("hidden")) return;
    if (rootImportConta?.contains(e.target)) return;
    contaComboboxPlanilha?.close();
  });

  let state = {
    contaId: null,
    categorias: null,
    chavePorTipo: null,
    linhas: [],
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
    contaComboboxPlanilha?.close();
    overlay.classList.add("opacity-0");
    setTimeout(() => {
      overlay.classList.add("hidden");
      resetModal();
    }, 300);
  }

  function abrirModal() {
    resetModal();
    overlay.classList.remove("hidden");
    requestAnimationFrame(() => {
      overlay.classList.remove("opacity-0");
    });
  }

  /** Tempo do fade “leave” antes da troca de passo (alinha ao opacity ~0,65s no CSS + folga). */
  const PLANILHA_FADE_MS = 700;
  let stepAnimTimer = null;

  function clearStepAnimTimer() {
    if (stepAnimTimer != null) {
      window.clearTimeout(stepAnimTimer);
      stepAnimTimer = null;
    }
  }

  function limparClassesPasso() {
    stepUpload?.classList.remove("import-planilha-step-leaving", "import-planilha-step-enter-from");
    stepPreview?.classList.remove("import-planilha-step-leaving", "import-planilha-step-enter-from");
  }

  function resetModal() {
    contaComboboxPlanilha?.close();
    clearStepAnimTimer();
    limparClassesPasso();
    if (panel) panel.dataset.planilhaStep = "upload";
    state = { contaId: null, categorias: null, chavePorTipo: null, linhas: [] };
    stepUpload?.classList.remove("hidden");
    stepPreview?.classList.add("hidden");
    if (inputArquivo) inputArquivo.value = "";
    if (tbody) tbody.innerHTML = "";
    if (cbToggleAll) {
      cbToggleAll.checked = false;
      cbToggleAll.indeterminate = false;
    }
    showErrUpload("");
    showErrPreview("");
    showLoading(false);
  }

  /** Crossfade + leve translateY; largura do painel em ~240ms (CSS). */
  function irParaPreview() {
    if (!stepUpload || !stepPreview || !panel) {
      stepUpload?.classList.add("hidden");
      stepPreview?.classList.remove("hidden");
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      limparClassesPasso();
      panel.dataset.planilhaStep = "preview";
      stepUpload.classList.add("hidden");
      stepPreview.classList.remove("hidden");
      return;
    }

    clearStepAnimTimer();
    limparClassesPasso();
    panel.dataset.planilhaStep = "preview";
    stepUpload.classList.add("import-planilha-step-leaving");

    stepAnimTimer = window.setTimeout(() => {
      stepAnimTimer = null;
      stepUpload.classList.remove("import-planilha-step-leaving");
      stepUpload.classList.add("hidden");
      stepPreview.classList.remove("hidden");
      stepPreview.classList.add("import-planilha-step-enter-from");
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          stepPreview.classList.remove("import-planilha-step-enter-from");
        });
      });
    }, PLANILHA_FADE_MS);
  }

  function irParaUpload() {
    if (!stepUpload || !stepPreview || !panel) {
      stepPreview?.classList.add("hidden");
      stepUpload?.classList.remove("hidden");
      showErrPreview("");
      if (tbody) tbody.innerHTML = "";
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      limparClassesPasso();
      panel.dataset.planilhaStep = "upload";
      stepPreview.classList.add("hidden");
      showErrPreview("");
      if (tbody) tbody.innerHTML = "";
      stepUpload.classList.remove("hidden");
      return;
    }

    clearStepAnimTimer();
    limparClassesPasso();
    stepPreview.classList.add("import-planilha-step-leaving");

    stepAnimTimer = window.setTimeout(() => {
      stepAnimTimer = null;
      stepPreview.classList.remove("import-planilha-step-leaving");
      stepPreview.classList.add("hidden");
      showErrPreview("");
      if (tbody) tbody.innerHTML = "";
      panel.dataset.planilhaStep = "upload";
      stepUpload.classList.remove("hidden");
      stepUpload.classList.add("import-planilha-step-enter-from");
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          stepUpload.classList.remove("import-planilha-step-enter-from");
        });
      });
    }, PLANILHA_FADE_MS);
  }

  function labelTipo(t) {
    if (t === "receita") return "Receita";
    if (t === "despesa") return "Despesa";
    if (t === "ajuste") return "Ajuste";
    return t;
  }

  const inputCellClass =
    "w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500";

  /** Normaliza string digitada (vírgula → ponto) e devolve número finito ou NaN. */
  function parseValorDigitado(raw) {
    if (raw === undefined || raw === null) return Number.NaN;
    const s = String(raw).trim().replace(/\s/g, "").replace(",", ".");
    if (s === "") return Number.NaN;
    return Number.parseFloat(s);
  }

  function atualizarEstadoToggleAll() {
    if (!cbToggleAll || !tbody) return;
    const checkboxes = [...tbody.querySelectorAll(".import-planilha-incluir")];
    if (!checkboxes.length) {
      cbToggleAll.checked = false;
      cbToggleAll.indeterminate = false;
      return;
    }
    const marcados = checkboxes.filter((cb) => cb.checked).length;
    cbToggleAll.checked = marcados === checkboxes.length;
    cbToggleAll.indeterminate = marcados > 0 && marcados < checkboxes.length;
  }

  function montarTabela(data) {
    if (!tbody) return;
    tbody.innerHTML = "";
    const cats = data.categorias || {};
    const chaves = data.categorias_chave_por_tipo_transacao || {};

    data.linhas.forEach((linha) => {
      const tr = document.createElement("tr");
      tr.className = "border-b border-gray-100 hover:bg-gray-50/80";
      tr.dataset.indice = String(linha.indice);

      const dup =
        linha.duplicata_por_fitid || linha.duplicata_por_heuristica;
      const incluirDefault = !dup;

      const chaveCat = chaves[linha.tipo] || linha.tipo;
      const listaCat = cats[chaveCat] || [];

      const tdCheck = document.createElement("td");
      tdCheck.className = "px-1.5 py-2 align-top min-w-0";
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.className = "import-planilha-incluir rounded border-gray-300";
      cb.checked = incluirDefault;
      cb.dataset.indice = String(linha.indice);
      tdCheck.appendChild(cb);

      const tdData = document.createElement("td");
      tdData.className = "px-2 py-2 align-top min-w-0";
      const inpData = document.createElement("input");
      inpData.type = "date";
      inpData.className = `import-planilha-data ${inputCellClass} min-w-0 max-w-full text-gray-800`;
      const iso = linha.data && String(linha.data).slice(0, 10);
      inpData.value = /^\d{4}-\d{2}-\d{2}$/.test(iso) ? iso : "";
      inpData.dataset.indice = String(linha.indice);
      tdData.appendChild(inpData);

      const tdDesc = document.createElement("td");
      tdDesc.className = "px-2 py-2 align-top min-w-0";
      const inpDesc = document.createElement("input");
      inpDesc.type = "text";
      inpDesc.className =
        "import-planilha-descricao w-full min-w-0 max-w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-emerald-500";
      inpDesc.value = linha.descricao ?? "";
      inpDesc.maxLength = 255;
      inpDesc.setAttribute("autocomplete", "off");
      inpDesc.dataset.indice = String(linha.indice);
      tdDesc.appendChild(inpDesc);

      const tdValor = document.createElement("td");
      tdValor.className =
        "px-2 py-2 align-top text-right font-medium min-w-0 " +
        (linha.tipo === "despesa"
          ? "text-red-600"
          : linha.tipo === "receita"
            ? "text-emerald-600"
            : "text-gray-700");
      const inpValor = document.createElement("input");
      inpValor.type = "number";
      inpValor.step = "any";
      inpValor.min = "0";
      inpValor.inputMode = "decimal";
      inpValor.className =
        "import-planilha-valor w-full min-w-0 max-w-full text-right font-medium " +
        inputCellClass +
        " " +
        (linha.tipo === "despesa"
          ? "text-red-600"
          : linha.tipo === "receita"
            ? "text-emerald-600"
            : "text-gray-700");
      inpValor.value =
        linha.valor != null && linha.valor !== "" ? String(linha.valor).trim() : "";
      inpValor.dataset.indice = String(linha.indice);
      tdValor.appendChild(inpValor);

      const tdTipo = document.createElement("td");
      tdTipo.className =
        "px-1 py-2 align-top min-w-0 break-words text-xs leading-tight text-gray-600";
      tdTipo.textContent = labelTipo(linha.tipo);

      const tdAvisos = document.createElement("td");
      tdAvisos.className = "px-2 py-2 align-top min-w-0 break-words text-xs";
      const avisos = [];
      if (linha.duplicata_por_heuristica) avisos.push("Possível dup. (dados)");
      tdAvisos.innerHTML = avisos.length
        ? `<span class="text-amber-700">${avisos.join("<br>")}</span>`
        : "—";

      const tdCat = document.createElement("td");
      tdCat.className = "px-2 py-2 align-top min-w-0";
      const sel = document.createElement("select");
      sel.className =
        "import-planilha-categoria w-full min-w-0 max-w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500";
      sel.dataset.indice = String(linha.indice);
      const opt0 = document.createElement("option");
      opt0.value = "";
      opt0.textContent = "Selecione…";
      sel.appendChild(opt0);
      listaCat.forEach((c) => {
        const opt = document.createElement("option");
        opt.value = String(c.id);
        opt.textContent = c.nome;
        sel.appendChild(opt);
      });
      if (listaCat.length === 1) {
        sel.value = String(listaCat[0].id);
      }
      tdCat.appendChild(sel);

      tr.append(tdCheck, tdData, tdDesc, tdValor, tdTipo, tdAvisos, tdCat);
      tbody.appendChild(tr);
    });
    atualizarEstadoToggleAll();
  }

  btnAbrir.addEventListener("click", () => abrirModal());

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !overlay.classList.contains("hidden")) fecharModal();
  });

  btnFechar?.addEventListener("click", fecharModal);
  overlay.addEventListener("click", (e) => {
    const t = e.target;
    if (!(t instanceof Element)) return;
    if (!t.closest("#import-planilha-panel")) fecharModal();
  });

  btnVoltar?.addEventListener("click", irParaUpload);

  cbToggleAll?.addEventListener("change", () => {
    if (!tbody) return;
    const marcar = cbToggleAll.checked;
    tbody.querySelectorAll(".import-planilha-incluir").forEach((cb) => {
      cb.checked = marcar;
    });
    cbToggleAll.indeterminate = false;
  });

  tbody?.addEventListener("change", (e) => {
    const alvo = e.target;
    if (!(alvo instanceof HTMLInputElement)) return;
    if (!alvo.classList.contains("import-planilha-incluir")) return;
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
      showErrUpload("Selecione um arquivo .xlsx.");
      return;
    }

    const fd = new FormData();
    fd.append("conta_id", contaId);
    fd.append("arquivo", file);

    btnPreview.disabled = true;
    showLoading(true);
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
        showErrUpload(data.message || `Erro ao ler o arquivo (${res.status}).`);
        return;
      }
      if (!data.linhas?.length) {
        showErrUpload("Nenhuma transação encontrada nesta planilha.");
        return;
      }
      state.contaId = Number(data.conta_id);
      state.categorias = data.categorias;
      state.chavePorTipo = data.categorias_chave_por_tipo_transacao;
      state.linhas = data.linhas;
      showLoading(false);
      montarTabela(data);
      irParaPreview();
    } catch {
      showErrUpload("Falha de rede. Tente novamente.");
    } finally {
      btnPreview.disabled = false;
      showLoading(false);
    }
  });

  btnConfirmar?.addEventListener("click", async () => {
    showErrPreview("");
    if (!state.contaId || !state.linhas.length) {
      showErrPreview("Nada para importar. Volte e pré-visualize novamente.");
      return;
    }

    const linhasPayload = [];
    const rows = tbody?.querySelectorAll("tr") || [];

    for (const tr of rows) {
      const indice = tr.dataset.indice;
      const cb = tr.querySelector(".import-planilha-incluir");
      const sel = tr.querySelector(".import-planilha-categoria");
      if (!cb?.checked) continue;

      const linha = state.linhas.find((l) => String(l.indice) === indice);
      if (!linha) continue;

      const inpDesc = tr.querySelector(".import-planilha-descricao");
      const descricao = (inpDesc instanceof HTMLInputElement ? inpDesc.value : linha.descricao ?? "")
        .trim();
      if (!descricao) {
        showErrPreview("Preencha a descrição em todas as linhas marcadas.");
        return;
      }

      const inpData = tr.querySelector(".import-planilha-data");
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

      const inpValor = tr.querySelector(".import-planilha-valor");
      const valorDigitado =
        inpValor instanceof HTMLInputElement ? inpValor.value : String(linha.valor ?? "");
      const valorNorm = valorDigitado.trim().replace(/\s/g, "").replace(",", ".");
      const vNum = parseValorDigitado(valorNorm);
      if (valorNorm === "" || Number.isNaN(vNum)) {
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
      linhasPayload.push(linhaPayload);
    }

    if (!linhasPayload.length) {
      showErrPreview("Marque pelo menos uma linha para importar.");
      return;
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
