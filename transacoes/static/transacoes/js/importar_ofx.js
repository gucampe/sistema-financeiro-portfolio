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
  const tbody = document.getElementById("import-ofx-tbody");
  const errUpload = document.getElementById("import-ofx-erro-upload");
  const errPreview = document.getElementById("import-ofx-erro-preview");
  const loading = document.getElementById("import-ofx-loading");
  const formCsrf = document.getElementById("form-csrf-import-ofx");
  const panel = document.getElementById("import-ofx-panel");

  if (!overlay || !btnAbrir) return;

  const previewUrl = overlay.dataset.previewUrl;
  const confirmUrl = overlay.dataset.confirmUrl;

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
    panel?.classList.add("scale-95", "opacity-90");
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
      panel?.classList.remove("scale-95", "opacity-90");
      panel?.classList.add("scale-100", "opacity-100");
    });
  }

  function resetModal() {
    state = { contaId: null, categorias: null, chavePorTipo: null, linhas: [] };
    stepUpload?.classList.remove("hidden");
    stepPreview?.classList.add("hidden");
    if (inputArquivo) inputArquivo.value = "";
    if (tbody) tbody.innerHTML = "";
    showErrUpload("");
    showErrPreview("");
    showLoading(false);
    panel?.classList.remove("scale-100", "opacity-100");
    panel?.classList.add("scale-95", "opacity-90");
  }

  function irParaPreview() {
    stepUpload?.classList.add("hidden");
    stepPreview?.classList.remove("hidden");
  }

  function irParaUpload() {
    stepPreview?.classList.add("hidden");
    stepUpload?.classList.remove("hidden");
    showErrPreview("");
    if (tbody) tbody.innerHTML = "";
  }

  function labelTipo(t) {
    if (t === "receita") return "Receita";
    if (t === "despesa") return "Despesa";
    if (t === "ajuste") return "Ajuste";
    return t;
  }

  function formatarValor(str) {
    const n = Number.parseFloat(str);
    if (Number.isNaN(n)) return str;
    return n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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
      tdCheck.className = "px-2 py-2 align-top";
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.className = "import-ofx-incluir rounded border-gray-300";
      cb.checked = incluirDefault;
      cb.dataset.indice = String(linha.indice);
      tdCheck.appendChild(cb);

      const tdData = document.createElement("td");
      tdData.className = "px-2 py-2 align-top whitespace-nowrap text-gray-800";
      const [y, m, d] = linha.data.split("-");
      tdData.textContent = d && m && y ? `${d}/${m}/${y}` : linha.data;

      const tdDesc = document.createElement("td");
      tdDesc.className = "px-2 py-2 align-top text-gray-800 max-w-[12rem] truncate";
      tdDesc.title = linha.descricao;
      tdDesc.textContent = linha.descricao;

      const tdValor = document.createElement("td");
      tdValor.className =
        "px-2 py-2 align-top text-right font-medium whitespace-nowrap " +
        (linha.tipo === "despesa"
          ? "text-red-600"
          : linha.tipo === "receita"
            ? "text-emerald-600"
            : "text-gray-700");
      tdValor.textContent =
        (linha.tipo === "despesa" ? "-" : linha.tipo === "receita" ? "+" : "") +
        formatarValor(linha.valor);

      const tdTipo = document.createElement("td");
      tdTipo.className = "px-2 py-2 align-top text-gray-600";
      tdTipo.textContent = labelTipo(linha.tipo);

      const tdAvisos = document.createElement("td");
      tdAvisos.className = "px-2 py-2 align-top text-xs";
      const avisos = [];
      if (linha.duplicata_por_fitid) avisos.push("Possível dup. (FITID)");
      if (linha.duplicata_por_heuristica) avisos.push("Possível dup. (dados)");
      tdAvisos.innerHTML = avisos.length
        ? `<span class="text-amber-700">${avisos.join("<br>")}</span>`
        : "—";

      const tdCat = document.createElement("td");
      tdCat.className = "px-2 py-2 align-top min-w-[17rem] w-[17rem]";
      const sel = document.createElement("select");
      sel.className =
        "import-ofx-categoria w-full min-w-[15rem] max-w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500";
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
  }

  btnAbrir.addEventListener("click", () => abrirModal());

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !overlay.classList.contains("hidden")) fecharModal();
  });

  btnFechar?.addEventListener("click", fecharModal);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) fecharModal();
  });

  btnVoltar?.addEventListener("click", irParaUpload);

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
      const cb = tr.querySelector(".import-ofx-incluir");
      const sel = tr.querySelector(".import-ofx-categoria");
      if (!cb?.checked) continue;

      const catId = sel?.value;
      if (!catId) {
        showErrPreview("Selecione a categoria em todas as linhas marcadas.");
        return;
      }

      const linha = state.linhas.find((l) => String(l.indice) === indice);
      if (!linha) continue;

      linhasPayload.push({
        indice: linha.indice,
        data: linha.data,
        valor: linha.valor,
        tipo: linha.tipo,
        descricao: linha.descricao,
        categoria_id: Number(catId),
        ofx_fitid: linha.ofx_fitid,
      });
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
