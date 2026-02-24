// =====================
// Seletores
// =====================
const iconGrid = document.getElementById("icon-grid");
const inputIcone = document.getElementById("icone");

const colorGrid = document.getElementById("color-grid");
const inputCor = document.getElementById("cor");

const inputTipo = document.getElementById("tipo");

const overlay = document.getElementById("overlay-adicionar-categoria");
const btnAbrir = document.getElementById("btn-adicionar-categoria");
const btnFechar = document.getElementById("btn-fechar-categoria");
const form = document.getElementById("form-adicionar-categoria");
const erroBox = document.getElementById("erro-categoria");
const tituloModal = overlay ? overlay.querySelector("h2") : null;

const overlayExcluir = document.getElementById("overlay-excluir-categoria");
const btnCancelarExcluir = document.getElementById("btn-cancelar-excluir");
const btnConfirmarExcluir = document.getElementById("btn-confirmar-excluir");

const toast = document.getElementById("toast");
const toastMsg = document.getElementById("toast-msg");
const toastClose = document.getElementById("toast-close");
let toastTimeout;

const tbodyDespesa = document.getElementById("tbody-despesa");
const tbodyReceita = document.getElementById("tbody-receita");

const tabelaCategorias = document.querySelector("table");

// Guarda o tr selecionado
let categoriaParaExcluir = null;

// Guarda o ID da categoria sendo editada (null se for nova)
let categoriaEditandoId = null;

// =====================
// Toast
// =====================
const toastColors = {
  sucesso: "bg-green-600",
  erro: "bg-red-600",
  info: "bg-blue-600",
};

function showToast(message, tipo = "sucesso") {
  if (!toast) return;

  toast.classList.remove(...Object.values(toastColors));
  toast.classList.add(toastColors[tipo] || toastColors.sucesso);

  if (toastMsg) toastMsg.textContent = message;

  toast.classList.remove("opacity-0", "pointer-events-none");
  toast.classList.add("opacity-100");

  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    toast.classList.remove("opacity-100");
    toast.classList.add("opacity-0", "pointer-events-none");
  }, 4000);
}

if (toastClose) {
  toastClose.addEventListener("click", () => {
    clearTimeout(toastTimeout);
    toast.classList.remove("opacity-100");
    toast.classList.add("opacity-0", "pointer-events-none");
  });
}

// =====================
// Helpers
// =====================
function getTipoAbaAtiva() {
  if (tbodyDespesa && !tbodyDespesa.classList.contains("hidden")) return "despesa";
  return "receita";
}

function getTargetTbodyByTipo(tipo) {
  return tipo === "receita" ? tbodyReceita : tbodyDespesa;
}

function limparIcones() {
  if (!iconGrid) return;
  iconGrid.querySelectorAll("div").forEach((d) => {
    d.classList.remove("border-blue-500", "bg-blue-50");
    const check = d.querySelector(".check-icon");
    if (check) check.classList.add("hidden");
  });
}

function limparCores() {
  if (!colorGrid) return;
  colorGrid.querySelectorAll("div").forEach((d) => {
    d.classList.remove("ring-4", "ring-blue-500");
    const check = d.querySelector(".check-color");
    if (check) check.classList.add("hidden");
  });
}

function getCsrfToken() {
  const el = document.querySelector("[name=csrfmiddlewaretoken]");
  return el ? el.value : "";
}

function safeText(s) {
  return String(s ?? "").trim();
}

// =====================
// Modal: preencher / abrir / fechar
// =====================
function preencherModal(nome, icone, cor, tipo, id) {
  if (!form) return;

  form.nome.value = safeText(nome);
  if (inputIcone) inputIcone.value = safeText(icone);
  if (inputCor) inputCor.value = safeText(cor);
  if (inputTipo) inputTipo.value = tipo || "despesa";

  const hiddenId = document.getElementById("categoria_id");
  if (hiddenId) hiddenId.value = id;

  categoriaEditandoId = id;

  limparIcones();
  limparCores();

  // Seleciona ícone
  if (iconGrid && icone) {
    const divIcon = iconGrid.querySelector(`div[data-value="${icone}"]`);
    if (divIcon) {
      divIcon.classList.add("border-blue-500", "bg-blue-50");
      const ck = divIcon.querySelector(".check-icon");
      if (ck) ck.classList.remove("hidden");
    }
  }

  // Seleciona cor
  if (colorGrid && cor) {
    const divCor = colorGrid.querySelector(`div[data-value="${cor}"]`);
    if (divCor) {
      divCor.classList.add("ring-4", "ring-blue-500");
      const ck = divCor.querySelector(".check-color");
      if (ck) ck.classList.remove("hidden");
    }
  }

  if (tituloModal) tituloModal.textContent = "Editar Categoria";

  if (overlay) {
    overlay.classList.remove("hidden", "opacity-0");
    overlay.classList.add("opacity-100", "scale-100");
  }
}

