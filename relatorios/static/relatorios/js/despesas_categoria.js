/**
 * Por categoria — expandir/recolher detalhes sem recarregar a página.
 */
(() => {
  const lista = document.getElementById('lista-categorias-analise');
  if (!lista) return;

  const closeOthers = (exceptId) => {
    lista.querySelectorAll('[data-cat-toggle]').forEach((btn) => {
      const panelId = btn.getAttribute('aria-controls');
      if (!panelId || panelId === exceptId) return;
      const panel = document.getElementById(panelId);
      btn.setAttribute('aria-expanded', 'false');
      panel?.classList.add('hidden');
      btn.querySelector('.cat-analise-item__chevron')?.classList.remove('rotate-180');
    });
  };

  lista.querySelectorAll('[data-cat-toggle]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const panelId = btn.getAttribute('aria-controls');
      const panel = panelId ? document.getElementById(panelId) : null;
      if (!panel) return;

      const isOpen = !panel.classList.contains('hidden');
      if (isOpen) {
        panel.classList.add('hidden');
        btn.setAttribute('aria-expanded', 'false');
        btn.querySelector('.cat-analise-item__chevron')?.classList.remove('rotate-180');
        return;
      }

      closeOthers(panelId);
      panel.classList.remove('hidden');
      btn.setAttribute('aria-expanded', 'true');
      btn.querySelector('.cat-analise-item__chevron')?.classList.add('rotate-180');
    });
  });
})();
