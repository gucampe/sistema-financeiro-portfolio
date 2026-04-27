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
    let lastOptgroup = null;
    Array.from(selectEl.options).forEach((opt) => {
      if (!opt.value) return;
      const og = opt.parentElement && opt.parentElement.tagName === "OPTGROUP" ? opt.parentElement : null;
      if (og && og !== lastOptgroup) {
        lastOptgroup = og;
        const header = document.createElement("div");
        header.setAttribute("role", "presentation");
        header.className =
          "sticky top-0 z-[1] border-b border-gray-100 bg-gray-50 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-fg-muted";
        header.textContent = og.label || "";
        list.appendChild(header);
      } else if (!og) {
        lastOptgroup = null;
      }
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
