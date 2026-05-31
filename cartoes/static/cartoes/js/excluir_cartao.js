(function () {
  var idCartaoParaExcluir = null;

  function getCsrfToken() {
    var el = document.querySelector("[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  }

  function showToast(message, tipo) {
    var toastEl = document.getElementById("toast-cartoes");
    var toastMsg = document.getElementById("toast-cartoes-msg");
    if (!toastEl || !toastMsg) return;
    toastEl.classList.remove("bg-green-600", "bg-red-600");
    toastEl.classList.add(tipo === "erro" ? "bg-red-600" : "bg-green-600");
    toastMsg.textContent = message;
    toastEl.classList.remove("opacity-0", "pointer-events-none");
    toastEl.classList.add("opacity-100", "pointer-events-auto");
    window.clearTimeout(showToast._timeout);
    showToast._timeout = window.setTimeout(function () {
      toastEl.classList.add("opacity-0", "pointer-events-none");
      toastEl.classList.remove("opacity-100", "pointer-events-auto");
    }, 4000);
  }

  function abrirModal() {
    globalThis.GranaGoModal?.open("modal-confirmar-exclusao-cartao");
  }

  function fecharModal() {
    idCartaoParaExcluir = null;
  }

  function enviarExclusao(id) {
    if (!id) return;

    fetch("/cartoes/" + id + "/excluir/", {
      method: "POST",
      headers: {
        "X-CSRFToken": getCsrfToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then(function (response) {
        return response.json();
      })
      .then(function (result) {
        if (result.status === "ok") {
          showToast("Cartão excluído com sucesso!");
          window.location.reload();
        } else {
          showToast(result.errors || "Erro ao excluir cartão.", "erro");
        }
      })
      .catch(function () {
        showToast("Erro inesperado. Tente novamente.", "erro");
      });
  }

  window.solicitarExclusaoCartao = function (id) {
    if (!id) return;
    idCartaoParaExcluir = String(id);
    abrirModal();
  };

  var modalEl = document.getElementById("modal-confirmar-exclusao-cartao");
  if (modalEl && globalThis.GranaGoModal) {
    GranaGoModal.bind(modalEl, { onClose: fecharModal });
  }

  document.addEventListener("click", function (e) {
    var excluir = e.target.closest(".btn-excluir-cartao");
    if (excluir) {
      e.preventDefault();
      e.stopPropagation();
      var id = excluir.getAttribute("data-id");
      if (!id) return;
      window.solicitarExclusaoCartao(id);
      return;
    }

    if (e.target.id === "confirmar-exclusao-cartao") {
      e.preventDefault();
      var id = idCartaoParaExcluir;
      globalThis.GranaGoModal?.close("modal-confirmar-exclusao-cartao");
      if (id) enviarExclusao(id);
    }
  });
})();
