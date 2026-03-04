(function () {
  const overlay = document.getElementById("overlay-modal-conta");
  const btnAbrir = document.getElementById("btn-adicionar-conta");
  const btnFechar = document.getElementById("btn-fechar-modal-conta");
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
  const gridIcones = document.getElementById("grid-icones-conta");

  const toastEl = document.getElementById("toast-contas");
  const toastMsg = document.getElementById("toast-contas-msg");
  const toastClose = document.getElementById("toast-contas-close");
  const toastColors = { sucesso: "bg-green-600", erro: "bg-red-600" };
  let toastTimeout;

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

  function selecionarIcone(icone) {
    if (!inputIcone) return;
    inputIcone.value = icone || "bank";
    if (gridIcones) {
      gridIcones.querySelectorAll(".btn-icone-conta").forEach((btn) => {
        if (btn.dataset.icone === (icone || "bank")) {
          btn.classList.add("icone-selecionado");
        } else {
          btn.classList.remove("icone-selecionado");
        }
      });
    }
  }

  function abrirModal(conta) {
    if (erroBox) erroBox.classList.add("hidden");
    if (conta) {
      inputContaId.value = conta.id;
      document.getElementById("conta_nome").value = conta.nome || "";
      document.getElementById("conta_tipo").value = conta.tipo || "corrente";
      selecionarIcone(conta.icone);
      const saldoField = document.getElementById("conta_saldo_inicial");
      if (saldoField) {
        saldoField.value = "0";
        saldoField.disabled = true;
      }
      if (grupoSaldoInicial) grupoSaldoInicial.classList.add("hidden");
      if (tituloModal) tituloModal.textContent = "Editar conta";
    } else {
      inputContaId.value = "";
      form.reset();
      document.getElementById("conta_id").value = "";
      selecionarIcone("bank");
      const saldoField = document.getElementById("conta_saldo_inicial");
      if (saldoField) {
        saldoField.value = "0";
        saldoField.disabled = false;
      }
      if (grupoSaldoInicial) grupoSaldoInicial.classList.remove("hidden");
      if (tituloModal) tituloModal.textContent = "Nova conta";
    }
    overlay.classList.remove("hidden", "opacity-0");
    overlay.classList.add("opacity-100");
  }

  function fecharModal() {
    overlay.classList.add("hidden");
    form.reset();
    inputContaId.value = "";
    if (inputIcone) inputIcone.value = "bank";
    selecionarIcone("bank");
  }

  if (btnAbrir) btnAbrir.addEventListener("click", () => abrirModal(null));
  if (btnFechar) btnFechar.addEventListener("click", fecharModal);

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
          fecharModal();
          showToast(editandoId ? "Conta atualizada!" : "Conta criada!");
          window.location.reload();
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

  if (gridIcones) {
    gridIcones.addEventListener("click", (e) => {
      const btn = e.target.closest(".btn-icone-conta");
      if (btn) {
        e.preventDefault();
        selecionarIcone(btn.dataset.icone);
      }
    });
  }

  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".btn-editar-conta");
    if (btn) {
      e.preventDefault();
      abrirModal({
        id: btn.dataset.id,
        nome: btn.dataset.nome,
        tipo: btn.dataset.tipo,
        saldo: btn.dataset.saldo,
        icone: btn.dataset.icone,
      });
    }
  });
})();
