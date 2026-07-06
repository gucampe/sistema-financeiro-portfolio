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
  let listPortaled = false;
  const listPlaceholder = document.createComment("combobox-list-anchor");

  function isInsideModalPanel() {
    return !!root.closest("[data-modal-panel], .modal-panel");
  }

  function resolveFloatingZIndex() {
    let el = root;
    while (el) {
      if (el.matches?.("[data-modal], .modal-overlay")) {
        const z = parseInt(window.getComputedStyle(el).zIndex, 10);
        if (Number.isFinite(z) && z > 0) return z + 10;
      }
      el = el.parentElement;
    }
    const token = getComputedStyle(document.documentElement)
      .getPropertyValue("--z-combobox-floating")
      .trim();
    const parsed = parseInt(token, 10);
    return Number.isFinite(parsed) ? parsed : 70;
  }

  function positionFloatingList() {
    const rect = trigger.getBoundingClientRect();
    const maxH = Math.min(224, window.innerHeight - rect.bottom - 12);
    list.style.position = "fixed";
    list.style.top = `${rect.bottom + 4}px`;
    list.style.left = `${rect.left}px`;
    list.style.width = `${rect.width}px`;
    list.style.maxHeight = `${Math.max(120, maxH)}px`;
    list.style.zIndex = String(resolveFloatingZIndex());
    list.classList.add("combobox-list--floating");
  }

  function portalList() {
    if (listPortaled || !isInsideModalPanel()) return;
    list.after(listPlaceholder);
    document.body.appendChild(list);
    listPortaled = true;
  }

  function restoreList() {
    if (!listPortaled) return;
    listPlaceholder.replaceWith(list);
    list.style.position = "";
    list.style.top = "";
    list.style.left = "";
    list.style.width = "";
    list.style.maxHeight = "";
    list.style.zIndex = "";
    list.classList.remove("combobox-list--floating");
    listPortaled = false;
  }

  function setOpen(next) {
    isOpen = next;
    trigger.setAttribute("aria-expanded", String(next));
    if (next) {
      portalList();
      if (listPortaled) positionFloatingList();
    } else {
      restoreList();
    }
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

  window.addEventListener(
    "resize",
    () => {
      if (isOpen && listPortaled) positionFloatingList();
    },
    { passive: true }
  );

  document.addEventListener(
    "scroll",
    () => {
      if (isOpen && listPortaled) positionFloatingList();
    },
    true
  );

  if (isInsideModalPanel()) {
    const overlay = root.closest("[data-modal], .modal-overlay");
    if (overlay) {
      const observer = new MutationObserver(() => {
        if (
          overlay.classList.contains("hidden") ||
          overlay.getAttribute("aria-hidden") === "true"
        ) {
          closeList();
        }
      });
      observer.observe(overlay, {
        attributes: true,
        attributeFilter: ["class", "aria-hidden"],
      });
    }
  }

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
