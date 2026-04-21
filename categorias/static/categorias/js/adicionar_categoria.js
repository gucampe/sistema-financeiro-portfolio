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

const overlayAcao = document.getElementById("overlay-acao-categoria");
const btnCancelarAcao = document.getElementById("btn-cancelar-acao");
const btnConfirmarAcao = document.getElementById("btn-confirmar-acao");
const modalAcaoTitulo = document.getElementById("modal-acao-titulo");
const modalAcaoMsg = document.getElementById("modal-acao-msg");

const overlayMigracao = document.getElementById("overlay-migracao-categoria");
const btnCancelarMigracao = document.getElementById("btn-cancelar-migracao");
const btnConfirmarMigracao = document.getElementById("btn-confirmar-migracao");
const selectMigracao = document.getElementById("select-migracao-categoria");
const migracaoCountEl = document.getElementById("migracao-count");
const erroMigracao = document.getElementById("erro-migracao");

const toast = document.getElementById("toast");
const toastMsg = document.getElementById("toast-msg");
const toastClose = document.getElementById("toast-close");
let toastTimeout;

const tbodyDespesa = document.getElementById("tbody-despesa");
const tbodyReceita = document.getElementById("tbody-receita");
const tbodyDespesaArquivadas = document.getElementById("tbody-despesa-arquivadas");
const tbodyReceitaArquivadas = document.getElementById("tbody-receita-arquivadas");
const tabelaCategorias = document.querySelector(".container table");

// Guarda o tr e a ação pendente: "arquivar" | "excluir"
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
  if (tbodyDespesa && !tbodyDespesa.classList.contains("hidden")) return "despesa";
  return "receita";
}

