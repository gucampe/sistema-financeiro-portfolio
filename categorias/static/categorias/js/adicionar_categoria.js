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
const form = document.getElementById("form-adicionar-categoria");
const erroBox = document.getElementById("erro-categoria");
const tituloModal = overlay ? overlay.querySelector("h2") : null;

const overlayAcao = document.getElementById("overlay-acao-categoria");
const btnConfirmarAcao = document.getElementById("btn-confirmar-acao");
const modalAcaoTitulo = document.getElementById("modal-acao-titulo");
const modalAcaoMsg = document.getElementById("modal-acao-msg");

const overlayMigracao = document.getElementById("overlay-migracao-categoria");
const btnConfirmarMigracao = document.getElementById("btn-confirmar-migracao");
const selectMigracao = document.getElementById("select-migracao-categoria");
const migracaoCountEl = document.getElementById("migracao-count");
const erroMigracao = document.getElementById("erro-migracao");

const toast = document.getElementById("toast");
const toastMsg = document.getElementById("toast-msg");
const toastClose = document.getElementById("toast-close");
let toastTimeout;

const listaDespesa = document.getElementById("lista-despesa");
const listaReceita = document.getElementById("lista-receita");
const listaDespesaArquivadas = document.getElementById("lista-despesa-arquivadas");
const listaReceitaArquivadas = document.getElementById("lista-receita-arquivadas");

const LIST_ITEM_SELECTOR = "[data-categoria-item]";

// Guarda o item da lista e a ação pendente: "arquivar" | "excluir"
let categoriaParaAcao = null;
let acaoPendente = null;

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
  if (listaDespesa && !listaDespesa.classList.contains("hidden")) return "despesa";
  return "receita";
}

function getTargetListaByTipo(tipo) {
  return tipo === "receita" ? listaReceita : listaDespesa;
}

function closestCategoriaItem(el) {
  return el ? el.closest(LIST_ITEM_SELECTOR) : null;
}

function isListaArquivadas(lista) {
  return (
    lista?.id === "lista-despesa-arquivadas" || lista?.id === "lista-receita-arquivadas"
  );
}

function removeEmptyPlaceholder(lista) {
  lista?.querySelector("[data-empty-categoria]")?.remove();
}

function ensureEmptyPlaceholder(lista, message, id) {
  if (!lista || countCategorias(lista) > 0) return;
  if (lista.querySelector("[data-empty-categoria]")) return;
  const li = document.createElement("li");
  if (id) li.id = id;
  li.setAttribute("role", "presentation");
  li.dataset.emptyCategoria = "1";
  li.className = "px-4 py-12 text-center text-sm text-fg-muted sm:px-5";
  li.textContent = message;
  lista.appendChild(li);
}

function countCategorias(lista) {
  return lista ? lista.querySelectorAll(LIST_ITEM_SELECTOR).length : 0;
}

function limparIcones() {
  if (!iconGrid) return;
  iconGrid.querySelectorAll("div").forEach((d) => {
    d.classList.remove("border-brand-500", "bg-brand-50");
    const check = d.querySelector(".check-icon");
    if (check) check.classList.add("hidden");
  });
}

