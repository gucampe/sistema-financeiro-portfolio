(function (global) {
  const MQ_MOBILE_TABLET = "(max-width: 1023px)";
  const MENU_TRIGGER_CLASS = "lista-contextual-menu-trigger";
  const ACTION_ATTR = "data-lista-acao";

  /** @type {HTMLElement | null} */
  let floatingDropdown = null;
  /** @type {import('./lista_contextual').ListaContextualInstance | null} */
  let activeController = null;
  /** @type {HTMLElement | null} */
  let dropdownTrigger = null;

  const controllers = new Set();

  function isMobileTablet() {
    return window.matchMedia(MQ_MOBILE_TABLET).matches;
  }

  function limparEstiloDropdown(menu) {
    menu.style.top = "";
    menu.style.bottom = "";
    menu.style.left = "";
    menu.style.right = "";
  }

  function posicionarDropdown(menu, trigger) {
    limparEstiloDropdown(menu);
    menu.classList.remove("hidden");

    const rect = trigger.getBoundingClientRect();
    const menuWidth = menu.offsetWidth || 200;
    const menuHeight = menu.offsetHeight || 160;
    const margem = 6;

    let top = rect.bottom + margem;
    if (top + menuHeight > window.innerHeight - margem) {
      top = rect.top - menuHeight - margem;
    }

    let left = rect.right - menuWidth;
    if (left < margem) left = margem;
    if (left + menuWidth > window.innerWidth - margem) {
      left = window.innerWidth - menuWidth - margem;
    }

    menu.style.top = `${Math.max(margem, top)}px`;
    menu.style.left = `${left}px`;
  }

  function getOrCreateDropdown() {
    if (!floatingDropdown) {
      floatingDropdown = document.createElement("div");
      floatingDropdown.id = "lista-contextual-dropdown-floating";
      floatingDropdown.className =
        "lista-contextual-acoes-menu lista-contextual-acoes-menu--dropdown hidden";
      floatingDropdown.setAttribute("role", "menu");
      floatingDropdown.setAttribute("aria-label", "Ações");
      document.body.appendChild(floatingDropdown);
    }
    return floatingDropdown;
  }

  function criarBotaoAcao(action, variant) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "lista-contextual-acao-item";
    if (variant === "sheet") btn.classList.add("lista-contextual-acao-item--sheet");
    if (action.danger) btn.classList.add("lista-contextual-acao-item--danger");
    btn.setAttribute(ACTION_ATTR, action.id);
    btn.setAttribute("role", "menuitem");

    const icon = document.createElement("i");
    icon.className = `${action.icon} text-sm${action.danger ? "" : " text-gray-500"}`;
    icon.setAttribute("aria-hidden", "true");

    const label = document.createElement("span");
    label.textContent = action.label;

    btn.appendChild(icon);
    btn.appendChild(label);
    return btn;
  }

  function montarNavAcoes(container, actions, variant) {
    container.innerHTML = "";
    const normal = actions.filter((a) => !a.danger);
    const danger = actions.filter((a) => a.danger);

    if (variant === "sheet") {
      const ul = document.createElement("ul");
      ul.className = "lista-contextual-sheet__list";
      ul.setAttribute("role", "menu");

      normal.forEach((action) => {
        const li = document.createElement("li");
        li.setAttribute("role", "none");
        li.appendChild(criarBotaoAcao(action, "sheet"));
        ul.appendChild(li);
      });

      if (danger.length) {
        const li = document.createElement("li");
        li.className = "mt-1 border-t border-gray-100 pt-1";
        li.setAttribute("role", "none");
        danger.forEach((action) => li.appendChild(criarBotaoAcao(action, "sheet")));
        ul.appendChild(li);
      }

      container.appendChild(ul);
      return;
    }

    normal.forEach((action) => container.appendChild(criarBotaoAcao(action, "dropdown")));

    if (danger.length) {
      const sep = document.createElement("div");
      sep.className = "my-1 border-t border-gray-100";
      sep.setAttribute("role", "separator");
      sep.setAttribute("aria-hidden", "true");
      container.appendChild(sep);
      danger.forEach((action) => container.appendChild(criarBotaoAcao(action, "dropdown")));
    }
  }

  function fecharDropdown() {
    if (!floatingDropdown || !floatingDropdown.classList.contains("lista-contextual-acoes-menu--open")) {
      return;
    }
    const trigger = dropdownTrigger;
    floatingDropdown.classList.remove("lista-contextual-acoes-menu--open");
    floatingDropdown.classList.add("hidden");
    limparEstiloDropdown(floatingDropdown);
    if (trigger) trigger.setAttribute("aria-expanded", "false");
    dropdownTrigger = null;
    activeController = null;
  }

  function abrirDropdown(controller, trigger, item) {
    fecharDropdown();
    const actions = controller.getActions(item);
    if (!actions.length) return;

    activeController = controller;
    dropdownTrigger = trigger;
    controller.activeItem = item;
    controller.activePayload = controller.getPayload(item);

    const menu = getOrCreateDropdown();
    montarNavAcoes(menu, actions, "dropdown");
    document.body.appendChild(menu);
    posicionarDropdown(menu, trigger);

    requestAnimationFrame(() => {
      menu.classList.add("lista-contextual-acoes-menu--open");
    });
    trigger.setAttribute("aria-expanded", "true");
    menu.querySelector(".lista-contextual-acao-item")?.focus();
  }

  function resolverController(target) {
    if (activeController) return activeController;
    for (const ctrl of controllers) {
      if (ctrl.root?.contains(target)) return ctrl;
    }
    return null;
  }

  function executarAcaoDeEvento(acaoBtn) {
    const acao = acaoBtn.getAttribute(ACTION_ATTR);
    if (!acao) return;

    const sheetOverlay = document.getElementById("overlay-lista-contextual-acoes");
    const veioDoSheet = !!sheetOverlay?.contains(acaoBtn);
    const veioDoDropdown = !!floatingDropdown?.contains(acaoBtn);

    const controller = activeController || resolverController(acaoBtn);
    if (!controller) return;

    const item = controller.activeItem;
    const payload = controller.activePayload ?? (item ? controller.getPayload(item) : null);

    if (veioDoSheet) global.GranaGoModal?.close(sheetOverlay);
    if (veioDoDropdown) fecharDropdown();

    controller.onAction(acao, payload, item);

    if (veioDoSheet) {
      controller.activeItem = null;
      controller.activePayload = null;
      if (activeController === controller) activeController = null;
    }
  }

  function tentarExecutarAcaoDeEvento(target) {
    const acaoBtn = target.closest?.(`[${ACTION_ATTR}]`);
    if (!acaoBtn) return false;

    const sheetOverlay = document.getElementById("overlay-lista-contextual-acoes");
    const noSheet = sheetOverlay?.contains(acaoBtn);
    const noDropdown = floatingDropdown?.contains(acaoBtn);
    if (!noSheet && !noDropdown) return false;

    executarAcaoDeEvento(acaoBtn);
    return true;
  }

  class ListaContextual {
    constructor(options) {
      this.options = options;
      this.root =
        typeof options.root === "string" ? document.querySelector(options.root) : options.root;
      if (!this.root) return;

      this.sheetOverlay = document.getElementById(options.sheetId || "overlay-lista-contextual-acoes");
      this.sheetTitulo = document.getElementById(options.sheetTituloId || "lista-contextual-sheet-titulo");
      this.sheetMeta = document.getElementById(options.sheetMetaId || "lista-contextual-sheet-meta");
      this.sheetNav = document.getElementById(options.sheetNavId || "lista-contextual-sheet-nav");

      this.itemSelector = options.itemSelector || ".lista-contextual-item";
      this.interactiveSelector =
        options.interactiveSelector ||
        "button, a, input, select, textarea, label, form, [data-lista-acao]";

      /** @type {HTMLElement | null} */
      this.activeItem = null;
      /** @type {unknown} */
      this.activePayload = null;

      controllers.add(this);
      this._bind();
    }

    canInteract(item) {
      if (this.options.canInteract) return this.options.canInteract(item);
      return true;
    }

    getPayload(item) {
      return this.options.getPayload ? this.options.getPayload(item) : { el: item };
    }

    getTitulo(item) {
      return this.options.getTitulo ? this.options.getTitulo(item) : "";
    }

    getMeta(item) {
      return this.options.getMeta ? this.options.getMeta(item) : "";
    }

    getActions(item) {
      return this.options.getActions ? this.options.getActions(item) : [];
    }

    onAction(actionId, payload, item) {
      if (this.options.onAction) this.options.onAction(actionId, payload, item);
    }

    abrirSheet(item) {
      if (!this.sheetOverlay || !global.GranaGoModal) return;
      const actions = this.getActions(item);
      if (!actions.length) return;

      activeController = this;
      this.activeItem = item;
      this.activePayload = this.getPayload(item);

      if (this.sheetTitulo) this.sheetTitulo.textContent = this.getTitulo(item);
      if (this.sheetMeta) {
        const meta = this.getMeta(item);
        this.sheetMeta.textContent = meta;
        this.sheetMeta.classList.toggle("hidden", !meta);
      }
      if (this.sheetNav) montarNavAcoes(this.sheetNav, actions, "sheet");

      GranaGoModal.open(this.sheetOverlay);
    }

    _onSheetClose() {
      this.activeItem = null;
      this.activePayload = null;
      if (activeController === this) activeController = null;
    }

    _itemFromTarget(target) {
      const item = target.closest(this.itemSelector);
      if (!item || !this.root.contains(item)) return null;
      if (!this.canInteract(item)) return null;
      return item;
    }

    _tentarAbrirSheetMobile(target) {
      if (!isMobileTablet()) return false;
      if (global.GranaGoTouch?.wasScroll()) return false;
      if (target.closest(this.interactiveSelector)) return false;

      const item = this._itemFromTarget(target);
      if (!item) return false;

      this.abrirSheet(item);
      return true;
    }

    _bind() {
      const onClick = (event) => {
        const menuTrigger = event.target.closest(`.${MENU_TRIGGER_CLASS}`);
        if (menuTrigger && this.root.contains(menuTrigger)) {
          event.preventDefault();
          event.stopPropagation();
          const item = menuTrigger.closest(this.itemSelector);
          if (!item || !this.canInteract(item)) return;

          const aberto =
            floatingDropdown?.classList.contains("lista-contextual-acoes-menu--open") &&
            dropdownTrigger === menuTrigger;

          if (aberto) fecharDropdown();
          else abrirDropdown(this, menuTrigger, item);
          return;
        }

        if (this._tentarAbrirSheetMobile(event.target)) {
          event.preventDefault();
        }
      };

      this.root.addEventListener("click", onClick);

      this.root.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        if (!isMobileTablet()) return;
        if (event.target.closest(`.${MENU_TRIGGER_CLASS}, [${ACTION_ATTR}]`)) return;

        const item = this._itemFromTarget(event.target);
        if (!item) return;

        event.preventDefault();
        this.abrirSheet(item);
      });
    }
  }

  if (!global.__listaContextualGlobalBound) {
    global.__listaContextualGlobalBound = true;

    const sheetOverlay = document.getElementById("overlay-lista-contextual-acoes");
    if (sheetOverlay && global.GranaGoModal) {
      GranaGoModal.bind(sheetOverlay, {
        onClose: () => {
          for (const ctrl of controllers) ctrl._onSheetClose();
        },
      });
    }

    document.addEventListener("click", (event) => {
      if (global.GranaGoTouch?.wasScroll() && event.target.closest?.(`[${ACTION_ATTR}]`)) {
        event.preventDefault();
        event.stopPropagation();
        return;
      }
      if (tentarExecutarAcaoDeEvento(event.target)) {
        event.preventDefault();
        event.stopPropagation();
        return;
      }

      if (
        floatingDropdown?.classList.contains("lista-contextual-acoes-menu--open") &&
        !event.target.closest(
          "#lista-contextual-dropdown-floating, .lista-contextual-menu-trigger"
        )
      ) {
        fecharDropdown();
      }
    });

    document.addEventListener(
      "touchend",
      (event) => {
        if (global.GranaGoTouch?.wasScroll()) return;
        if (tentarExecutarAcaoDeEvento(event.target)) {
          event.preventDefault();
          event.stopPropagation();
        }
      },
      { passive: false }
    );

    document.addEventListener(
      "keydown",
      (event) => {
        if (!floatingDropdown?.classList.contains("lista-contextual-acoes-menu--open")) return;
        if (event.key !== "Escape") return;
        event.preventDefault();
        event.stopImmediatePropagation();
        const trigger = dropdownTrigger;
        fecharDropdown();
        trigger?.focus();
      },
      true
    );

    document.addEventListener("keydown", (event) => {
      if (!floatingDropdown?.classList.contains("lista-contextual-acoes-menu--open")) return;
      const items = [...floatingDropdown.querySelectorAll(".lista-contextual-acao-item")];
      const idx = items.indexOf(document.activeElement);
      if (event.key === "ArrowDown" && items.length) {
        event.preventDefault();
        items[(idx + 1) % items.length]?.focus();
      }
      if (event.key === "ArrowUp" && items.length) {
        event.preventDefault();
        items[(idx - 1 + items.length) % items.length]?.focus();
      }
    });

    window.addEventListener("resize", () => {
      if (floatingDropdown?.classList.contains("lista-contextual-acoes-menu--open") && dropdownTrigger) {
        posicionarDropdown(floatingDropdown, dropdownTrigger);
      }
    });

    window.addEventListener(
      "scroll",
      () => {
        if (floatingDropdown?.classList.contains("lista-contextual-acoes-menu--open")) {
          fecharDropdown();
        }
      },
      true
    );

    window.matchMedia(MQ_MOBILE_TABLET).addEventListener("change", () => {
      fecharDropdown();
      const overlay = document.getElementById("overlay-lista-contextual-acoes");
      if (!isMobileTablet() && overlay && global.GranaGoModal?.isVisible(overlay)) {
        GranaGoModal.close(overlay);
      }
    });
  }

  global.ListaContextual = {
    create(options) {
      return new ListaContextual(options);
    },
    fecharDropdown,
  };
})(window);
