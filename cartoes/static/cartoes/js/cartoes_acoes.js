(function () {
  const MQ_MOBILE_TABLET = "(max-width: 1023px)";
  const overlaySheet = document.getElementById("overlay-cartao-acoes");
  const sheetTitulo = document.getElementById("cartao-acoes-sheet-titulo");
  const sheetMeta = document.getElementById("cartao-acoes-sheet-meta");
  const listaCartoes = document.getElementById("lista-cartoes");

  /** @type {Record<string, string> | null} */
  let cartaoAtivo = null;
  /** @type {HTMLElement | null} */
  let dropdownAberto = null;
  /** @type {HTMLElement | null} */
  let dropdownTrigger = null;

  function isMobileTablet() {
    return window.matchMedia(MQ_MOBILE_TABLET).matches;
  }

  function dadosDoItem(item) {
    if (!item) return null;
    const id = item.getAttribute("data-cartao-id");
    if (!id) return null;
    return {
      id,
      nome: item.getAttribute("data-cartao-nome") || "",
      icone: item.getAttribute("data-cartao-icone") || "bank",
      limite: item.getAttribute("data-cartao-limite") || "",
      limiteLabel: item.getAttribute("data-cartao-limite-label") || "",
      diaFechamento: item.getAttribute("data-cartao-dia-fechamento") || "",
      diaVencimento: item.getAttribute("data-cartao-dia-vencimento") || "",
      contaPadrao: item.getAttribute("data-cartao-conta-padrao") || "",
      faturasUrl: item.getAttribute("data-cartao-faturas-url") || "",
    };
  }

  function formatarMetaSheet(cartao) {
    const partes = [];
    if (cartao.limiteLabel) partes.push(`Limite ${cartao.limiteLabel}`);
    if (cartao.diaFechamento) partes.push(`Fecha dia ${cartao.diaFechamento}`);
    if (cartao.diaVencimento) partes.push(`Vence dia ${cartao.diaVencimento}`);
    return partes.join(" · ");
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

  function fecharDropdown() {
    if (!dropdownAberto) return;
    const menu = dropdownAberto;
    const trigger = dropdownTrigger;
    menu.classList.remove("cartao-acoes-menu--open");
    menu.classList.add("hidden");
    limparEstiloDropdown(menu);
    if (trigger) trigger.setAttribute("aria-expanded", "false");
    if (trigger) {
      const host = trigger.closest(".cartao-item__menu-host");
      if (host && menu.parentElement === document.body) {
        host.appendChild(menu);
      }
    }
    dropdownAberto = null;
    dropdownTrigger = null;
  }

  function abrirDropdown(menu, trigger) {
    fecharDropdown();
    dropdownAberto = menu;
    dropdownTrigger = trigger;
    cartaoAtivo = dadosDoItem(trigger.closest(".cartao-item"));
    document.body.appendChild(menu);
    posicionarDropdown(menu, trigger);
    requestAnimationFrame(() => {
      menu.classList.add("cartao-acoes-menu--open");
    });
    trigger.setAttribute("aria-expanded", "true");
    menu.querySelector(".cartao-acao-item")?.focus();
  }

  function abrirSheet(cartao) {
    if (!overlaySheet || !cartao || !globalThis.GranaGoModal) return;
    cartaoAtivo = cartao;
    if (sheetTitulo) sheetTitulo.textContent = cartao.nome;
    if (sheetMeta) sheetMeta.textContent = formatarMetaSheet(cartao);
    GranaGoModal.open(overlaySheet);
  }

  function fecharSheet() {
    cartaoAtivo = null;
  }

  function executarAcao(acao, cartao) {
    if (!cartao) return;

    if (acao === "faturas") {
      if (cartao.faturasUrl) window.location.assign(cartao.faturasUrl);
      return;
    }

    if (acao === "editar") {
      if (typeof window.abrirModalCartao === "function") {
        window.abrirModalCartao({
          id: cartao.id,
          nome: cartao.nome,
          icone: cartao.icone,
          limite: cartao.limite,
          diaFechamento: cartao.diaFechamento,
          diaVencimento: cartao.diaVencimento,
          contaPadrao: cartao.contaPadrao,
        });
      }
      return;
    }

    if (acao === "excluir" && typeof window.solicitarExclusaoCartao === "function") {
      window.solicitarExclusaoCartao(cartao.id);
    }
  }

  function resolverCartaoDoEvento(target) {
    const item = target.closest(".cartao-item");
    if (item) return dadosDoItem(item);
    return cartaoAtivo;
  }

  function tentarAbrirSheetMobile(target) {
    if (!isMobileTablet()) return false;
    if (target.closest("button, a, input, select, textarea, label, form, [data-cartao-acao]")) {
      return false;
    }
    const item = target.closest(".cartao-item");
    if (!item) return false;
    const cartao = dadosDoItem(item);
    if (!cartao) return false;
    abrirSheet(cartao);
    return true;
  }

  if (overlaySheet && globalThis.GranaGoModal) {
    GranaGoModal.bind(overlaySheet, { onClose: fecharSheet });
  }

  document.addEventListener("click", (event) => {
    const acaoBtn = event.target.closest("[data-cartao-acao]");
    if (acaoBtn) {
      event.preventDefault();
      event.stopPropagation();
      const acao = acaoBtn.dataset.cartaoAcao;
      const cartao = resolverCartaoDoEvento(acaoBtn) || cartaoAtivo;
      const veioDoSheet = overlaySheet?.contains(acaoBtn);
      const veioDoDropdown = !!acaoBtn.closest(".cartao-acoes-menu--dropdown");

      if (veioDoSheet) globalThis.GranaGoModal?.close(overlaySheet);
      if (veioDoDropdown) fecharDropdown();

      executarAcao(acao, cartao);
      return;
    }

    const menuTrigger = event.target.closest(".cartao-menu-trigger");
    if (menuTrigger) {
      event.preventDefault();
      event.stopPropagation();
      const host = menuTrigger.closest(".cartao-item__menu-host");
      const menu = host?.querySelector(".cartao-acoes-menu--dropdown");
      if (!menu) return;

      const aberto = menu === dropdownAberto && menu.classList.contains("cartao-acoes-menu--open");
      if (aberto) fecharDropdown();
      else abrirDropdown(menu, menuTrigger);
      return;
    }

    if (dropdownAberto && !event.target.closest(".cartao-acoes-menu--dropdown, .cartao-menu-trigger")) {
      fecharDropdown();
    }

    if (tentarAbrirSheetMobile(event.target)) {
      event.preventDefault();
    }
  });

  listaCartoes?.addEventListener(
    "touchend",
    (event) => {
      if (!isMobileTablet()) return;
      if (tentarAbrirSheetMobile(event.target)) {
        event.preventDefault();
      }
    },
    { passive: false }
  );

  document.addEventListener(
    "keydown",
    (event) => {
      if (!dropdownAberto || event.key !== "Escape") return;
      event.preventDefault();
      event.stopImmediatePropagation();
      const trigger = dropdownTrigger;
      fecharDropdown();
      trigger?.focus();
    },
    true
  );

  document.addEventListener("keydown", (event) => {
    if (dropdownAberto) {
      const items = [...dropdownAberto.querySelectorAll(".cartao-acao-item")];
      const idx = items.indexOf(document.activeElement);
      if (event.key === "ArrowDown" && items.length) {
        event.preventDefault();
        items[(idx + 1) % items.length]?.focus();
        return;
      }
      if (event.key === "ArrowUp" && items.length) {
        event.preventDefault();
        items[(idx - 1 + items.length) % items.length]?.focus();
        return;
      }
    }

    if (event.key !== "Enter" && event.key !== " ") return;
    if (!isMobileTablet()) return;
    if (event.target.closest(".cartao-menu-trigger, [data-cartao-acao]")) return;

    const item = event.target.closest(".cartao-item");
    if (!item) return;

    event.preventDefault();
    const cartao = dadosDoItem(item);
    if (cartao) abrirSheet(cartao);
  });

  window.addEventListener("resize", () => {
    if (dropdownAberto && dropdownTrigger) {
      posicionarDropdown(dropdownAberto, dropdownTrigger);
    }
  });

  window.addEventListener(
    "scroll",
    () => {
      if (dropdownAberto) fecharDropdown();
    },
    true
  );

  window.matchMedia(MQ_MOBILE_TABLET).addEventListener("change", () => {
    fecharDropdown();
    if (!isMobileTablet() && overlaySheet && globalThis.GranaGoModal?.isVisible(overlaySheet)) {
      GranaGoModal.close(overlaySheet);
    }
  });
})();
