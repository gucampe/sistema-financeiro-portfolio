/**
 * Portal de filtros — painel lateral compartilhado nas páginas analíticas.
 */
(() => {
  const portal = document.getElementById('filtros-portal');
  if (!portal) return;

  const backdrop = document.getElementById('filtros-portal-backdrop');
  const panel = document.getElementById('filtros-portal-panel');
  const openBtns = document.querySelectorAll('.js-abrir-filtros-portal');
  const closeBtn = document.getElementById('btn-fechar-filtros-portal');

  if (!panel || openBtns.length === 0) return;

  const DESKTOP_MQ = window.matchMedia('(min-width: 1024px)');
  const PANEL_GAP_PX = 12;
  const MIN_INSET_PX = 16;

  const getLayoutAnchor = () =>
    portal.closest('[data-filtros-layout-anchor]') ||
    document.querySelector('[data-filtros-layout-anchor]');

  const getVerticalAnchor = () => {
    const layout = getLayoutAnchor();
    const scoped = layout
      ? layout.querySelector(
          '[data-filtros-vertical-anchor], #secao-resumo-hero, #orcamento-hero-resumo'
        )
      : null;
    return (
      scoped ||
      document.querySelector(
        '[data-filtros-vertical-anchor], #secao-resumo-hero, #orcamento-hero-resumo'
      )
    );
  };

  const updatePanelLayout = () => {
    if (!DESKTOP_MQ.matches) {
      portal.style.removeProperty('--filtros-panel-inset-right');
      portal.style.removeProperty('--filtros-panel-top');
      portal.style.removeProperty('--filtros-panel-max-height');
      return;
    }

    const anchor = getLayoutAnchor();
    if (!anchor) {
      portal.style.setProperty('--filtros-panel-inset-right', '1rem');
    } else {
      const rect = anchor.getBoundingClientRect();
      const insetRight = Math.max(MIN_INSET_PX, window.innerWidth - rect.right + PANEL_GAP_PX);
      portal.style.setProperty('--filtros-panel-inset-right', `${Math.round(insetRight)}px`);
    }

    const vAnchor = getVerticalAnchor();
    const bottomGapPx = 16;
    if (vAnchor) {
      const top = Math.max(0, Math.round(vAnchor.getBoundingClientRect().top));
      portal.style.setProperty('--filtros-panel-top', `${top}px`);
      portal.style.setProperty(
        '--filtros-panel-max-height',
        `calc(100dvh - ${top}px - ${bottomGapPx}px)`
      );
    } else {
      portal.style.setProperty('--filtros-panel-top', '1rem');
      portal.style.setProperty('--filtros-panel-max-height', 'calc(100dvh - 2rem)');
    }
  };

  let open = false;
  let bodyLocked = false;
  let lastOpenBtn = openBtns[0];
  let layoutObserver = null;

  const setButtonsExpanded = (expanded) => {
    openBtns.forEach((btn) => btn.setAttribute('aria-expanded', expanded ? 'true' : 'false'));
  };

  const lockScroll = () => {
    if (!document.documentElement.classList.contains('sidebar-open')) {
      globalThis.GranaGoModal?.lockScroll?.();
      bodyLocked = true;
    }
  };

  const unlockScroll = () => {
    if (bodyLocked && !document.documentElement.classList.contains('sidebar-open')) {
      globalThis.GranaGoModal?.unlockScroll?.();
    }
    bodyLocked = false;
  };

  const setOpen = (next) => {
    open = next;
    portal.dataset.open = next ? 'true' : 'false';
    portal.setAttribute('aria-hidden', next ? 'false' : 'true');
    setButtonsExpanded(next);
    if (next) {
      updatePanelLayout();
      lockScroll();
      closeBtn?.focus();
    } else {
      unlockScroll();
      window.resizeDashboardCharts?.();
    }
  };

  const bindLayoutTracking = () => {
    const anchor = getLayoutAnchor();
    if (!anchor) return;
    layoutObserver?.disconnect();
    layoutObserver = new ResizeObserver(() => updatePanelLayout());
    layoutObserver.observe(anchor);
    const vAnchor = getVerticalAnchor();
    if (vAnchor && vAnchor !== anchor) layoutObserver.observe(vAnchor);
    const main = document.getElementById('mainContent');
    if (main) layoutObserver.observe(main);
  };

  updatePanelLayout();
  bindLayoutTracking();
  window.addEventListener('resize', () => {
    updatePanelLayout();
    if (open && !DESKTOP_MQ.matches) close();
  });
  window.addEventListener(
    'scroll',
    () => {
      if (open && DESKTOP_MQ.matches) updatePanelLayout();
    },
    { passive: true, capture: true }
  );
  DESKTOP_MQ.addEventListener('change', updatePanelLayout);

  const toggle = () => {
    if (!open && DESKTOP_MQ.matches) updatePanelLayout();
    setOpen(!open);
  };
  const close = () => setOpen(false);

  openBtns.forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      lastOpenBtn = btn;
      toggle();
    });
  });

  closeBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    close();
    lastOpenBtn.focus();
  });

  backdrop?.addEventListener('click', () => {
    close();
    lastOpenBtn.focus();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape' || !open) return;
    if (document.querySelector('.cat-picker[data-open="true"]')) return;
    close();
    lastOpenBtn.focus();
  });

})();

/**
 * Fade nas abas mobile ao rolar horizontalmente.
 */
(() => {
  const track = document.querySelector('.relatorios-tabs__track');
  const scroll = document.querySelector('.relatorios-tabs__scroll');
  if (!track || !scroll) return;

  const fadeL = track.querySelector('.relatorios-tabs__fade--left');
  const fadeR = track.querySelector('.relatorios-tabs__fade--right');

  const MOBILE_TABS_MQ = '(max-width: 1023px)';

  const scrollActiveTab = () => {
    if (!window.matchMedia(MOBILE_TABS_MQ).matches) return;
    const active = scroll.querySelector('.relatorios-tab.is-active');
    if (!active) return;

    const target =
      active.offsetLeft - scroll.clientWidth / 2 + active.offsetWidth / 2;
    scroll.scrollLeft = Math.max(
      0,
      Math.min(target, scroll.scrollWidth - scroll.clientWidth)
    );
  };

  const updateFades = () => {
    if (!window.matchMedia(MOBILE_TABS_MQ).matches) return;
    const max = scroll.scrollWidth - scroll.clientWidth;
    const x = scroll.scrollLeft;
    if (fadeL) fadeL.style.opacity = x > 4 ? '1' : '0';
    if (fadeR) fadeR.style.opacity = max - x > 4 ? '1' : '0';
  };

  const syncTabsScroll = () => {
    scrollActiveTab();
    updateFades();
  };

  scroll.addEventListener('scroll', updateFades, { passive: true });
  window.addEventListener('resize', syncTabsScroll);
  requestAnimationFrame(syncTabsScroll);
})();
