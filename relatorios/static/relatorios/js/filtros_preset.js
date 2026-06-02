/**
 * Exibe campos De/Até apenas quando o preset é "Personalizado".
 */
(() => {
  const initForm = (form) => {
    const preset = form.querySelector('[data-filtro-preset]');
    const dates = form.querySelector('[data-filtro-datas]');
    if (!preset || !dates) return;

    const inicio = dates.querySelector('[name="inicio"]');
    const fim = dates.querySelector('[name="fim"]');

    const sync = () => {
      const custom = preset.value === 'custom';
      dates.classList.toggle('hidden', !custom);
      dates.setAttribute('aria-hidden', custom ? 'false' : 'true');
      if (inicio) inicio.disabled = !custom;
      if (fim) fim.disabled = !custom;
    };

    preset.addEventListener('change', sync);
    sync();
  };

  const boot = () => {
    document.querySelectorAll('#form-filtros-panel, #form-filtros-bar').forEach(initForm);
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