function limparCores() {
  if (!colorGrid) return;
  colorGrid.querySelectorAll("div").forEach((d) => {
    d.classList.remove("ring-4", "ring-brand-500");
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

function getCorFromIconEl(iconEl) {
  if (!iconEl) return "#4F46E5";
  if (iconEl.style?.color) return iconEl.style.color;
  const fromClass = [...iconEl.classList].find((c) => c.startsWith("text-[") && c.endsWith("]"));
  if (fromClass) return fromClass.slice(6, -1);
  const computed = getComputedStyle(iconEl).color;
  return computed && computed !== "rgba(0, 0, 0, 0)" ? computed : "#4F46E5";
}

function abrirModalMigracao(categoriaId, tipo, count) {
  if (!overlayMigracao || !migracaoCountEl || !selectMigracao) return;
  migracaoCountEl.textContent = count;
  if (erroMigracao) erroMigracao.classList.add("hidden");
  selectMigracao.innerHTML = '<option value="">Selecione uma categoria</option>';

  fetch(`/categorias/listar-ativas/?tipo=${tipo}`, {
    headers: { "X-Requested-With": "XMLHttpRequest" },
  })
    .then((r) => r.json())
    .then((result) => {
      if (result.status !== "ok" || !result.categorias?.length) {
        showToast("Não há categorias ativas disponíveis. Crie uma nova categoria primeiro.", "erro");
        return;
      }
      const opts = result.categorias.filter((c) => parseInt(c.id, 10) !== parseInt(categoriaId, 10));
      if (!opts.length) {
        showToast("Não há outras categorias ativas deste tipo. Crie uma nova categoria primeiro.", "erro");
        return;
      }
      opts.forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = c.nome;
        selectMigracao.appendChild(opt);
      });
      globalThis.GranaGoModal?.open(overlayMigracao);
      categoriaParaAcao = document.querySelector(
        `${LIST_ITEM_SELECTOR}[data-id="${categoriaId}"]`
      );
      acaoPendente = "migracao";
    })
    .catch((err) => {
      console.error(err);
      showToast("Erro ao carregar categorias.", "erro");
    });
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
      divIcon.classList.add("border-brand-500", "bg-brand-50");
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

  globalThis.GranaGoModal?.open(overlay);
}

if (btnAbrir && overlay && form) {
  btnAbrir.addEventListener("click", () => {
    form.reset();
    categoriaEditandoId = null;
    limparIcones();
    limparCores();

    if (inputTipo) inputTipo.value = getTipoAbaAtiva();
    if (tituloModal) tituloModal.textContent = "Nova Categoria";

    globalThis.GranaGoModal?.open(overlay, { trigger: btnAbrir });
  });
}

function fecharOverlayAdicionar() {
  categoriaEditandoId = null;
}

function fecharOverlayAcao() {
  categoriaParaAcao = null;
  acaoPendente = null;
}

function fecharOverlayMigracao() {
  categoriaParaAcao = null;
  acaoPendente = null;
}

if (globalThis.GranaGoModal) {
  if (overlay) GranaGoModal.bind(overlay, { onClose: fecharOverlayAdicionar });
  if (overlayAcao) GranaGoModal.bind(overlayAcao, { onClose: fecharOverlayAcao });
  if (overlayMigracao) GranaGoModal.bind(overlayMigracao, { onClose: fecharOverlayMigracao });
}

// =====================
// Seleção de ícone / cor
// =====================
if (iconGrid) {
  iconGrid.querySelectorAll("div").forEach((div) => {
    div.addEventListener("click", () => {
      limparIcones();
      div.classList.add("border-brand-500", "bg-brand-50");
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
      div.classList.add("ring-4", "ring-brand-500");
      const ck = div.querySelector(".check-color");
      if (ck) ck.classList.remove("hidden");
      if (inputCor) inputCor.value = div.dataset.value;
    });
  });
}

// =====================
// Render helpers (list row)
// =====================
const LI_ROW_CLASSES =
  "group relative -mx-4 px-4 py-2.5 transition hover:bg-surface-muted active:bg-surface-muted sm:-mx-5 sm:px-5";

const BTN_ACAO_BASE =
  "inline-flex items-center gap-2 rounded-lg bg-gray-200 px-2 py-1.5 text-sm transition hover:bg-gray-300 sm:px-4 sm:py-2";

function renderIconBox(result) {
  const icone = result.icone || "fa-ellipsis-h";
  const cor = result.cor || "#4F46E5";
  return `
    <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border bg-[${cor}20] border-[${cor}40]">
      <i class="fas ${icone} text-[15px] text-[${cor}]"></i>
    </div>
  `;
}

function renderActionsButtons(result, tipo, isArquivada = false) {
  if (isArquivada) {
    return `
      <div class="inline-flex shrink-0 items-center gap-2">
        <button type="button" class="restaurar-categoria ${BTN_ACAO_BASE} text-gray-800"
                data-id="${result.id}" title="Restaurar">
          <i class="fa-solid fa-rotate-left text-xs text-gray-700"></i>
          <span class="hidden sm:inline">Restaurar</span>
        </button>
        <button type="button" class="excluir-definitivamente ${BTN_ACAO_BASE} text-red-600"
          data-id="${result.id}" title="Excluir definitivamente">
          <i class="fa-solid fa-trash text-xs"></i>
          <span class="hidden sm:inline">Excluir</span>
        </button>
      </div>
    `;
  }
  return `
    <div class="inline-flex shrink-0 items-center gap-2">
      <button
        type="button"
        class="editar-categoria ${BTN_ACAO_BASE} text-gray-800"
        data-id="${result.id}"
        data-nome="${result.nome}"
        data-icone="${result.icone}"
        data-cor="${result.cor}"
        data-tipo="${tipo}"
        title="Editar"
      >
        <i class="fa-solid fa-pen-to-square text-xs text-gray-700"></i>
        <span class="hidden sm:inline">Editar</span>
      </button>
      <button
        type="button"
        class="arquivar-categoria ${BTN_ACAO_BASE} text-amber-700"
        data-id="${result.id}"
        title="Arquivar"
      >
        <i class="fa-solid fa-archive text-xs"></i>
        <span class="hidden sm:inline">Arquivar</span>
      </button>
    </div>
  `;
}

function renderCategoriaRowInner(result, tipo, isArquivada = false) {
  const secondary = isArquivada
    ? '<p class="mt-0.5 truncate text-[12px] leading-tight text-gray-500">Arquivada</p>'
    : "";
  const actions = renderActionsButtons(result, tipo, isArquivada);
  return `
    <div class="flex min-w-0 items-center gap-2 md:grid md:grid-cols-[minmax(0,1fr)_auto] md:items-center md:gap-4">
      <div class="flex min-w-0 flex-1 items-center gap-2.5 md:min-w-0">
        ${renderIconBox(result)}
        <div class="min-w-0 flex-1">
          <p class="nome-categoria truncate text-sm font-semibold leading-tight text-fg" title="${result.nome}">${result.nome}</p>
          ${secondary}
        </div>
      </div>
      <div class="flex shrink-0 flex-row items-center justify-end gap-1.5 min-w-0 sm:gap-2 md:gap-3">
        ${actions}
      </div>
    </div>
  `;
}

function createListItem(result, tipo, isArquivada = false) {
  const li = document.createElement("li");
  li.setAttribute("role", "listitem");
  li.dataset.categoriaItem = "1";
  li.dataset.id = String(result.id);
  li.dataset.tipo = tipo;
  li.className = LI_ROW_CLASSES;
  li.innerHTML = renderCategoriaRowInner(result, tipo, isArquivada);
  return li;
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
        const targetLista = getTargetListaByTipo(tipo);

        if (!targetLista) {
          showToast("Erro: listas não encontradas no template.", "erro");
          return;
        }

        if (categoriaEditandoId) {
          const li = document.querySelector(
            `${LIST_ITEM_SELECTOR}[data-id="${categoriaEditandoId}"]`
          );
          if (!li) {
            showToast("Não encontrei a categoria para editar.", "erro");
            return;
          }

          if (li.parentElement !== targetLista) {
            li.remove();
            targetLista.appendChild(li);
          }

          li.dataset.id = String(categoriaEditandoId);
          li.innerHTML = renderCategoriaRowInner(
            {
              id: result.id,
              nome: result.nome,
              icone: result.icone,
              cor: result.cor,
            },
            tipo,
            false
          );
        } else {
          removeEmptyPlaceholder(targetLista);
          const li = createListItem(
            {
              id: result.id,
              nome: result.nome,
              icone: result.icone,
              cor: result.cor,
            },
            tipo
          );
          targetLista.appendChild(li);
        }

        // Fecha modal + limpa
        form.reset();
        if (inputIcone) inputIcone.value = "";
        if (inputCor) inputCor.value = "";
        limparIcones();
        limparCores();

        if (inputTipo) inputTipo.value = getTipoAbaAtiva();
        globalThis.GranaGoModal?.close(overlay);

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

// Delegação em document para listas ativas e arquivadas
document.addEventListener("click", (e) => {
  const btnEditar = e.target.closest(".editar-categoria");
  if (btnEditar) {
    e.preventDefault();
    const item = closestCategoriaItem(btnEditar);
    if (!item) return;
    if (isListaArquivadas(item.parentElement)) return;
    const id = item.dataset.id;
    const nome = btnEditar.dataset.nome || safeText(item.querySelector(".nome-categoria")?.textContent);
    const icone = btnEditar.dataset.icone || "fa-ellipsis-h";
    const cor = btnEditar.dataset.cor || "#4F46E5";
    const tipo =
      btnEditar.dataset.tipo ||
      (item.parentElement?.id === "lista-receita" ? "receita" : "despesa");
    preencherModal(nome, icone, cor, tipo, id);
    return;
  }

  const btnArquivar = e.target.closest(".arquivar-categoria");
  if (btnArquivar) {
    e.preventDefault();
    const item = closestCategoriaItem(btnArquivar);
    if (!item) return;
    if (isListaArquivadas(item.parentElement)) return;
    categoriaParaAcao = item;
    acaoPendente = "arquivar";
      if (modalAcaoTitulo) modalAcaoTitulo.textContent = "Arquivar categoria?";
      if (modalAcaoMsg)
        modalAcaoMsg.textContent =
          "A categoria será arquivada e não aparecerá mais nas listas. Você poderá excluí-la definitivamente depois, se não tiver transações vinculadas.";
      if (btnConfirmarAcao) {
        btnConfirmarAcao.textContent = "Arquivar";
        btnConfirmarAcao.className = "btn btn-warning-soft btn-sm";
      }
    globalThis.GranaGoModal?.open(overlayAcao);
    return;
  }

  const btnExcluirDef = e.target.closest(".excluir-definitivamente");
  if (btnExcluirDef) {
    e.preventDefault();
    const item = closestCategoriaItem(btnExcluirDef);
    if (!item) return;
    categoriaParaAcao = item;
    const id = item.dataset.id;
    const tipo = item.dataset.tipo || "despesa";

    fetch(`/categorias/verificar-exclusao/${id}/`, {
      method: "GET",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then((r) => r.json())
      .then((result) => {
        if (result.status === "ok" && result.count === 0) {
          acaoPendente = "excluir";
          if (modalAcaoTitulo) modalAcaoTitulo.textContent = "Excluir definitivamente?";
          if (modalAcaoMsg)
            modalAcaoMsg.textContent =
              "Tem certeza? Esta ação não pode ser desfeita. Só é permitido excluir categorias arquivadas sem transações vinculadas.";
          if (btnConfirmarAcao) {
            btnConfirmarAcao.textContent = "Excluir";
            btnConfirmarAcao.className = "btn btn-danger btn-sm";
          }
          globalThis.GranaGoModal?.open(overlayAcao);
        } else if (result.status === "ok" && result.count > 0) {
          abrirModalMigracao(id, tipo, result.count);
        } else {
          showToast(result.errors || "Erro ao verificar exclusão.", "erro");
        }
      })
      .catch((err) => {
        console.error(err);
        showToast("Erro ao verificar exclusão.", "erro");
      });
    return;
  }

  const btnRestaurar = e.target.closest(".restaurar-categoria");
  if (btnRestaurar) {
    e.preventDefault();
    const item = closestCategoriaItem(btnRestaurar);
    if (!item || !isListaArquivadas(item.parentElement)) return;
    const id = item.dataset.id;
    const tipo = item.dataset.tipo || "despesa";
    const nome = safeText(item.querySelector(".nome-categoria")?.textContent);
    const iconEl = item.querySelector("i.fas");
    const icone = [...(iconEl?.classList || [])].find((c) =>
      c.startsWith("fa-") && !["fas", "far", "fab"].includes(c)
    ) || "fa-ellipsis-h";
    const cor = getCorFromIconEl(iconEl);

    const formData = new FormData();
    formData.append("categoria_id", id);
    formData.append("csrfmiddlewaretoken", getCsrfToken());

    fetch("/categorias/restaurar/", {
      method: "POST",
      body: formData,
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then((r) => r.json())
      .then((result) => {
        if (result.status === "ok") {
          const tipoFinal = result.tipo || tipo;
          const targetAtivas = getTargetListaByTipo(tipoFinal);
          const parentArq = item.parentElement;
          removeEmptyPlaceholder(targetAtivas);
          item.remove();
          if (targetAtivas) {
            targetAtivas.appendChild(
              createListItem({ id, nome, icone, cor }, tipoFinal, false)
            );
          }
          if (parentArq && countCategorias(parentArq) === 0) {
            ensureEmptyPlaceholder(
              parentArq,
              "Nenhuma categoria arquivada.",
              parentArq.id === "lista-despesa-arquivadas"
                ? "empty-despesa-arquivadas"
                : "empty-receita-arquivadas"
            );
          }
          showToast("Categoria restaurada com sucesso!", "sucesso");
          if (typeof window.atualizarContadorArquivadas === "function") {
            window.atualizarContadorArquivadas(result.tipo || tipo, -1);
          }
        } else {
          showToast(result.errors || "Erro ao restaurar categoria!", "erro");
        }
      })
      .catch((err) => {
        console.error(err);
        showToast("Erro inesperado ao restaurar!", "erro");
      });
  }
});

// =====================
// Modal Migração
// =====================

if (btnConfirmarMigracao) {
  btnConfirmarMigracao.addEventListener("click", async () => {
    if (!categoriaParaAcao || acaoPendente !== "migracao") return;
    const novaId = selectMigracao?.value;
    if (!novaId) {
      if (erroMigracao) {
        erroMigracao.textContent = "Selecione uma categoria.";
        erroMigracao.classList.remove("hidden");
      }
      return;
    }
    if (erroMigracao) erroMigracao.classList.add("hidden");

    const formData = new FormData();
    formData.append("categoria_id", categoriaParaAcao.dataset.id);
    formData.append("nova_categoria_id", novaId);
    formData.append("csrfmiddlewaretoken", getCsrfToken());

    try {
      const response = await fetch("/categorias/excluir-com-migracao/", {
        method: "POST",
        body: formData,
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const result = await response.json();

      if (result.status === "ok") {
        const parent = categoriaParaAcao.parentElement;
        const tipo = categoriaParaAcao.dataset.tipo || "despesa";
        categoriaParaAcao.remove();
        if (parent && countCategorias(parent) === 0) {
          ensureEmptyPlaceholder(
            parent,
            "Nenhuma categoria arquivada.",
            parent.id === "lista-despesa-arquivadas"
              ? "empty-despesa-arquivadas"
              : "empty-receita-arquivadas"
          );
        }
        showToast("Transações transferidas e categoria excluída com sucesso!", "sucesso");
        if (typeof window.atualizarContadorArquivadas === "function") {
          window.atualizarContadorArquivadas(tipo, -1);
        }
      } else {
        if (erroMigracao) {
          erroMigracao.textContent = result.errors || "Erro ao processar.";
          erroMigracao.classList.remove("hidden");
        } else {
          showToast(result.errors || "Erro ao processar.", "erro");
        }
      }
    } catch (err) {
      console.error(err);
      showToast("Erro inesperado!", "erro");
    } finally {
      globalThis.GranaGoModal?.close(overlayMigracao);
      categoriaParaAcao = null;
      acaoPendente = null;
    }
  });
}

// =====================
// Modal: Arquivar / Excluir definitivamente
// =====================

if (btnConfirmarAcao) {
  btnConfirmarAcao.addEventListener("click", async () => {
    if (!categoriaParaAcao || !acaoPendente) return;
    const id = categoriaParaAcao.dataset.id;

    try {
      if (acaoPendente === "arquivar") {
        const formData = new FormData();
        formData.append("categoria_id", id);
        formData.append("csrfmiddlewaretoken", getCsrfToken());

        const response = await fetch("/categorias/arquivar/", {
          method: "POST",
          body: formData,
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        const result = await response.json();

        if (result.status === "ok") {
          const listaAtivas = categoriaParaAcao.parentElement;
          const tipo =
            categoriaParaAcao.dataset.tipo ||
            (listaAtivas?.id === "lista-receita" ? "receita" : "despesa");
          const nome = safeText(categoriaParaAcao.querySelector(".nome-categoria")?.textContent);
          const iconeEl = categoriaParaAcao.querySelector("i.fas");
          const icone = iconeEl?.className?.match(/fa-[a-z0-9-]+/)?.[0] || "fa-ellipsis-h";
          const cor = getCorFromIconEl(iconeEl);

          categoriaParaAcao.remove();
          if (listaAtivas && countCategorias(listaAtivas) === 0) {
            const msg =
              tipo === "despesa"
                ? "Nenhuma categoria de despesa."
                : "Nenhuma categoria de receita.";
            ensureEmptyPlaceholder(listaAtivas, msg);
          }

          const targetArquivadas =
            tipo === "receita" ? listaReceitaArquivadas : listaDespesaArquivadas;
          if (targetArquivadas) {
            removeEmptyPlaceholder(targetArquivadas);
            targetArquivadas.appendChild(
              createListItem({ id, nome, icone, cor }, tipo, true)
            );
          }
          showToast("Categoria arquivada com sucesso!", "sucesso");
          if (typeof window.atualizarContadorArquivadas === "function") {
            window.atualizarContadorArquivadas(tipo, 1);
          }
        } else {
          showToast(result.errors || "Erro ao arquivar categoria!", "erro");
        }
      } else {
        const response = await fetch(`/categorias/excluir/${id}/`, {
          method: "POST",
          headers: {
            "X-CSRFToken": getCsrfToken(),
            "X-Requested-With": "XMLHttpRequest",
          },
        });
        const result = await response.json();

        if (result.status === "ok") {
          const parent = categoriaParaAcao.parentElement;
          const tipo =
            categoriaParaAcao.dataset.tipo ||
            (parent?.id === "lista-receita-arquivadas" ? "receita" : "despesa");
          categoriaParaAcao.remove();
          if (parent && isListaArquivadas(parent) && countCategorias(parent) === 0) {
            ensureEmptyPlaceholder(
              parent,
              "Nenhuma categoria arquivada.",
              parent.id === "lista-despesa-arquivadas"
                ? "empty-despesa-arquivadas"
                : "empty-receita-arquivadas"
            );
          }
          showToast("Categoria excluída definitivamente!", "sucesso");
          if (typeof window.atualizarContadorArquivadas === "function") {
            window.atualizarContadorArquivadas(tipo, -1);
          }
        } else if (result.status === "blocked") {
          const msg =
            result.message ||
            (result.reason === "in_use"
              ? `Categoria possui ${result.count || 0} transação(ões) e não pode ser excluída.`
              : result.message);
          showToast(msg, "erro");
        } else {
          showToast(result.error || "Erro ao excluir categoria!", "erro");
        }
      }
    } catch (err) {
      console.error(err);
      showToast("Erro inesperado!", "erro");
    } finally {
      globalThis.GranaGoModal?.close(overlayAcao);
      categoriaParaAcao = null;
      acaoPendente = null;
    }
  });
}