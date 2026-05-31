(function () {
  var idTransacaoParaExcluir = null;

  function getCsrfToken() {
    var el = document.querySelector("[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  }

  function abrirModal() {
    globalThis.GranaGoModal?.open("modal-confirmar-exclusao");
  }

  function fecharModal() {
    idTransacaoParaExcluir = null;
  }

  function enviarExclusao(id) {
    if (!id) return;

    var form = document.createElement("form");
    form.method = "POST";
    form.action = "/transacoes/" + id + "/excluir/";

    var csrf = document.createElement("input");
    csrf.type = "hidden";
    csrf.name = "csrfmiddlewaretoken";
    csrf.value = getCsrfToken();

    form.appendChild(csrf);
    document.body.appendChild(form);
    form.submit();
  }

  window.solicitarExclusaoTransacao = function (id) {
    if (!id) return;
    idTransacaoParaExcluir = String(id);
    abrirModal();
  };

  var modalEl = document.getElementById("modal-confirmar-exclusao");
  if (modalEl && globalThis.GranaGoModal) {
    GranaGoModal.bind(modalEl, { onClose: fecharModal });
  }

  document.addEventListener("click", function (e) {
    var excluir = e.target.closest(".excluir-transacao");
    if (excluir) {
      e.preventDefault();
      e.stopPropagation();
      var id = excluir.getAttribute("data-id");
      if (!id) return;
      window.solicitarExclusaoTransacao(id);
      return;
    }

    if (e.target.id === "confirmar-exclusao") {
      e.preventDefault();
      var id = idTransacaoParaExcluir;
      globalThis.GranaGoModal?.close("modal-confirmar-exclusao");
      if (id) enviarExclusao(id);
    }
  });
})();
