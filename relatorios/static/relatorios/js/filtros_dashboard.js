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

  let open = false;
  let bodyLocked = false;
  let lastOpenBtn = openBtns[0];

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
      lockScroll();
      closeBtn?.focus();
    } else {
      unlockScroll();
      window.resizeDashboardCharts?.();
    }
  };

  const toggle = () => setOpen(!open);
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

  window.addEventListener('resize', () => {
    if (open) close();
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

  const updateFades = () => {
    if (!window.matchMedia('(max-width: 1023px)').matches) return;
    const max = scroll.scrollWidth - scroll.clientWidth;
    const x = scroll.scrollLeft;
    if (fadeL) fadeL.style.opacity = x > 4 ? '1' : '0';
    if (fadeR) fadeR.style.opacity = max - x > 4 ? '1' : '0';
  };

  scroll.addEventListener('scroll', updateFades, { passive: true });
  window.addEventListener('resize', updateFades);
  updateFades();
})();
