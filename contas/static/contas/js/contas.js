(function () {
  const overlay = document.getElementById("overlay-modal-conta");
  const btnAbrir = document.getElementById("btn-adicionar-conta");
  const form = document.getElementById("form-modal-conta");
  const erroBox = document.getElementById("erro-modal-conta");
  const tituloModal = document.getElementById("titulo-modal-conta");
  const inputContaId = document.getElementById("conta_id");
  const listaAtivas = document.getElementById("lista-contas-ativas");
  const listaArquivadas = document.getElementById("lista-contas-arquivadas");
  const secaoArquivadas = document.getElementById("secao-contas-arquivadas");
  const emptyAtivas = document.getElementById("empty-contas-ativas");
  const grupoSaldoInicial = document.getElementById("grupo-saldo-inicial");
  const inputIcone = document.getElementById("conta_icone");
  const previewIconeImg = document.getElementById("preview-icone-conta-img");

  let contaEditandoArquivada = false;

  const toastEl = document.getElementById("toast-contas");
  const toastMsg = document.getElementById("toast-contas-msg");
  const toastClose = document.getElementById("toast-contas-close");
  const toastColors = { sucesso: "bg-green-600", erro: "bg-red-600" };
  let toastTimeout;

  function dadosContaDoItem(item) {
    if (!item?.dataset?.id) return null;
    return {
      id: item.dataset.id,
      nome: item.dataset.contaNome,
      tipo: item.dataset.contaTipo,
      saldo: item.dataset.contaSaldo,
      icone: item.dataset.contaIcone || "bank",
    };
  }

  function isContaArquivada(item) {
    return !!item?.closest("#lista-contas-arquivadas");
  }

  function submeterPostConta(url) {
    const postForm = document.createElement("form");
    postForm.method = "POST";
    postForm.action = url;
    const csrf = document.createElement("input");
    csrf.type = "hidden";
    csrf.name = "csrfmiddlewaretoken";
    csrf.value = getCsrfToken();
    postForm.appendChild(csrf);
    document.body.appendChild(postForm);
    postForm.submit();
  }

  function getCsrfToken() {
    const el = document.querySelector("[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  }

  function showToast(message, tipo) {
    if (!toastEl) return;
    toastEl.classList.remove("bg-green-600", "bg-red-600");
    toastEl.classList.add(tipo === "erro" ? toastColors.erro : toastColors.sucesso);
    if (toastMsg) toastMsg.textContent = message;
    toastEl.classList.remove("opacity-0", "pointer-events-none");
    toastEl.classList.add("opacity-100");
    clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => {
      toastEl.classList.remove("opacity-100");
      toastEl.classList.add("opacity-0", "pointer-events-none");
    }, 4000);
  }

  if (toastClose) {
    toastClose.addEventListener("click", () => {
      clearTimeout(toastTimeout);
      toastEl.classList.remove("opacity-100");
      toastEl.classList.add("opacity-0", "pointer-events-none");
    });
  }

  const overlayModalIcone = document.getElementById("overlay-modal-icone");
  const btnFecharModalIcone = document.getElementById("btn-fechar-modal-icone");
  const previewIconeWrapper = document.getElementById("preview-icone-conta-wrapper");

  function getPreviewIconeUrl(icone) {
    const slug = (icone || "bank").trim() || "bank";
    if (!form) return "";
    const instituicoes = (form.dataset.instituicoes || "").split(",").map((s) => s.trim()).filter(Boolean);
    const genericos = (form.dataset.genericos || "").split(",").map((s) => s.trim()).filter(Boolean);
    const baseInst = form.dataset.urlInstituicoes || "";
    const baseGen = form.dataset.urlGenericos || "";
    const filenameInst = slug === "inter" ? "intermedium" : slug;
    if (instituicoes.includes(slug)) return baseInst + filenameInst + ".png";
    if (genericos.includes(slug)) return baseGen + slug + ".svg";
    return baseGen + "bank.svg";
  }

  function selecionarIcone(icone) {
    if (!inputIcone) return;
    inputIcone.value = icone || "bank";
    if (previewIconeImg) {
      previewIconeImg.src = getPreviewIconeUrl(icone || "bank");
    }
    syncSelecionadoModalIcone();
  }

  function syncSelecionadoModalIcone() {
    const current = (inputIcone && inputIcone.value) ? inputIcone.value.trim() : "bank";
    document.querySelectorAll(".item-icone-conta").forEach((btn) => {
      if (btn.dataset.icone === current) {
        btn.classList.add("icone-selecionado");
      } else {
        btn.classList.remove("icone-selecionado");
      }
    });
  }

  function abrirModalIcone() {
    syncSelecionadoModalIcone();
    globalThis.GranaGoModal?.open(overlayModalIcone, {
      trigger: previewIconeWrapper || undefined,
    });
  }

  function fecharModalIcone() {
    /* cleanup opcional; visibilidade via GranaGoModal.close / defaultClose */
  }

  function abrirModal(conta, { arquivada = false } = {}) {
    if (erroBox) erroBox.classList.add("hidden");
    contaEditandoArquivada = arquivada;
    if (conta) {
      inputContaId.value = conta.id;
      document.getElementById("conta_nome").value = conta.nome || "";
      document.getElementById("conta_tipo").value = conta.tipo || "corrente";
      selecionarIcone(conta.icone);
      const saldoField = document.getElementById("conta_saldo_inicial");
      if (saldoField) {
        if (window.MoedaInput) window.MoedaInput.setValueFromDecimal(saldoField, "0");
        else saldoField.value = "0";
        saldoField.disabled = true;
      }
      if (grupoSaldoInicial) grupoSaldoInicial.classList.add("hidden");
      if (tituloModal) tituloModal.textContent = "Editar conta";
    } else {
      contaEditandoArquivada = false;
      inputContaId.value = "";
      form.reset();
      document.getElementById("conta_id").value = "";
      selecionarIcone("bank");
      const saldoField = document.getElementById("conta_saldo_inicial");
      if (saldoField) {
        if (window.MoedaInput) window.MoedaInput.setValueFromDecimal(saldoField, "0");
        else saldoField.value = "0";
        saldoField.disabled = false;
      }
      if (grupoSaldoInicial) grupoSaldoInicial.classList.remove("hidden");
      if (tituloModal) tituloModal.textContent = "Nova conta";
    }
    globalThis.GranaGoModal?.open(overlay, { trigger: btnAbrir || undefined });
  }

  function fecharModal() {
    if (erroBox) erroBox.classList.add("hidden");
    if (overlayModalIcone && globalThis.GranaGoModal?.isVisible(overlayModalIcone)) {
      globalThis.GranaGoModal.close(overlayModalIcone);
    }
    form.reset();
    inputContaId.value = "";
    contaEditandoArquivada = false;
    if (inputIcone) inputIcone.value = "bank";
    selecionarIcone("bank");
  }

  if (btnAbrir) btnAbrir.addEventListener("click", () => abrirModal(null));

  function consumirQueryNova() {
    try {
      const url = new URL(window.location.href);
      if (url.searchParams.get("nova") !== "1") return false;
      url.searchParams.delete("nova");
      window.history.replaceState({}, "", url.pathname + url.search + url.hash);
      return true;
    } catch {
      return false;
    }
  }

  if (consumirQueryNova() && btnAbrir) {
    requestAnimationFrame(() => btnAbrir.click());
  }

  if (previewIconeWrapper) {
    previewIconeWrapper.addEventListener("click", (e) => {
      e.preventDefault();
      abrirModalIcone();
    });
    previewIconeWrapper.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        abrirModalIcone();
      }
    });
  }
  if (globalThis.GranaGoModal) {
    GranaGoModal.bind(overlay, { onClose: fecharModal });
    if (overlayModalIcone) {
      GranaGoModal.bind(overlayModalIcone, { onClose: fecharModalIcone });
    }
  }

  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".item-icone-conta");
    if (btn) {
      e.preventDefault();
      selecionarIcone(btn.dataset.icone);
      globalThis.GranaGoModal?.close(overlayModalIcone);
    }
  });

  function getSalvarUrl() {
    return form ? form.action : "/contas/salvar/";
  }

  function formatCurrencyBr(value) {
    const num = Number(value);
    if (Number.isNaN(num)) return "R$ 0,00";
    return num.toLocaleString("pt-BR", {
      style: "currency",
      currency: "BRL",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function renderLiContent(result, isArquivada) {
    const salvarUrl = "/contas/" + result.id + "/arquivar/";
    const reativarUrl = "/contas/" + result.id + "/reativar/";
    const csrf = getCsrfToken();
    const acaoForm = isArquivada
      ? `<form method="post" action="${reativarUrl}" class="inline">\n<input type="hidden" name="csrfmiddlewaretoken" value="${csrf}">\n<button type="submit" class="px-3 py-1.5 rounded-lg border text-sm" style="border-color: rgba(46,204,113,.4); color:#2ECC71;">Reativar</button>\n</form>`
      : `<form method="post" action="${salvarUrl}" class="inline">\n<input type="hidden" name="csrfmiddlewaretoken" value="${csrf}">\n<button type="submit" class="px-3 py-1.5 rounded-lg border text-sm" style="border-color: rgba(245,158,11,.4); color:#F59E0B;">Arquivar</button>\n</form>`;
    const saldoStr = formatCurrencyBr(result.saldo);
    const icone = result.icone || "bank";
    return `<span class="conta-info">${escapeHtml(result.nome)} (${escapeHtml(result.tipo_display)}) — ${saldoStr}</span>
        <div class="flex items-center gap-2">
          <button type="button" class="btn-editar-conta px-3 py-1.5 rounded-lg border text-sm" style="border-color:#BDC3C7; color:#34495E;"
                  data-id="${result.id}" data-nome="${escapeHtml(result.nome)}" data-tipo="${result.tipo}" data-saldo="${escapeHtml(result.saldo)}" data-icone="${escapeHtml(icone)}">Editar</button>
          ${acaoForm}
        </div>`;
  }

  function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (erroBox) erroBox.classList.add("hidden");

      const data = new FormData(form);
      data.set("csrfmiddlewaretoken", getCsrfToken());

      try {
        const response = await fetch(getSalvarUrl(), {
          method: "POST",
          body: data,
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        const result = await response.json();

        if (result.status === "ok") {
          const editandoId = inputContaId.value ? String(inputContaId.value) : null;
          globalThis.GranaGoModal?.close(overlay);
          showToast(editandoId ? "Conta atualizada!" : "Conta criada!");
          window.location.assign(window.location.pathname);
        } else {
          if (erroBox) {
            erroBox.textContent = result.errors || "Erro ao salvar.";
            erroBox.classList.remove("hidden");
          } else {
            showToast(result.errors || "Erro ao salvar.", "erro");
          }
        }
      } catch (err) {
        console.error(err);
        if (erroBox) {
          erroBox.textContent = "Erro inesperado. Tente novamente.";
          erroBox.classList.remove("hidden");
        } else {
          showToast("Erro inesperado. Tente novamente.", "erro");
        }
      }
    });
  }

  if (globalThis.ListaContextual) {
    const contasRoot = document.querySelector(".page-shell .max-w-5xl") || document.querySelector(".page-shell");
    if (contasRoot) {
      ListaContextual.create({
        root: contasRoot,
      itemSelector: ".lista-contextual-item.conta-item",
      getPayload: (item) => ({ el: item, ...dadosContaDoItem(item) }),
      getTitulo: (item) => dadosContaDoItem(item)?.nome || "",
      getMeta: (item) => (isContaArquivada(item) ? "Conta arquivada" : ""),
      getActions: (item) => {
        if (isContaArquivada(item)) {
          return [
            {
              id: "reativar",
              label: "Reativar conta",
              icon: "fa-solid fa-rotate-left",
            },
          ];
        }
        return [
          {
            id: "editar",
            label: "Editar conta",
            icon: "fa-solid fa-pen-to-square",
          },
          {
            id: "arquivar",
            label: "Arquivar conta",
            icon: "fa-solid fa-archive",
          },
        ];
      },
      onAction: (actionId, _payload, item) => {
        const conta = dadosContaDoItem(item);
        if (!conta) return;
        if (actionId === "editar") {
          abrirModal(conta, { arquivada: isContaArquivada(item) });
        } else if (actionId === "arquivar") {
          submeterPostConta("/contas/" + conta.id + "/arquivar/");
        } else if (actionId === "reativar") {
          submeterPostConta("/contas/" + conta.id + "/reativar/");
        }
      },
    });
    }
  }
})();
