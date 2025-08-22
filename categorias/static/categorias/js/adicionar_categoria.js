// Seletores
const iconGrid = document.getElementById("icon-grid");
const inputIcone = document.getElementById("icone");

const colorGrid = document.getElementById("color-grid");
const inputCor = document.getElementById("cor");

const overlay = document.getElementById("overlay-adicionar-categoria");
const btnAbrir = document.getElementById("btn-adicionar-categoria");
const btnFechar = document.getElementById("btn-fechar-categoria");
const form = document.getElementById("form-adicionar-categoria");
const erroBox = document.getElementById("erro-categoria");
const tituloModal = overlay.querySelector("h2");
const overlayExcluir = document.getElementById("overlay-excluir-categoria");
const btnCancelarExcluir = document.getElementById("btn-cancelar-excluir");
const btnConfirmarExcluir = document.getElementById("btn-confirmar-excluir");
const toast = document.getElementById("toast");
const toastMsg = document.getElementById("toast-msg");
const toastClose = document.getElementById("toast-close");
let toastTimeout;

let categoriaParaExcluir = null; // Guarda o tr selecionado

// Guarda o ID da categoria sendo editada (null se for nova)
let categoriaEditandoId = null;

// Função para mostrar toast
// Cores padrão para cada tipo de toast
const toastColors = {
  sucesso: "bg-green-600",
  erro: "bg-red-600",
  info: "bg-blue-600"
};

// Função para exibir toast
function showToast(message, tipo = "sucesso") {
  // Remove cores anteriores
  toast.classList.remove(...Object.values(toastColors));

  // Aplica cor correta
  toast.classList.add(toastColors[tipo]);
  toastMsg.textContent = message;

  // Exibe
  toast.classList.remove("opacity-0", "pointer-events-none");
  toast.classList.add("opacity-100");

  // Limpa timeout anterior
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    toast.classList.remove("opacity-100");
    toast.classList.add("opacity-0", "pointer-events-none");
  }, 4000); // desaparece após 4s
}

// Fecha manualmente ao clicar no X
toastClose.addEventListener("click", () => {
  clearTimeout(toastTimeout);
  toast.classList.remove("opacity-100");
  toast.classList.add("opacity-0", "pointer-events-none");
});

// Função para limpar seleção de ícone
function limparIcones() {
  iconGrid.querySelectorAll("div").forEach(d => {
    d.classList.remove("border-blue-500", "bg-blue-50");
    const check = d.querySelector(".check-icon");
    if (check) check.classList.add("hidden");
  });
}

// Função para limpar seleção de cor
function limparCores() {
  colorGrid.querySelectorAll("div").forEach(d => {
    d.classList.remove("ring-4", "ring-blue-500");
    const check = d.querySelector(".check-color");
    if (check) check.classList.add("hidden");
  });
}

// Preenche modal com dados de edição
  // Preenche modal com dados de edição
function preencherModal(nome, icone, cor, id) {
  form.nome.value = nome;
  inputIcone.value = icone;
  inputCor.value = cor;
  document.getElementById("categoria_id").value = id; // <- aqui
  categoriaEditandoId = id;

  limparIcones();
  limparCores();

  // Seleciona ícone
  const divIcon = iconGrid.querySelector(`div[data-value="${icone}"]`);
  if (divIcon) {
    divIcon.classList.add("border-blue-500", "bg-blue-50");
    divIcon.querySelector(".check-icon").classList.remove("hidden");
  }

  // Seleciona cor
  const divCor = colorGrid.querySelector(`div[data-value="${cor}"]`);
  if (divCor) {
    divCor.classList.add("ring-4", "ring-blue-500");
    divCor.querySelector(".check-color").classList.remove("hidden");
  }

  tituloModal.textContent = "Editar Categoria";
  overlay.classList.remove("hidden", "opacity-0");
  overlay.classList.add("opacity-100", "scale-100");
}



// Seleção de ícone
if (iconGrid) {
  iconGrid.querySelectorAll("div").forEach(div => {
    div.addEventListener("click", () => {
      limparIcones();
      div.classList.add("border-blue-500", "bg-blue-50");
      div.querySelector(".check-icon").classList.remove("hidden");
      inputIcone.value = div.dataset.value;
    });
  });
}

// Seleção de cor
if (colorGrid) {
  colorGrid.querySelectorAll("div").forEach(div => {
    div.addEventListener("click", () => {
      limparCores();
      div.classList.add("ring-4", "ring-blue-500");
      div.querySelector(".check-color").classList.remove("hidden");
      inputCor.value = div.dataset.value;
    });
  });
}

