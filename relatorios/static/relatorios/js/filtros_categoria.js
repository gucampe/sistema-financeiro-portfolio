/**
 * Seletor de categorias — dropdown (barra) ou picker (painel mobile/desktop).
 */
(() => {
  const MAX_CHIPS_VISIBLE = 2;
  const OPEN = new Set();

  const bindEscape = () => {
    if (bindEscape.done) return;
    bindEscape.done = true;
    document.addEventListener(
      'keydown',
      (e) => {
        if (e.key !== 'Escape' || !OPEN.size) return;
        OPEN.forEach((close) => close());
        OPEN.clear();
        e.preventDefault();
        e.stopImmediatePropagation();
      },
      true
    );
  };

  const initRoot = (root) => {
    if (root.dataset.catInit === '1') return;
    root.dataset.catInit = '1';

    const mode = root.dataset.catMode || 'dropdown';
    const trigger = root.querySelector('[data-cat-trigger]');
    const triggerLabel = root.querySelector('[data-cat-trigger-label]');
    const triggerCount = root.querySelector('[data-cat-trigger-count]');
    const chips = root.querySelector('[data-cat-chips]');
    const dropdown = root.querySelector('[data-cat-dropdown]');
    const picker = root.querySelector('[data-cat-picker]');
    const searches = () => Array.from(root.querySelectorAll('[data-cat-search]'));
    const checkboxes = () => Array.from(root.querySelectorAll('input[name="categoria"]'));

    if (!trigger || !chips) return;

    const selectedItems = () =>
      checkboxes()
        .filter((cb) => cb.checked)
        .map((cb) => ({
          id: cb.value,
          label: cb.closest('label')?.querySelector('span:last-child')?.textContent?.trim() || '',
        }));

    const syncUI = () => {
      const selected = selectedItems();
      const count = selected.length;
      if (triggerCount) triggerCount.textContent = String(count);
      if (triggerLabel) {
        triggerLabel.textContent = count
          ? `${count} categoria${count > 1 ? 's' : ''} selecionada${count > 1 ? 's' : ''}`
          : 'Selecionar categorias';
      }

      chips.innerHTML = '';
      if (!count) return;

      const visible = selected.slice(0, MAX_CHIPS_VISIBLE);
      visible.forEach((item) => {
        chips.appendChild(buildChip(item));
      });

      const rest = count - visible.length;
      if (rest > 0) {
        const more = document.createElement('span');
        more.className =
          'inline-flex items-center rounded-full bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-800';
        more.textContent = `+${rest} categoria${rest > 1 ? 's' : ''}`;
        chips.appendChild(more);
      }
    };

    const buildChip = (item) => {
      const chip = document.createElement('span');
      chip.className =
        'inline-flex max-w-[calc(100%-0.25rem)] items-center gap-1 rounded-full bg-gray-100 py-1 pl-2.5 pr-1 text-xs text-gray-700';
      const text = document.createElement('span');
      text.className = 'truncate';
      text.style.maxWidth = '8.5rem';
      text.textContent = item.label;
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className =
        'inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-gray-500 hover:bg-gray-200/80 hover:text-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40';
      remove.setAttribute('data-remove-cat', item.id);
      remove.setAttribute('aria-label', `Remover ${item.label}`);
      remove.textContent = '×';
      chip.appendChild(text);
      chip.appendChild(remove);
      return chip;
    };

    const filterOptions = () => {
      const activeSearch = searches().find((el) => {
        const pickerOpen = picker?.dataset.open === 'true';
        if (picker && pickerOpen) return picker.contains(el);
        return dropdown?.dataset.open === 'true' && dropdown.contains(el);
      });
      const term = (activeSearch?.value || '').toLowerCase().trim();
      root.querySelectorAll('[data-cat-option]').forEach((opt) => {
        const name = opt.getAttribute('data-cat-name') || '';
        opt.classList.toggle('hidden', !!term && !name.includes(term));
      });
      root.querySelectorAll('[data-cat-group]').forEach((group) => {
        const hasVisible = !!group.querySelector('[data-cat-option]:not(.hidden)');
        group.classList.toggle('hidden', !hasVisible);
      });
    };

    searches().forEach((search) => search.addEventListener('input', filterOptions));
    checkboxes().forEach((cb) => cb.addEventListener('change', syncUI));

    chips.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-remove-cat]');
      if (!btn) return;
      const cb = root.querySelector(`input[name="categoria"][value="${btn.getAttribute('data-remove-cat')}"]`);
      if (!cb) return;
      cb.checked = false;
      syncUI();
    });

    if (mode === 'dropdown' && dropdown) {
      const closeDropdown = () => {
        dropdown.dataset.open = 'false';
        dropdown.setAttribute('aria-hidden', 'true');
        trigger.setAttribute('aria-expanded', 'false');
        OPEN.delete(closeDropdown);
      };

      const openDropdown = () => {
        OPEN.forEach((close) => close());
        OPEN.clear();
        dropdown.dataset.open = 'true';
        dropdown.setAttribute('aria-hidden', 'false');
        trigger.setAttribute('aria-expanded', 'true');
        OPEN.add(closeDropdown);
        dropdown.querySelector('[data-cat-search]')?.focus();
      };

      trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        if (dropdown.dataset.open === 'true') closeDropdown();
        else openDropdown();
      });

      document.addEventListener('click', (e) => {
        if (!root.contains(e.target)) closeDropdown();
      });

      bindEscape();
    }

    if (mode === 'picker' && picker) {
      const backBtn = picker.querySelector('[data-cat-picker-back]');
      const doneBtn = picker.querySelector('[data-cat-picker-done]');
      const pickerBackdrop = picker.querySelector('[data-cat-picker-backdrop]');

      const closePicker = () => {
        picker.dataset.open = 'false';
        picker.setAttribute('aria-hidden', 'true');
        trigger.setAttribute('aria-expanded', 'false');
        OPEN.delete(closePicker);
      };

      const openPicker = () => {
        OPEN.forEach((close) => close());
        OPEN.clear();
        picker.dataset.open = 'true';
        picker.setAttribute('aria-hidden', 'false');
        trigger.setAttribute('aria-expanded', 'true');
        OPEN.add(closePicker);
        picker.querySelector('[data-cat-search]')?.focus();
      };

      trigger.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        openPicker();
      });

      const finish = (e) => {
        e?.preventDefault();
        closePicker();
        trigger.focus();
      };

      backBtn?.addEventListener('click', finish);
      doneBtn?.addEventListener('click', finish);
      pickerBackdrop?.addEventListener('click', finish);

      bindEscape();
    }

    syncUI();
    filterOptions();
  };

  const boot = () => document.querySelectorAll('[data-categoria-filter]').forEach(initRoot);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
