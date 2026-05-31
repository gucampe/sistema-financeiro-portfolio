/**
 * Modais GranaGo — backdrop, Escape, data-modal-close, open/close, foco e ARIA.
 *
 * Markup: .modal-overlay[data-modal] > .modal-panel[data-modal-panel]
 * Fechar: data-modal-close no botão | GranaGoModal.close(id)
 * Abrir:  GranaGoModal.open(id, { trigger: elemento })
 * Lógica: GranaGoModal.bind(overlay, { onOpen, onClose, onEscape })
 */
(function (global) {
  const PANEL_SELECTOR = "[data-modal-panel], .modal-panel";
  const BACKDROP_SELECTOR = "[data-modal-backdrop]";
  const CLOSE_SELECTOR = "[data-modal-close]";
  const OVERLAY_SELECTOR =
    "[data-modal], .modal-overlay, [id^='overlay-'], [id^='modal-confirmar']";

  const FOCUSABLE_SELECTOR =
    'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

  /** Mesmo fade do modal de transação (opacity 300ms + hidden após o fade). */
  const DEFAULT_FADE_MS = 300;
  const PANEL_SCALE_MS = 300;

  /** @type {Map<HTMLElement, { onOpen?: (el: HTMLElement) => void, onClose?: (el: HTMLElement) => void, onEscape?: (e: KeyboardEvent) => boolean | void, fadeMs?: number }>} */
  const registry = new Map();
  /** @type {WeakMap<HTMLElement, HTMLElement>} */
  const lastFocus = new WeakMap();
  /** @type {WeakMap<HTMLElement, (e: KeyboardEvent) => void>} */
  const focusTrapHandlers = new WeakMap();

  let handlersReady = false;
  let bodyScrollLock = 0;
  /** @type {{ scrollY: number } | null} */
  let scrollLockSnapshot = null;

  function lockBodyScroll() {
    bodyScrollLock += 1;
    if (bodyScrollLock !== 1) return;

    const scrollY = window.scrollY;
    const viewportWidth = document.documentElement.clientWidth;

    scrollLockSnapshot = { scrollY };

    document.body.style.position = "fixed";
    document.body.style.top = `-${scrollY}px`;
    document.body.style.left = "0";
    document.body.style.right = "0";
    document.body.style.width = `${viewportWidth}px`;
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";
  }

  function unlockBodyScroll() {
    bodyScrollLock = Math.max(0, bodyScrollLock - 1);
    if (bodyScrollLock !== 0 || !scrollLockSnapshot) return;

    const { scrollY } = scrollLockSnapshot;
    scrollLockSnapshot = null;

    document.body.style.position = "";
    document.body.style.top = "";
    document.body.style.left = "";
    document.body.style.right = "";
    document.body.style.width = "";
    document.body.style.overflow = "";
    document.documentElement.style.overflow = "";

    window.scrollTo(0, scrollY);
  }

  function resolveOverlay(overlayOrId) {
    if (!overlayOrId) return null;
    if (overlayOrId instanceof HTMLElement) return overlayOrId;
    if (typeof overlayOrId === "string") {
      return document.getElementById(overlayOrId);
    }
    return null;
  }

  function isVisible(overlay) {
    if (!overlay || !(overlay instanceof HTMLElement)) return false;
    if (overlay.classList.contains("hidden")) return false;
    if (overlay.getAttribute("aria-hidden") === "true") return false;
    const style = window.getComputedStyle(overlay);
    if (style.display === "none" || style.visibility === "hidden") return false;
    return true;
  }

  function getZIndex(el) {
    const z = parseInt(window.getComputedStyle(el).zIndex, 10);
    return Number.isFinite(z) ? z : 0;
  }

  function getOpenOverlays() {
    return [...document.querySelectorAll(OVERLAY_SELECTOR)]
      .filter(isVisible)
      .sort((a, b) => getZIndex(b) - getZIndex(a));
  }

  function getPanel(overlay) {
    const panel = overlay.querySelector(PANEL_SELECTOR);
    if (panel) return panel;

    const importPanel = overlay.querySelector(
      "#import-ofx-panel, #import-planilha-panel"
    );
    if (importPanel) return importPanel;

    for (const child of overlay.children) {
      if (!(child instanceof HTMLElement)) continue;
      if (child.matches(BACKDROP_SELECTOR)) continue;
      if (child.dataset.modalBackdrop !== undefined) continue;
      if (
        child.classList.contains("absolute") &&
        child.classList.contains("inset-0") &&
        !child.querySelector(PANEL_SELECTOR)
      ) {
        continue;
      }
      return child;
    }
    return null;
  }

  function getFocusable(container) {
    return [...container.querySelectorAll(FOCUSABLE_SELECTOR)].filter((el) => {
      if (!(el instanceof HTMLElement)) return false;
      return el.offsetParent !== null || el === document.activeElement;
    });
  }

  function getFadeMs(overlay) {
    if (overlay.dataset.modalFade === "0") return 0;
    const entry = registry.get(overlay);
    if (entry?.fadeMs != null) return entry.fadeMs;
    const attr = overlay.dataset.modalFade;
    if (attr != null && attr !== "") {
      const parsed = parseInt(attr, 10);
      return Number.isFinite(parsed) ? parsed : DEFAULT_FADE_MS;
    }
    return DEFAULT_FADE_MS;
  }

  function usesOpacityTransition(overlay) {
    return getFadeMs(overlay) > 0;
  }

  function ensureTransitionClasses(overlay) {
    if (getFadeMs(overlay) <= 0) return;
    if (!overlay.dataset.modalFade) {
      overlay.dataset.modalFade = String(DEFAULT_FADE_MS);
    }
    overlay.classList.add("transition-opacity");
    if (!overlay.classList.contains("duration-300")) {
      overlay.classList.add("duration-300");
    }
    if (
      !overlay.classList.contains("opacity-100") &&
      overlay.classList.contains("hidden")
    ) {
      overlay.classList.add("opacity-0");
    }
  }

  function panelScaleEnabled(overlay) {
    return overlay.dataset.modalPanelScale !== "0";
  }

  function ensurePanelTransitionClasses(panel) {
    panel.classList.add("transform", "transition-all", "duration-300");
  }

  function setPanelScaleClosed(panel) {
    panel.classList.remove("scale-100");
    panel.classList.add("scale-95");
  }

  function animatePanelOpen(overlay) {
    if (!panelScaleEnabled(overlay)) return;
    const panel = getPanel(overlay);
    if (!panel) return;
    ensurePanelTransitionClasses(panel);
    setPanelScaleClosed(panel);
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        panel.classList.remove("scale-95");
        panel.classList.add("scale-100");
      });
    });
  }

  function animatePanelClose(overlay) {
    if (!panelScaleEnabled(overlay)) return;
    const panel = getPanel(overlay);
    if (!panel) return;
    ensurePanelTransitionClasses(panel);
    panel.classList.remove("scale-100");
    panel.classList.add("scale-95");
  }

  function setAriaOpen(overlay, open) {
    const panel = getPanel(overlay);
    if (open) {
      overlay.setAttribute("aria-hidden", "false");
      overlay.setAttribute("aria-modal", "true");
      if (panel) {
        if (!panel.hasAttribute("role")) panel.setAttribute("role", "dialog");
        panel.setAttribute("aria-modal", "true");
        const labelledBy = overlay.dataset.modalLabelledby;
        if (labelledBy) panel.setAttribute("aria-labelledby", labelledBy);
      }
    } else {
      overlay.setAttribute("aria-hidden", "true");
      overlay.removeAttribute("aria-modal");
      if (panel) {
        panel.removeAttribute("aria-modal");
      }
    }
  }

  function activateFocusTrap(overlay) {
    deactivateFocusTrap(overlay);
    const handler = (e) => {
      if (e.key !== "Tab") return;
      if (!isVisible(overlay)) return;
      const open = getOpenOverlays();
      if (!open.length || open[0] !== overlay) return;

      const panel = getPanel(overlay);
      if (!panel) return;

      const focusable = getFocusable(panel);
      if (!focusable.length) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;

      if (e.shiftKey) {
        if (active === first || !panel.contains(active)) {
          e.preventDefault();
          last.focus();
        }
      } else if (active === last) {
        e.preventDefault();
        first.focus();
      }
    };
    focusTrapHandlers.set(overlay, handler);
    document.addEventListener("keydown", handler, true);
  }

  function deactivateFocusTrap(overlay) {
    const handler = focusTrapHandlers.get(overlay);
    if (handler) {
      document.removeEventListener("keydown", handler, true);
      focusTrapHandlers.delete(overlay);
    }
  }

  function focusPanel(overlay) {
    const panel = getPanel(overlay);
    if (!panel) return;
    const focusable = getFocusable(panel);
    if (focusable.length) {
      focusable[0].focus();
      return;
    }
    if (!panel.hasAttribute("tabindex")) {
      panel.setAttribute("tabindex", "-1");
    }
    panel.focus();
  }

  function restoreFocus(overlay) {
    const el = lastFocus.get(overlay);
    lastFocus.delete(overlay);
    if (el && typeof el.focus === "function") {
      requestAnimationFrame(() => {
        try {
          el.focus({ preventScroll: true });
        } catch (_) {
          el.focus();
        }
      });
    }
  }

  function defaultOpen(overlay) {
    ensureTransitionClasses(overlay);
    overlay.classList.remove("hidden");
    setAriaOpen(overlay, true);

    if (usesOpacityTransition(overlay)) {
      overlay.classList.remove("opacity-100");
      overlay.classList.add("opacity-0");
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          overlay.classList.remove("opacity-0");
          overlay.classList.add("opacity-100");
        });
      });
    }
    animatePanelOpen(overlay);
  }

  function defaultClose(overlay, onFinished) {
    const fadeMs = getFadeMs(overlay);

    const finish = () => {
      overlay.classList.add("hidden");
      setAriaOpen(overlay, false);
      if (usesOpacityTransition(overlay)) {
        overlay.classList.remove("opacity-100");
        overlay.classList.add("opacity-0");
      }
      if (typeof onFinished === "function") onFinished();
    };

    if (fadeMs > 0 && usesOpacityTransition(overlay)) {
      animatePanelClose(overlay);
      overlay.classList.remove("opacity-100");
      overlay.classList.add("opacity-0");
      const closeMs = Math.max(fadeMs, PANEL_SCALE_MS);
      setTimeout(finish, closeMs);
    } else {
      animatePanelClose(overlay);
      finish();
    }
  }

  function isBackdropClick(overlay, target) {
    if (!(target instanceof Node) || !overlay.contains(target)) return false;
    if (target === overlay) return true;

    if (target instanceof HTMLElement) {
      if (target.matches(BACKDROP_SELECTOR)) return true;
      if (target.dataset.modalBackdrop !== undefined) return true;
    }

    const panel = getPanel(overlay);
    if (panel && (target === panel || panel.contains(target))) return false;

    return true;
  }

  function open(overlayOrId, options) {
    const overlay = resolveOverlay(overlayOrId);
    if (!overlay) return;

    const opts = options || {};
    const trigger = opts.trigger;
    if (trigger instanceof HTMLElement) {
      lastFocus.set(overlay, trigger);
    } else if (document.activeElement instanceof HTMLElement) {
      lastFocus.set(overlay, document.activeElement);
    }

    defaultOpen(overlay);
    const entry = registry.get(overlay);
    if (entry?.onOpen) {
      entry.onOpen(overlay);
    }

    lockBodyScroll();
    activateFocusTrap(overlay);
    setAriaOpen(overlay, true);
    requestAnimationFrame(() => focusPanel(overlay));
  }

  function closeOverlay(overlayOrId) {
    const overlay = resolveOverlay(overlayOrId);
    if (!overlay || !isVisible(overlay)) {
      const el = resolveOverlay(overlayOrId);
      if (el) deactivateFocusTrap(el);
      return;
    }

    deactivateFocusTrap(overlay);

    const entry = registry.get(overlay);
    const afterClose = () => {
      unlockBodyScroll();
      restoreFocus(overlay);
    };

    if (entry?.onClose) {
      entry.onClose(overlay);
    }

    if (isVisible(overlay)) {
      defaultClose(overlay, afterClose);
    } else {
      afterClose();
    }
  }

  function bind(overlay, options) {
    const el = resolveOverlay(overlay);
    if (!el) return;
    if (!el.hasAttribute("data-modal")) {
      el.setAttribute("data-modal", "");
    }
    if (!el.hasAttribute("aria-hidden")) {
      el.setAttribute("aria-hidden", "true");
    }
    ensureTransitionClasses(el);
    const panel = getPanel(el);
    if (panel && panelScaleEnabled(el)) {
      ensurePanelTransitionClasses(panel);
      if (el.classList.contains("hidden")) {
        setPanelScaleClosed(panel);
      }
    }
    const prev = registry.get(el) || {};
    registry.set(el, {
      onOpen: options?.onOpen ?? prev.onOpen,
      onClose: options?.onClose ?? prev.onClose,
      onEscape: options?.onEscape ?? prev.onEscape,
      fadeMs: options?.fadeMs ?? prev.fadeMs,
    });
  }

  function unbind(overlay) {
    const el = resolveOverlay(overlay);
    if (el) registry.delete(el);
  }

  function findOverlayFromCloseButton(btn) {
    return btn.closest(OVERLAY_SELECTOR);
  }

  function scan() {
    document.querySelectorAll(OVERLAY_SELECTOR).forEach((el) => {
      if (!(el instanceof HTMLElement)) return;
      if (!registry.has(el)) {
        bind(el, {});
      }
    });
  }

  function initHandlers() {
    if (handlersReady) return;
    handlersReady = true;

    document.addEventListener(
      "click",
      (e) => {
        const closeBtn = e.target.closest(CLOSE_SELECTOR);
        if (closeBtn) {
          const overlay = findOverlayFromCloseButton(closeBtn);
          if (overlay && isVisible(overlay)) {
            closeOverlay(overlay);
            e.preventDefault();
            e.stopPropagation();
            return;
          }
        }

        const open = getOpenOverlays();
        if (!open.length) return;

        for (const overlay of open) {
          if (!isBackdropClick(overlay, e.target)) continue;
          closeOverlay(overlay);
          e.preventDefault();
          e.stopPropagation();
          return;
        }
      },
      false
    );

    document.addEventListener(
      "keydown",
      (e) => {
        if (e.key !== "Escape") return;

        const open = getOpenOverlays();
        if (!open.length) return;

        const top = open[0];
        const entry = registry.get(top);

        if (entry?.onEscape) {
          const allowClose = entry.onEscape(e);
          if (allowClose === false) {
            e.preventDefault();
            e.stopPropagation();
            return;
          }
        }

        closeOverlay(top);
        e.preventDefault();
        e.stopPropagation();
      },
      false
    );
  }

  let scanTimer = null;
  function scheduleScan() {
    clearTimeout(scanTimer);
    scanTimer = setTimeout(scan, 30);
  }

  function init() {
    initHandlers();
    scan();
  }

  const observer = new MutationObserver(scheduleScan);
  function startObserver() {
    if (!document.body) return;
    observer.observe(document.body, { childList: true, subtree: true });
  }

  global.GranaGoModal = {
    bind,
    unbind,
    open,
    close: closeOverlay,
    lockScroll: lockBodyScroll,
    unlockScroll: unlockBodyScroll,
    isVisible,
    getOpenOverlays,
    getPanel,
    init,
    scan,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      init();
      startObserver();
    });
  } else {
    init();
    startObserver();
  }
})(window);
