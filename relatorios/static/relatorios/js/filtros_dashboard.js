/**
 * Portal de filtros da Visão Geral — mobile sheet / notebook overlay / XL drawer.
 */
(() => {
  const portal = document.getElementById('filtros-portal');
  if (!portal) return;

  const backdrop = document.getElementById('filtros-portal-backdrop');
  const panel = document.getElementById('filtros-portal-panel');
  const openBtn = document.getElementById('btn-abrir-filtros');
  const closeBtn = document.getElementById('btn-fechar-filtros-portal');

  if (!panel || !openBtn) return;

  let open = false;
  let bodyLocked = false;

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
    openBtn.setAttribute('aria-expanded', next ? 'true' : 'false');
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

  openBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    toggle();
  });

  closeBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    close();
    openBtn.focus();
  });

  backdrop?.addEventListener('click', () => {
    close();
    openBtn.focus();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape' || !open) return;
    if (document.querySelector('.cat-picker[data-open="true"]')) return;
    close();
    openBtn.focus();
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