if (btnAbrir && overlay && form) {
  btnAbrir.addEventListener("click", () => {
    form.reset();
    categoriaEditandoId = null;
    limparIcones();
    limparCores();

    if (inputTipo) inputTipo.value = getTipoAbaAtiva();
    if (tituloModal) tituloModal.textContent = "Nova Categoria";

    overlay.classList.remove("hidden", "opacity-0");
    overlay.classList.add("opacity-100", "scale-100");
  });
}

if (btnFechar && overlay) {
  btnFechar.addEventListener("click", () => {
    overlay.classList.add("hidden");
  });
}

// =====================
// Seleção de ícone / cor
// =====================
if (iconGrid) {
  iconGrid.querySelectorAll("div").forEach((div) => {
    div.addEventListener("click", () => {
      limparIcones();
      div.classList.add("border-blue-500", "bg-blue-50");
      const ck = div.querySelector(".check-icon");
      if (ck) ck.classList.remove("hidden");
      if (inputIcone) inputIcone.value = div.dataset.value;
    });
  });
}

if (colorGrid) {
  colorGrid.querySelectorAll("div").forEach((div) => {
    div.addEventListener("click", () => {
      limparCores();
      div.classList.add("ring-4", "ring-blue-500");
      const ck = div.querySelector(".check-color");
      if (ck) ck.classList.remove("hidden");
      if (inputCor) inputCor.value = div.dataset.value;
    });
  });
}

// =====================
// Render helpers (linha da tabela)
// =====================
function renderActionsButtons(result, tipo) {
  // Botões bonitos (mesma estética que você colocou no template)
  return `
    <div class="inline-flex items-center gap-2">
      <button
        type="button"
        class="editar-categoria inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-200 text-gray-700 bg-white hover:bg-gray-50 hover:border-gray-300 transition text-sm"
        data-id="${result.id}"
        data-nome="${result.nome}"
        data-icone="${result.icone}"
        data-cor="${result.cor}"
        data-tipo="${tipo}"
        title="Editar"
      >
        <i class="fa-solid fa-pen-to-square text-xs"></i>
        <span class="hidden sm:inline">Editar</span>
      </button>

      <button
        type="button"
        class="excluir-categoria inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-red-200 text-red-600 bg-white hover:bg-red-50 hover:border-red-300 transition text-sm"
        data-id="${result.id}"
        title="Excluir"
      >
        <i class="fa-solid fa-trash text-xs"></i>
        <span class="hidden sm:inline">Excluir</span>
      </button>
    </div>
  `;
}

function renderRow(result, tipo) {
  return `
    <td class="py-2 flex items-center gap-2">
      <i class="fas ${result.icone}" style="color:${result.cor};"></i>
      <span class="nome-categoria">${result.nome}</span>
    </td>
    <td class="py-2 text-right">
      ${renderActionsButtons(result, tipo)}
    </td>
  `;
}

