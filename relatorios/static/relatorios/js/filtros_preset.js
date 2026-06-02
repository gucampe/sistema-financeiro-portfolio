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

  const syncOrcamentosAnoMes = (form) => {
    const root = document.getElementById('orcamentos-root');
    if (!root || form.id !== 'form-filtros-panel') return;

    const ensureHidden = (name, value) => {
      let input = form.querySelector(`input[type="hidden"][name="${name}"]`);
      if (!input) {
        input = document.createElement('input');
        input.type = 'hidden';
        input.name = name;
        form.appendChild(input);
      }
      input.value = String(value);
    };

    const fimInput = form.querySelector('[name="fim"]:not(:disabled)');
    if (fimInput?.value) {
      const d = new Date(`${fimInput.value}T12:00:00`);
      ensureHidden('ano', d.getFullYear());
      ensureHidden('mes', d.getMonth() + 1);
      return;
    }

    if (root.dataset.ano && root.dataset.mes) {
      ensureHidden('ano', root.dataset.ano);
      ensureHidden('mes', root.dataset.mes);
    }
  };

  const boot = () => {
    document.querySelectorAll('#form-filtros-panel, #form-filtros-bar').forEach(initForm);

    const panelForm = document.getElementById('form-filtros-panel');
    panelForm?.addEventListener('submit', () => syncOrcamentosAnoMes(panelForm));
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
