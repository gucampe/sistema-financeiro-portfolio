document.addEventListener("DOMContentLoaded", () => {
    console.log("✅ adicionar_categoria.js carregado");
  
    const btnAbrir = document.getElementById("btn-adicionar-categoria");
    const btnFechar = document.getElementById("btn-fechar-categoria");
    const overlay = document.getElementById("overlay-adicionar-categoria");
    const form = document.getElementById("form-adicionar-categoria");
  
    if (!btnAbrir || !btnFechar || !overlay || !form) return;
  
    // Abrir modal
    btnAbrir.addEventListener("click", () => {
      overlay.classList.remove("hidden");
      overlay.classList.remove("opacity-0"); // <-- remover opacity-0
      setTimeout(() => overlay.classList.add("opacity-100"), 10);
    });
  
    // Fechar modal
    btnFechar.addEventListener("click", () => {
      overlay.classList.remove("opacity-100");
      overlay.classList.add("opacity-0"); // <-- recoloca opacity-0
      setTimeout(() => overlay.classList.add("hidden"), 300);
    });
  
    // Fechar clicando no fundo
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) btnFechar.click();
    });
  
    // Submit via AJAX
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
          window.location.reload();
        } else {
          alert("Erro: " + JSON.stringify(data.errors));
        }
      } catch (error) {
        alert("Erro de comunicação.");
      }
    });
  });
  