// =====================
// Submit (criar/editar) via AJAX
// =====================
if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (erroBox) erroBox.classList.add("hidden");

    const data = new FormData(form);

    if (categoriaEditandoId) {
      data.set("categoria_id", categoriaEditandoId);
    }

    if (inputTipo) {
      data.set("tipo", inputTipo.value || "despesa");
    }

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: data,
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });

      const result = await response.json();

      if (result.status === "ok") {
        const tipo = result.tipo || (inputTipo ? inputTipo.value : "despesa");
        const targetTbody = getTargetTbodyByTipo(tipo);

        if (!targetTbody) {
          showToast("Erro: tbodys não encontrados no template.", "erro");
          return;
        }

        if (categoriaEditandoId) {
          // Atualiza linha existente
          const tr = document.querySelector(`tr[data-id="${categoriaEditandoId}"]`);
          if (!tr) {
            showToast("Não encontrei a linha para editar.", "erro");
            return;
          }

          // Move se mudou o tipo
          if (tr.parentElement !== targetTbody) {
            tr.remove();
            targetTbody.appendChild(tr);
          }

          tr.dataset.id = categoriaEditandoId;
          tr.innerHTML = renderRow(
            {
              id: result.id,
              nome: result.nome,
              icone: result.icone,
              cor: result.cor,
            },
            tipo
          );
        } else {
          // Cria nova linha
          const tr = document.createElement("tr");
          tr.dataset.id = result.id;
          tr.classList.add("border-b", "hover:bg-gray-50");
          tr.innerHTML = renderRow(
            {
              id: result.id,
              nome: result.nome,
              icone: result.icone,
              cor: result.cor,
            },
            tipo
          );

          targetTbody.appendChild(tr);
        }

        // Fecha modal + limpa
        form.reset();
        if (inputIcone) inputIcone.value = "";
        if (inputCor) inputCor.value = "";
        limparIcones();
        limparCores();

        if (inputTipo) inputTipo.value = getTipoAbaAtiva();
        if (overlay) overlay.classList.add("hidden");

        showToast(categoriaEditandoId ? "Categoria editada com sucesso!" : "Categoria salva com sucesso!");
        categoriaEditandoId = null;

        if (typeof window.atualizarContador === "function") {
          window.atualizarContador();
        }
      } else {
        if (erroBox) {
          erroBox.textContent = result.errors || "Erro ao salvar categoria";
          erroBox.classList.remove("hidden");
        } else {
          showToast(result.errors || "Erro ao salvar categoria", "erro");
        }
      }
    } catch (err) {
      console.error(err);
      if (erroBox) {
        erroBox.textContent = "Erro inesperado. Tente novamente.";
        erroBox.classList.remove("hidden");
      } else {
        showToast("Erro inesperado. Tente novamente.", "erro");
      }
    }
  });
}

// =====================
// Clique em Editar/Excluir (delegação no TABLE inteiro)
// - usa closest() para funcionar ao clicar no ícone dentro do botão
// =====================
if (tabelaCategorias) {
  tabelaCategorias.addEventListener("click", (e) => {
    const btnEditar = e.target.closest(".editar-categoria");
    if (btnEditar) {
      e.preventDefault();

      const tr = btnEditar.closest("tr");
      if (!tr) return;

      const id = tr.dataset.id;
      const nome = btnEditar.dataset.nome || safeText(tr.querySelector(".nome-categoria")?.textContent);
      const icone = btnEditar.dataset.icone || "fa-ellipsis-h";
      const cor = btnEditar.dataset.cor || "#4F46E5";
      const tipo =
        btnEditar.dataset.tipo ||
        (tr.parentElement && tr.parentElement.id === "tbody-receita" ? "receita" : "despesa");

      preencherModal(nome, icone, cor, tipo, id);
      return;
    }

    const btnExcluir = e.target.closest(".excluir-categoria");
    if (btnExcluir) {
      e.preventDefault();

      const tr = btnExcluir.closest("tr");
      if (!tr) return;

      categoriaParaExcluir = tr;
      if (overlayExcluir) overlayExcluir.classList.remove("hidden");
      return;
    }
  });
}

// =====================
// Exclusão
// =====================
if (btnCancelarExcluir) {
  btnCancelarExcluir.addEventListener("click", () => {
    categoriaParaExcluir = null;
    if (overlayExcluir) overlayExcluir.classList.add("hidden");
  });
}

if (btnConfirmarExcluir) {
  btnConfirmarExcluir.addEventListener("click", async () => {
    if (!categoriaParaExcluir) return;

    const id = categoriaParaExcluir.dataset.id;

    try {
      const response = await fetch(`/categorias/excluir/${id}/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCsrfToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      const result = await response.json();

      if (result.status === "ok") {
        categoriaParaExcluir.remove();
        showToast("Categoria excluída com sucesso!", "sucesso");

        if (typeof window.atualizarContador === "function") {
          window.atualizarContador();
        }
      } else {
        showToast(result.error || "Erro ao excluir categoria!", "erro");
      }
    } catch (err) {
      console.error(err);
      showToast("Erro inesperado ao excluir categoria!", "erro");
    } finally {
      if (overlayExcluir) overlayExcluir.classList.add("hidden");
      categoriaParaExcluir = null;
    }
  });
}