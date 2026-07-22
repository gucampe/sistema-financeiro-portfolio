(function () {
  var idTransacaoParaExcluir = null;
  var exclusaoEhTransferencia = false;

  function getCsrfToken() {
    var el = document.querySelector("[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  }

  function atualizarCopyExclusao(isTransferencia) {
    var titulo = document.getElementById("modal-exclusao-titulo");
    var texto = document.querySelector("#modal-confirmar-exclusao .modal-panel__body p");
    if (titulo) {
      titulo.textContent = isTransferencia ? "Excluir transferência" : "Excluir transação";
    }
    if (texto) {
      texto.textContent = isTransferencia
        ? "Tem certeza que deseja excluir esta transferência? As duas movimentações (origem e destino) serão removidas. Essa ação não pode ser desfeita."
        : "Tem certeza que deseja excluir esta transação? Essa ação não pode ser desfeita.";
    }
  }

  function abrirModal() {
    atualizarCopyExclusao(exclusaoEhTransferencia);
    globalThis.GranaGoModal?.open("modal-confirmar-exclusao");
  }

  function fecharModal() {
    idTransacaoParaExcluir = null;
    exclusaoEhTransferencia = false;
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

  window.solicitarExclusaoTransacao = function (id, opts) {
    if (!id) return;
    idTransacaoParaExcluir = String(id);
    exclusaoEhTransferencia = !!(opts && opts.transferencia);
    if (!opts || opts.transferencia == null) {
      var row = document.querySelector(
        '.lista-contextual-item[data-transacao-id="' + CSS.escape(String(id)) + '"]'
      );
      exclusaoEhTransferencia = row?.dataset?.transacaoTipo === "transferencia";
    }
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
      var idExcluir = idTransacaoParaExcluir;
      globalThis.GranaGoModal?.close("modal-confirmar-exclusao");
      if (idExcluir) enviarExclusao(idExcluir);
    }
  });
})();
