document.addEventListener("DOMContentLoaded", () => {
  const btnAbrir = document.getElementById("btn-adicionar");
  const btnFechar = document.getElementById("btn-fechar");
  const overlay = document.getElementById("overlay-adicionar");
  const form = document.getElementById("form-adicionar");
  const selectTipo = document.getElementById("tipo");
  const selectCategoria = document.getElementById("categoria");
  const modalHeader = overlay.querySelector("h2");

  if (!overlay) return;

  function popularCategorias(tipo, selecionadaId = null) {
    if (!selectCategoria) return;
    fetch(`/categorias/listar-ativas/?tipo=${tipo || "despesa"}`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then((r) => r.json())
      .then((data) => {
        selectCategoria.innerHTML = '<option value="">Selecione uma categoria</option>';
        if (data.status === "ok" && data.categorias?.length) {
          data.categorias.forEach((c) => {
            const opt = document.createElement("option");
            opt.value = c.id;
            opt.textContent = c.nome;
            if (selecionadaId && c.id == selecionadaId) opt.selected = true;
            selectCategoria.appendChild(opt);
          });
        }
      })
      .catch(() => {});
  }

  function limparErroContaAjax() {
    const el = document.getElementById("erro-conta-ajax");
    if (el) {
      el.textContent = "";
      el.classList.add("hidden");
    }
  }

  // Abrir modal para adicionar
  btnAbrir?.addEventListener("click", () => {
    overlay.dataset.editando = ""; // limpar modo edição
    if (modalHeader) modalHeader.textContent = "Nova Transação";
    const tipo = selectTipo?.value || "despesa";
    if (!tipo) return;
    limparErroContaAjax();
    popularCategorias(tipo);
    overlay.classList.remove("hidden");
    setTimeout(() => overlay.classList.remove("opacity-0"), 10);
  });

  // Fechar modal
  const fecharModal = () => {
    overlay.classList.add("opacity-0");
    setTimeout(() => overlay.classList.add("hidden"), 300);
    overlay.dataset.editando = "";
    form.reset();
  };

  btnFechar?.addEventListener("click", fecharModal);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) fecharModal();
  });

  // Editar transação (clicando no botão histórico)
  document.addEventListener("click", (e) => {
    const editar = e.target.closest(".editar-transacao");
    if (!editar) return;
    const id = editar.dataset.id;

    fetch(`/transacoes/${id}/editar/?ajax=1`)
      .then(r => r.json())
      .then(data => {
        overlay.dataset.editando = id;
        if (modalHeader) modalHeader.textContent = "Editar Transação";
        selectTipo.value = data.tipo;
        document.getElementById("valor").value = data.valor;
        document.getElementById("descricao").value = data.descricao;
        document.getElementById("data").value = data.data;
        // Conta
        const selectConta = document.getElementById("id_conta");
        if (selectConta) selectConta.value = data.conta ? data.conta.id : "";
        // Categoria
        popularCategorias(data.tipo, data.categoria.id);
        limparErroContaAjax();
        overlay.classList.remove("hidden");
        setTimeout(() => overlay.classList.remove("opacity-0"), 10);
      })
      .catch(err => console.error("Erro ao carregar transação:", err));
  });

  // AJAX submit
  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const editandoId = overlay.dataset.editando;
    const url = editandoId ? `/transacoes/${editandoId}/editar/` : form.action;

    const formData = new FormData(form);
    const csrfToken = formData.get("csrfmiddlewaretoken");

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrfToken,
          "X-Requested-With": "XMLHttpRequest"
        },
        body: formData
      });

      const data = await response.json();

      if (data.status === "ok") {
        limparErroContaAjax();
        fecharModal();
        window.location.reload();
      } else {
        const erroContaEl = document.getElementById("erro-conta-ajax");
        if (erroContaEl && data.errors && data.errors.conta && data.errors.conta.length) {
          erroContaEl.textContent = data.errors.conta[0];
          erroContaEl.classList.remove("hidden");
        }
        if (data.errors && Object.keys(data.errors).length) {
          alert("Erro ao salvar: " + JSON.stringify(data.errors));
        }
      }
    } catch (error) {
      alert("Erro de comunicação.");
    }
  });

  // Atualiza categorias quando muda tipo
  selectTipo?.addEventListener("change", () => {
    const tipo = selectTipo.value || "despesa";
    popularCategorias(tipo);
  });
});