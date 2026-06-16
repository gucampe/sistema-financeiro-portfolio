(function () {
  const overlay = document.getElementById("overlay-modal-cartao");
  const btnAbrir = document.getElementById("btn-adicionar-cartao");
  const form = document.getElementById("form-modal-cartao");
  const selectContaPadrao = document.getElementById("cartao_conta_padrao");
  let contaPadraoCombobox = null;
  if (selectContaPadrao && typeof window.initIconCombobox === "function") {
    contaPadraoCombobox = window.initIconCombobox(selectContaPadrao, "account");
  }
  const rootContaPadrao = selectContaPadrao?.closest("[data-combobox-root]");
  const erroBox = document.getElementById("erro-modal-cartao");
  const inputCartaoId = document.getElementById("cartao_id");
  const inputIcone = document.getElementById("cartao_icone");
  const tituloModal = document.getElementById("titulo-modal-cartao");
  const toastEl = document.getElementById("toast-cartoes");
  const toastMsg = document.getElementById("toast-cartoes-msg");
  const toastClose = document.getElementById("toast-cartoes-close");
  let toastTimeout;

  function getCsrfToken() {
    const el = document.querySelector("[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  }

  function showToast(message, tipo) {
    if (!toastEl) return;
    toastEl.classList.remove("bg-green-600", "bg-red-600");
    toastEl.classList.add(tipo === "erro" ? "bg-red-600" : "bg-green-600");
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

  function resetModal() {
    if (!form) return;
    form.reset();
    contaPadraoCombobox?.sync();
    inputCartaoId.value = "";
    inputIcone.value = "bank";
    if (erroBox) erroBox.classList.add("hidden");
    if (tituloModal) tituloModal.textContent = "Novo Cartão";
    document.querySelectorAll(".item-icone-cartao").forEach((item) => {
      item.classList.remove("border-brand-500", "bg-brand-50");
      if (item.dataset.icone === "bank") item.classList.add("border-brand-500", "bg-brand-50");
    });
  }

  function abrirModal(cartao) {
    resetModal();
    if (cartao) {
      inputCartaoId.value = cartao.id;
      form.nome.value = cartao.nome || "";
      const limiteEl = document.getElementById("cartao_limite");
      if (limiteEl && window.MoedaInput) {
        window.MoedaInput.setValueFromDecimal(limiteEl, cartao.limite || "0");
      } else if (limiteEl) {
        limiteEl.value = cartao.limite || "";
      }
      form.dia_fechamento.value = cartao.diaFechamento || "";
      form.dia_vencimento.value = cartao.diaVencimento || "";
      if (selectContaPadrao) {
        selectContaPadrao.value = cartao.contaPadrao || "";
        contaPadraoCombobox?.sync();
      }
      inputIcone.value = cartao.icone || "bank";
      if (tituloModal) tituloModal.textContent = "Editar Cartão";
      document.querySelectorAll(".item-icone-cartao").forEach((item) => {
        item.classList.remove("border-brand-500", "bg-brand-50");
        if (item.dataset.icone === inputIcone.value) {
          item.classList.add("border-brand-500", "bg-brand-50");
        }
      });
    }
    globalThis.GranaGoModal?.open(overlay, { trigger: btnAbrir || undefined });
  }

  function fecharModal() {
    resetModal();
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

  if (overlay && globalThis.GranaGoModal) {
    GranaGoModal.bind(overlay, { onClose: fecharModal });
  }

  document.addEventListener("click", (event) => {
    if (rootContaPadrao && !rootContaPadrao.contains(event.target)) {
      contaPadraoCombobox?.close();
    }

    const itemIcone = event.target.closest(".item-icone-cartao");
    if (itemIcone) {
      inputIcone.value = itemIcone.dataset.icone || "bank";
      document.querySelectorAll(".item-icone-cartao").forEach((item) => {
        item.classList.remove("border-brand-500", "bg-brand-50");
      });
      itemIcone.classList.add("border-brand-500", "bg-brand-50");
      return;
    }

    const btnEditar = event.target.closest(".btn-editar-cartao");
    if (btnEditar) {
      abrirModal({
        id: btnEditar.dataset.id,
        nome: btnEditar.dataset.nome,
        icone: btnEditar.dataset.icone,
        limite: btnEditar.dataset.limite,
        diaFechamento: btnEditar.dataset.diaFechamento,
        diaVencimento: btnEditar.dataset.diaVencimento,
        contaPadrao: btnEditar.dataset.contaPadrao,
      });
      return;
    }

  });

  if (form) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (erroBox) erroBox.classList.add("hidden");
      const data = new FormData(form);
      data.set("csrfmiddlewaretoken", getCsrfToken());
      data.set("icone", inputIcone.value || "bank");

      try {
        const response = await fetch(form.action, {
          method: "POST",
          body: data,
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        const result = await response.json();
        if (result.status === "ok") {
          globalThis.GranaGoModal?.close(overlay);
          showToast(inputCartaoId.value ? "Cartão atualizado com sucesso!" : "Cartão criado com sucesso!");
          window.location.assign(window.location.pathname);
          return;
        }
        if (erroBox) {
          erroBox.textContent = result.errors || "Erro ao salvar cartão.";
          erroBox.classList.remove("hidden");
        } else {
          showToast(result.errors || "Erro ao salvar cartão.", "erro");
        }
      } catch (error) {
        if (erroBox) {
          erroBox.textContent = "Erro inesperado. Tente novamente.";
          erroBox.classList.remove("hidden");
        } else {
          showToast("Erro inesperado. Tente novamente.", "erro");
        }
      }
    });
  }
})();