// Abrir modal para nova categoria
if (btnAbrir && overlay) {
  btnAbrir.addEventListener("click", () => {
    form.reset();
    categoriaEditandoId = null;
    limparIcones();
    limparCores();
    tituloModal.textContent = "Nova Categoria";
    overlay.classList.remove("hidden", "opacity-0");
    overlay.classList.add("opacity-100", "scale-100");
  });
}

// Fechar modal
if (btnFechar && overlay) {
  btnFechar.addEventListener("click", () => {
    overlay.classList.add("hidden");
  });
}

// Envio do formulário via AJAX (criar ou editar)
if (form) {
  // Envio do formulário via AJAX (criar ou editar)
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  erroBox.classList.add("hidden");

  const data = new FormData(form);

  // Se estiver editando, envia ID
  if (categoriaEditandoId) {
    data.set("categoria_id", categoriaEditandoId); // garante que o campo está presente
  }

  try {
    const response = await fetch(form.action, {
      method: "POST",
      body: data,
      headers: { "X-Requested-With": "XMLHttpRequest" }
    });

    const result = await response.json();

    if (result.status === "ok") {
      const tbody = document.querySelector("table tbody");

      if (categoriaEditandoId) {
        // Atualiza linha existente
        const tr = tbody.querySelector(`tr[data-id="${categoriaEditandoId}"]`);
        tr.dataset.id = categoriaEditandoId;
        tr.innerHTML = `
          <td class="py-2 flex items-center gap-2">
            <i class="fas ${result.icone}" style="color:${result.cor};"></i>
            <span>${result.nome}</span>
          </td>
          <td class="py-2 text-right">
            <a href="#" class="text-blue-600 hover:underline text-sm">Editar</a>
            <a href="#" class="text-red-600 hover:underline text-sm ml-4">Excluir</a>
          </td>
        `;
      } else {
        // Cria nova linha
        const tr = document.createElement("tr");
        tr.dataset.id = result.id;
        tr.classList.add("border-b", "hover:bg-gray-50");
        tr.innerHTML = `
          <td class="py-2 flex items-center gap-2">
            <i class="fas ${result.icone}" style="color:${result.cor};"></i>
            <span>${result.nome}</span>
          </td>
          <td class="py-2 text-right">
            <a href="#" class="text-blue-600 hover:underline text-sm">Editar</a>
            <a href="#" class="text-red-600 hover:underline text-sm ml-4">Excluir</a>
          </td>
        `;
        tbody.appendChild(tr);
      }

      // Limpa modal
      form.reset();
      inputIcone.value = "";
      inputCor.value = "";
      limparIcones();
      limparCores();
      overlay.classList.add("hidden");

      showToast(categoriaEditandoId ? "Categoria editada com sucesso!" : "Categoria salva com sucesso!");

      categoriaEditandoId = null; // só depois do toast
    } else {
      erroBox.textContent = result.errors?.nome || "Erro ao salvar categoria";
      erroBox.classList.remove("hidden");
    }
  } catch (err) {
    erroBox.textContent = "Erro inesperado. Tente novamente.";
    erroBox.classList.remove("hidden");
    console.error(err);
  }
});

}



document.querySelector("table tbody").addEventListener("click", async (e) => {
  const tr = e.target.closest("tr");
  if (!tr) return;
  const id = tr.dataset.id;

  // Editar (mantém igual)
  if (e.target.textContent === "Editar") {
    const nome = tr.querySelector("span").textContent;
    const icone = tr.querySelector("i").classList[1];
    const cor = tr.querySelector("i").style.color;
    preencherModal(nome, icone, cor, id);
  }

  // Excluir
  if (e.target.textContent === "Excluir") {
    e.preventDefault();

    categoriaParaExcluir = tr;
    overlayExcluir.classList.remove("hidden");
  }
});

// Cancelar exclusão
btnCancelarExcluir.addEventListener("click", () => {
  categoriaParaExcluir = null;
  overlayExcluir.classList.add("hidden");
});

// Confirmar exclusão
btnConfirmarExcluir.addEventListener("click", async () => {
  if (!categoriaParaExcluir) return;
  
  const id = categoriaParaExcluir.dataset.id;
  try {
    const response = await fetch(`/categorias/excluir/${id}/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
        "X-Requested-With": "XMLHttpRequest"
      }
    });

    const result = await response.json();
    if (result.status === "ok") {
      categoriaParaExcluir.remove();
      showToast("Categoria excluída com sucesso!");
    } else {
      showToast(result.error || "Erro ao excluir categoria!");
    }
  } catch (err) {
    console.error(err);
    showToast("Erro inesperado ao excluir categoria!");
  } finally {
    overlayExcluir.classList.add("hidden");
    categoriaParaExcluir = null;
  }
});