function getTargetTbodyByTipo(tipo) {
  return tipo === "receita" ? tbodyReceita : tbodyDespesa;
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
      overlayMigracao.classList.remove("hidden");
      categoriaParaAcao = document.querySelector(`tr[data-id="${categoriaId}"]`);
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
// Render helpers (linha da tabela)
// =====================
function renderActionsButtons(result, tipo, isArquivada = false) {
  if (isArquivada) {
    return `
      <div class="inline-flex items-center gap-2">
        <button type="button" class="restaurar-categoria inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-success-border bg-white transition text-sm text-success hover:bg-emerald-50"
                data-id="${result.id}" title="Restaurar">
          <i class="fa-solid fa-rotate-left text-xs"></i>
          <span class="hidden sm:inline">Restaurar</span>
        </button>
        <button type="button" class="excluir-definitivamente inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-danger-border bg-white transition text-sm text-danger hover:bg-red-50"
          data-id="${result.id}" title="Excluir definitivamente">
          <i class="fa-solid fa-trash text-xs"></i>
          <span class="hidden sm:inline">Excluir definitivamente</span>
        </button>
      </div>
    `;
  }
  return `
    <div class="inline-flex items-center gap-2">
      <button
        type="button"
        class="editar-categoria inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-300 bg-white transition text-sm text-fg hover:bg-gray-100"
        data-id="${result.id}"
        data-nome="${result.nome}"
        data-icone="${result.icone}"
        data-cor="${result.cor}"
        data-tipo="${tipo}"
        title="Editar"
      >
        <i class="fa-solid fa-pen-to-square text-xs text-brand-600"></i>
        <span class="hidden sm:inline">Editar</span>
      </button>

      <button
        type="button"
        class="arquivar-categoria inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-warning-border bg-white transition text-sm text-warning hover:bg-amber-50"
        data-id="${result.id}"
        title="Arquivar"
      >
        <i class="fa-solid fa-archive text-xs"></i>
        <span class="hidden sm:inline">Arquivar</span>
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
          tr.classList.add("border-b", "border-gray-100", "transition", "hover:bg-gray-50/80");
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

function renderRowArquivada(result, tipo) {
  return `
    <td class="py-2 px-6 flex items-center gap-2">
      <i class="fas ${result.icone}" style="color:${result.cor};"></i>
      <span class="nome-categoria">${result.nome}</span>
      <span class="ml-2 px-2 py-0.5 text-xs rounded-full bg-gray-200 text-gray-600">Arquivada</span>
    </td>
    <td class="py-2 text-right px-6">
      ${renderActionsButtons({ id: result.id, nome: result.nome, icone: result.icone, cor: result.cor }, tipo, true)}
    </td>
  `;
}

// Delegação em document para cobrir tabela ativas e seção arquivadas
document.addEventListener("click", (e) => {
  const btnEditar = e.target.closest(".editar-categoria");
  if (btnEditar) {
    e.preventDefault();
    const tr = btnEditar.closest("tr");
    if (!tr) return;
    if (tr.closest("#tbody-despesa-arquivadas, #tbody-receita-arquivadas")) return;
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

  const btnArquivar = e.target.closest(".arquivar-categoria");
  if (btnArquivar) {
    e.preventDefault();
    const tr = btnArquivar.closest("tr");
    if (!tr) return;
    if (tr.closest("#tbody-despesa-arquivadas, #tbody-receita-arquivadas")) return;
    categoriaParaAcao = tr;
    acaoPendente = "arquivar";
      if (modalAcaoTitulo) modalAcaoTitulo.textContent = "Arquivar categoria?";
      if (modalAcaoMsg)
        modalAcaoMsg.textContent =
          "A categoria será arquivada e não aparecerá mais nas listas. Você poderá excluí-la definitivamente depois, se não tiver transações vinculadas.";
      if (btnConfirmarAcao) {
        btnConfirmarAcao.textContent = "Arquivar";
        btnConfirmarAcao.className = "btn btn-warning-soft btn-sm";
      }
    if (overlayAcao) overlayAcao.classList.remove("hidden");
    return;
  }

  const btnExcluirDef = e.target.closest(".excluir-definitivamente");
  if (btnExcluirDef) {
    e.preventDefault();
    const tr = btnExcluirDef.closest("tr");
    if (!tr) return;
    categoriaParaAcao = tr;
    const id = tr.dataset.id;
    const tipo = tr.dataset.tipo || "despesa";

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
          if (overlayAcao) overlayAcao.classList.remove("hidden");
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
    const tr = btnRestaurar.closest("tr");
    if (!tr || !tr.closest("#tbody-despesa-arquivadas, #tbody-receita-arquivadas")) return;
    const id = tr.dataset.id;
    const tipo = tr.dataset.tipo || "despesa";
    const nome = safeText(tr.querySelector(".nome-categoria")?.textContent);
    const iconEl = tr.querySelector("i.fas");
    const icone = [...(iconEl?.classList || [])].find((c) =>
      c.startsWith("fa-") && !["fas", "far", "fab"].includes(c)
    ) || "fa-ellipsis-h";
    const cor = iconEl?.getAttribute("style")?.match(/color:\s*([^;]+)/)?.[1]?.trim() || "#4F46E5";

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
          const targetAtivas = getTargetTbodyByTipo(result.tipo || tipo);
          const emptyRow = targetAtivas?.querySelector("tr td[colspan]")?.closest("tr");
          if (emptyRow) emptyRow.remove();
          tr.remove();
          const newTr = document.createElement("tr");
          newTr.dataset.id = id;
          newTr.dataset.tipo = result.tipo || tipo;
          newTr.className = "border-b border-gray-100 transition hover:bg-gray-50/80";
          newTr.innerHTML = renderRow(
            { id, nome, icone, cor },
            result.tipo || tipo
          );
          if (targetAtivas) targetAtivas.appendChild(newTr);
          const parentArq = tr.closest("tbody");
          const restantesArq = parentArq?.querySelectorAll("tr[data-id]")?.length ?? 0;
          if (restantesArq === 0 && parentArq) {
            const emptyTr = document.createElement("tr");
            emptyTr.id = parentArq.id === "tbody-despesa-arquivadas" ? "empty-despesa-arquivadas" : "empty-receita-arquivadas";
            emptyTr.innerHTML = '<td colspan="2" class="py-4 text-center px-6 text-fg-muted">Nenhuma categoria arquivada.</td>';
            parentArq.appendChild(emptyTr);
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
if (btnCancelarMigracao) {
  btnCancelarMigracao.addEventListener("click", () => {
    categoriaParaAcao = null;
    acaoPendente = null;
    if (overlayMigracao) overlayMigracao.classList.add("hidden");
  });
}

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
        if (parent?.querySelectorAll("tr[data-id]").length === 0 && parent) {
          const emptyTr = document.createElement("tr");
          emptyTr.id = parent.id === "tbody-despesa-arquivadas" ? "empty-despesa-arquivadas" : "empty-receita-arquivadas";
          emptyTr.innerHTML = '<td colspan="2" class="py-4 text-center px-6" style="color: rgba(52,73,94,.6);">Nenhuma categoria arquivada.</td>';
          parent.appendChild(emptyTr);
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
      if (overlayMigracao) overlayMigracao.classList.add("hidden");
      categoriaParaAcao = null;
      acaoPendente = null;
    }
  });
}

// =====================
// Modal: Arquivar / Excluir definitivamente
// =====================
if (btnCancelarAcao) {
  btnCancelarAcao.addEventListener("click", () => {
    categoriaParaAcao = null;
    acaoPendente = null;
    if (overlayAcao) overlayAcao.classList.add("hidden");
  });
}

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
          const parentTbody = categoriaParaAcao.closest("tbody");
          const tipo = categoriaParaAcao.dataset.tipo || (parentTbody?.id === "tbody-despesa" ? "despesa" : "receita");
          const nome = safeText(categoriaParaAcao.querySelector(".nome-categoria")?.textContent);
          const iconeEl = categoriaParaAcao.querySelector("i.fas");
          const icone = iconeEl?.className?.match(/fa-[a-z0-9-]+/)?.[0] || "fa-ellipsis-h";
          const cor = iconeEl?.style?.color || "#4F46E5";

          const tbodyAtivas = parentTbody;
          const emptyRow = tbodyAtivas?.querySelector("tr td[colspan]");
          if (emptyRow) emptyRow.closest("tr")?.remove();
          categoriaParaAcao.remove();
          const restantes = tbodyAtivas?.querySelectorAll("tr[data-id]")?.length ?? 0;
          if (restantes === 0 && tbodyAtivas) {
            const msg = tipo === "despesa" ? "Nenhuma categoria de despesa." : "Nenhuma categoria de receita.";
            const trEmpty = document.createElement("tr");
            trEmpty.innerHTML = `<td colspan="2" class="py-4 text-center text-fg-muted">${msg}</td>`;
            tbodyAtivas.appendChild(trEmpty);
          }

          const targetArquivadas = tipo === "receita" ? tbodyReceitaArquivadas : tbodyDespesaArquivadas;
          if (targetArquivadas) {
            const emptyArq = targetArquivadas.querySelector("tr[id^='empty']");
            if (emptyArq) emptyArq.remove();
            const newTr = document.createElement("tr");
            newTr.className = "border-b border-gray-100 transition hover:bg-gray-50/80";
            newTr.dataset.id = id;
            newTr.dataset.tipo = tipo;
            newTr.innerHTML = renderRowArquivada({ id, nome, icone, cor }, tipo);
            targetArquivadas.appendChild(newTr);
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
          const parentTbodyExcluir = categoriaParaAcao.closest("tbody");
          const tipo = categoriaParaAcao.dataset.tipo ||
            (parentTbodyExcluir?.id === "tbody-receita-arquivadas" ? "receita" : "despesa");
          const parent = categoriaParaAcao.parentElement;
          const wasEmpty = parent && parent.querySelectorAll("tr").length <= 1;
          categoriaParaAcao.remove();
          if (wasEmpty && (parent?.id === "tbody-despesa-arquivadas" || parent?.id === "tbody-receita-arquivadas")) {
            const emptyTr = document.createElement("tr");
            emptyTr.id = parent.id === "tbody-despesa-arquivadas" ? "empty-despesa-arquivadas" : "empty-receita-arquivadas";
            emptyTr.innerHTML = '<td colspan="2" class="py-4 text-center px-6 text-fg-muted">Nenhuma categoria arquivada.</td>';
            parent.appendChild(emptyTr);
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
      if (overlayAcao) overlayAcao.classList.add("hidden");
      categoriaParaAcao = null;
      acaoPendente = null;
    }
  });
}