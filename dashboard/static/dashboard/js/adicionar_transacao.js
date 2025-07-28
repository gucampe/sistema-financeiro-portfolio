console.log("✅ adicionar_transacao.js foi carregado");

document.addEventListener("DOMContentLoaded", () => {
  console.log("✅ DOM carregado");
  const btnAbrir = document.getElementById("btn-adicionar");
  const btnFechar = document.getElementById("btn-fechar");
  const overlay = document.getElementById("overlay-adicionar");
  const form = document.getElementById("form-adicionar");

  if (!btnAbrir || !btnFechar || !overlay || !form) {
    console.warn("⚠️ Elementos do modal não encontrados.");
    return;
  }

  // Abrir modal
  btnAbrir.addEventListener("click", () => {
    overlay.classList.remove("hidden", "opacity-0");
    overlay.classList.add("flex", "opacity-100");
  });

  // Fechar modal
  btnFechar.addEventListener("click", () => {
    overlay.classList.remove("opacity-100");
    overlay.classList.add("opacity-0");
    setTimeout(() => {
      overlay.classList.remove("flex");
      overlay.classList.add("hidden");
    }, 300); // espera a transição terminar
  });

  // Fechar clicando no fundo
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) btnFechar.click();
  });

  // AJAX submit
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = new FormData(form);
    const csrfToken = formData.get("csrfmiddlewaretoken");

    try {
      const response = await fetch(form.action, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken, "X-Requested-With": "XMLHttpRequest" },
        body: formData
      });

      const data = await response.json();

      if (data.status === "ok") {
        btnFechar.click();
        form.reset();
        window.location.reload(); // Atualiza o dashboard
      } else {
        alert("Erro ao salvar: " + JSON.stringify(data.errors));
      }
    } catch (error) {
      alert("Erro de comunicação.");
    }
  });
});
