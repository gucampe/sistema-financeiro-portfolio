(function () {
  var idTransacaoParaExcluir = null;

  function getCsrfToken() {
    var el = document.querySelector("[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  }

  function abrirModal() {
    var modal = document.getElementById("modal-confirmar-exclusao");
    if (modal) modal.classList.remove("hidden");
  }

  function fecharModal() {
    var modal = document.getElementById("modal-confirmar-exclusao");
    if (modal) modal.classList.add("hidden");
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

    if (e.target.id === "cancelar-exclusao") {
      e.preventDefault();
      fecharModal();
      return;
    }

    if (e.target.id === "confirmar-exclusao") {
      e.preventDefault();
      var id = idTransacaoParaExcluir;
      fecharModal();
      if (id) enviarExclusao(id);
    }
  });
})();
