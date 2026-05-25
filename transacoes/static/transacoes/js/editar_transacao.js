document.addEventListener("click", function (e) {
  const editar = e.target.closest(".editar-transacao");
  if (!editar) return;
  e.preventDefault();
  e.stopPropagation();
  const id = editar.dataset.id;
  if (typeof window.abrirModalEditarTransacao === "function") {
    window.abrirModalEditarTransacao(id);
  }
});
