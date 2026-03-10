document.addEventListener("DOMContentLoaded", () => {
  const btnAbrir = document.getElementById("btn-adicionar");
  const btnFechar = document.getElementById("btn-fechar");
  const overlay = document.getElementById("overlay-adicionar");
  const form = document.getElementById("form-adicionar");
  const selectTipo = document.getElementById("tipo");
  const selectCategoria = document.getElementById("categoria");

  if (!overlay) return;

  function popularCategorias(tipo) {
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
            selectCategoria.appendChild(opt);
          });
        }
      })
      .catch(() => {});
  }

  selectTipo?.addEventListener("change", () => {
    const tipo = selectTipo.value || "despesa";
    popularCategorias(tipo);
  });

  function limparErroContaAjax() {
    const el = document.getElementById("erro-conta-ajax");
    if (el) {
      el.textContent = "";
      el.classList.add("hidden");
    }
  }

  btnAbrir?.addEventListener("click", () => {
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
  };

  btnFechar?.addEventListener("click", fecharModal);

  // Fechar clicando no fundo
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) fecharModal();
  });

  // AJAX submit
  form?.addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = new FormData(form);
    const csrfToken = formData.get("csrfmiddlewaretoken");

    try {
      const response = await fetch(form.action, {
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
        form.reset();
        // data.conta (id, nome, icone) disponível para exibição na lista sem reload, se desejar
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
});
