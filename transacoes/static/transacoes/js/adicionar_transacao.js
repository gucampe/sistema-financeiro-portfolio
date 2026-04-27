/**
 * Combobox visual sobre <select> nativo (conta + categoria).
 * O select permanece a fonte da verdade para FormData / validação.
 */
function initIconCombobox(selectEl, kind) {
  const root = selectEl.closest("[data-combobox-root]");
  if (!root) return null;

  const trigger = root.querySelector("[data-combobox-trigger]");
  const list = root.querySelector("[data-combobox-list]");
  const iconSlot = trigger?.querySelector("[data-combobox-trigger-icon]");
  const labelEl = trigger?.querySelector("[data-combobox-trigger-label]");

  if (!trigger || !list || !iconSlot || !labelEl) return null;

  let isOpen = false;

  function setOpen(next) {
    isOpen = next;
    trigger.setAttribute("aria-expanded", String(next));
    list.classList.toggle("hidden", !next);
    list.toggleAttribute("hidden", !next);
  }

  function renderIconIntoSlot(slot, opt) {
    slot.innerHTML = "";
    if (!opt || !opt.value) {
      const i = document.createElement("i");
      i.className =
        kind === "account"
          ? "fa-solid fa-building-columns text-gray-300 text-lg"
          : "fa-solid fa-tag text-gray-300 text-lg";
      i.setAttribute("aria-hidden", "true");
      slot.appendChild(i);
      return;
    }

    if (kind === "account") {
      const url = opt.dataset.iconUrl;
      if (url) {
        const img = document.createElement("img");
        img.src = url;
        img.alt = "";
        img.className = "h-full w-full object-contain";
        slot.appendChild(img);
      } else {
        const i = document.createElement("i");
        i.className = "fa-solid fa-building-columns text-gray-300 text-lg";
        i.setAttribute("aria-hidden", "true");
        slot.appendChild(i);
      }
      return;
    }

    const icone = opt.dataset.icone || "fa-ellipsis-h";
    const cor = opt.dataset.cor || "#4F46E5";
    const i = document.createElement("i");
    i.className = `fas ${icone}`;
    i.style.color = cor;
    i.setAttribute("aria-hidden", "true");
    slot.appendChild(i);
  }

  function syncTrigger() {
    const sel = selectEl.options[selectEl.selectedIndex];
    if (!sel || !sel.value) {
      const ph =
        selectEl.options[0]?.textContent?.trim() ||
        (kind === "account" ? "Selecione uma conta" : "Selecione uma categoria");
      labelEl.textContent = ph;
      renderIconIntoSlot(iconSlot, null);
      return;
    }
    labelEl.textContent = sel.textContent.trim();
    renderIconIntoSlot(iconSlot, sel);
  }

  function buildList() {
    list.innerHTML = "";
    Array.from(selectEl.options).forEach((opt) => {
      if (!opt.value) return;
      const row = document.createElement("button");
      row.type = "button";
      row.setAttribute("role", "option");
      row.setAttribute("aria-selected", opt.selected ? "true" : "false");
      row.className =
        "flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-[#34495E] hover:bg-gray-100 focus:bg-gray-100 focus:outline-none";
      const slot = document.createElement("span");
      slot.className =
        "flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-md bg-gray-50";
      renderIconIntoSlot(slot, opt);
      const text = document.createElement("span");
      text.className = "min-w-0 flex-1 truncate";
      text.textContent = opt.textContent.trim();
      row.append(slot, text);
      row.addEventListener("click", () => {
        selectEl.value = opt.value;
        selectEl.dispatchEvent(new Event("change", { bubbles: true }));
        setOpen(false);
        syncTrigger();
      });
      list.appendChild(row);
    });
  }

  function openList() {
    buildList();
    setOpen(true);
  }

  function closeList() {
    setOpen(false);
  }

  trigger.addEventListener("click", () => {
    if (isOpen) closeList();
    else openList();
  });

  selectEl.addEventListener("change", syncTrigger);

  syncTrigger();

  return {
    refresh() {
      buildList();
      syncTrigger();
    },
    sync: syncTrigger,
    close: closeList,
  };
}

window.initIconCombobox = initIconCombobox;

document.addEventListener("DOMContentLoaded", () => {
  const btnAbrir = document.getElementById("btn-adicionar");
  const btnFechar = document.getElementById("btn-fechar");
  const overlay = document.getElementById("overlay-adicionar");
  const form = document.getElementById("form-adicionar");
  const selectTipo = document.getElementById("tipo");
  const selectCategoria = document.getElementById("categoria");
  const selectConta = document.getElementById("id_conta");
  const selectCartao = document.getElementById("id_cartao");
  const modalHeader = overlay?.querySelector("h2");

  let contaCombobox = null;
  let categoriaCombobox = null;
  if (selectConta) contaCombobox = initIconCombobox(selectConta, "account");
  if (selectCategoria) categoriaCombobox = initIconCombobox(selectCategoria, "category");

  const rootConta = selectConta?.closest("[data-combobox-root]");
  const rootCategoria = selectCategoria?.closest("[data-combobox-root]");

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
            if (c.icone != null) opt.dataset.icone = c.icone;
            if (c.cor != null) opt.dataset.cor = c.cor;
            if (selecionadaId && c.id == selecionadaId) opt.selected = true;
            selectCategoria.appendChild(opt);
          });
        }
        categoriaCombobox?.refresh();
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

  function fecharComboboxes() {
    contaCombobox?.close();
    categoriaCombobox?.close();
  }

  document.addEventListener("click", (e) => {
    const inConta = rootConta?.contains(e.target);
    const inCategoria = rootCategoria?.contains(e.target);
    if (inConta) {
      categoriaCombobox?.close();
      return;
    }
    if (inCategoria) {
      contaCombobox?.close();
      return;
    }
    fecharComboboxes();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") fecharComboboxes();
  });

  // Abrir modal para adicionar
  btnAbrir?.addEventListener("click", () => {
    overlay.dataset.editando = "";
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
    fecharComboboxes();
    form.reset();
    contaCombobox?.sync();
    categoriaCombobox?.sync();
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
      .then((r) => r.json())
      .then((data) => {
        overlay.dataset.editando = id;
        if (modalHeader) modalHeader.textContent = "Editar Transação";
        selectTipo.value = data.tipo;
        document.getElementById("valor").value = data.valor;
        document.getElementById("descricao").value = data.descricao;
        document.getElementById("data").value = data.data;
        if (selectConta) selectConta.value = data.conta ? data.conta.id : "";
        if (selectCartao) selectCartao.value = data.cartao ? data.cartao.id : "";
        contaCombobox?.sync();
        popularCategorias(data.tipo, data.categoria.id);
        limparErroContaAjax();
        overlay.classList.remove("hidden");
        setTimeout(() => overlay.classList.remove("opacity-0"), 10);
      })
      .catch((err) => console.error("Erro ao carregar transação:", err));
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
          "X-Requested-With": "XMLHttpRequest",
        },
        body: formData,
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
