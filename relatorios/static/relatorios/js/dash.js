function parseJsonScript(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  try {
    return JSON.parse(el.textContent);
  } catch {
    return null;
  }
}

function moedaTick(value) {
  return `R$ ${Number(value).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const CORES_GRAFICO_CATEGORIAS = [
  '#3B82F6',
  '#10B981',
  '#F59E0B',
  '#EF4444',
  '#8B5CF6',
  '#EC4899',
  '#06B6D4',
  '#14B8A6',
  '#F97316',
  '#6366F1',
];

function coresDistintasGrafico(items) {
  const usadas = new Set();
  let pi = 0;
  return items.map((item, index) => {
    let cor = (item.cor || '').trim();
    if (!cor || usadas.has(cor)) {
      for (let n = 0; n < CORES_GRAFICO_CATEGORIAS.length; n += 1) {
        const candidata = CORES_GRAFICO_CATEGORIAS[pi % CORES_GRAFICO_CATEGORIAS.length];
        pi += 1;
        if (!usadas.has(candidata)) {
          cor = candidata;
          break;
        }
      }
      if (!cor || usadas.has(cor)) {
        cor = CORES_GRAFICO_CATEGORIAS[index % CORES_GRAFICO_CATEGORIAS.length];
      }
    }
    usadas.add(cor);
    return cor;
  });
}

const DASHBOARD_MQ_LG = '(min-width: 1024px)';

function initDashboardMasonry() {
  const container = document.getElementById('dashboard-masonry');
  if (!container) return () => {};

  const mq = window.matchMedia(DASHBOARD_MQ_LG);
  const items = () => [...container.querySelectorAll('.dashboard-masonry-item')];
  let frame = null;

  const clearLayout = () => {
    container.style.height = '';
    container.style.width = '';
    items().forEach((item) => {
      item.style.position = '';
      item.style.top = '';
      item.style.left = '';
      item.style.width = '';
      item.style.visibility = '';
    });
  };

  const containerWidth = () => {
    container.style.width = '100%';
    const own = container.getBoundingClientRect().width;
    if (own > 0) return own;
    const parent = container.parentElement;
    return parent ? parent.getBoundingClientRect().width : 0;
  };

  const layout = (options = {}) => {
    const { reveal = true } = options;
    const cards = items();
    if (!cards.length) return;

    if (!mq.matches) {
      clearLayout();
      if (reveal) container.classList.remove('dashboard-masonry--pending');
      return;
    }

    const gap =
      Number.parseFloat(getComputedStyle(container).gap) ||
      Number.parseFloat(getComputedStyle(container).rowGap) ||
      24;
    const width = containerWidth();
    if (width <= 0) return;

    const colWidth = (width - gap) / 2;
    const heights = cards.map((item) => {
      item.style.position = 'absolute';
      item.style.width = `${colWidth}px`;
      item.style.left = '0';
      item.style.top = '0';
      item.style.visibility = 'hidden';
      return item.offsetHeight;
    });

    const colHeights = [0, 0];
    cards.forEach((item, index) => {
      const col = colHeights[0] <= colHeights[1] ? 0 : 1;
      item.style.visibility = '';
      item.style.left = `${col * (colWidth + gap)}px`;
      item.style.top = `${colHeights[col]}px`;
      colHeights[col] += heights[index] + gap;
    });

    const totalHeight = Math.max(colHeights[0], colHeights[1]);
    container.style.width = '100%';
    container.style.height = `${Math.max(0, totalHeight - gap)}px`;
    if (reveal) container.classList.remove('dashboard-masonry--pending');
  };

  const scheduleLayout = (options) => {
    if (frame) cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => layout(options));
  };

  mq.addEventListener('change', () => {
    if (mq.matches) {
      container.classList.add('dashboard-masonry--pending');
      scheduleLayout({ reveal: true });
    } else {
      clearLayout();
      container.classList.remove('dashboard-masonry--pending');
    }
  });

  window.addEventListener('resize', () => scheduleLayout({ reveal: false }));

  if (typeof ResizeObserver !== 'undefined') {
    const observer = new ResizeObserver(() => scheduleLayout({ reveal: false }));
    observer.observe(container);
    if (container.parentElement) observer.observe(container.parentElement);
    items().forEach((item) => observer.observe(item));
  }

  if (mq.matches) {
    container.classList.add('dashboard-masonry--pending');
    layout({ reveal: true });
  } else {
    container.classList.remove('dashboard-masonry--pending');
  }

  return () => scheduleLayout({ reveal: false });
}

document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('dashboard-root');
  const toggleBtn = document.getElementById('btn-toggle-valores');
  const MASCARA = '••••••';
  const relayoutMasonry = initDashboardMasonry();

  const aplicarOcultar = (ocultar) => {
    root?.querySelectorAll('.dash-valor').forEach((el) => {
      el.textContent = ocultar ? MASCARA : el.dataset.valor || MASCARA;
    });
    root?.classList.toggle('dashboard--ocultar-valores', ocultar);
    if (toggleBtn) {
      toggleBtn.setAttribute('aria-pressed', ocultar ? 'true' : 'false');
      toggleBtn.title = ocultar ? 'Exibir valores' : 'Ocultar valores';
    }
  };

  if (root) {
    aplicarOcultar(root.dataset.ocultar === '1');
  }

  toggleBtn?.addEventListener('click', async () => {
    const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    try {
      const res = await fetch(toggleBtn.dataset.url, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrf || '', 'Content-Type': 'application/json' },
      });
      if (!res.ok) return;
      const data = await res.json();
      root.dataset.ocultar = data.ocultar ? '1' : '0';
      aplicarOcultar(data.ocultar);
      relayoutMasonry();
    } catch {
      /* silencioso */
    }
  });

  window.resizeDashboardCharts = () => {
    if (typeof Chart !== 'undefined') {
      const el = document.getElementById('grafico-categorias');
      if (el) {
        const chart = Chart.getChart(el);
        if (chart) chart.resize();
      }
    }
    relayoutMasonry();
  };

  if (typeof Chart !== 'undefined') {
    const catCanvas = document.getElementById('grafico-categorias');
    const topData = parseJsonScript('top-despesas-data') || [];
    if (catCanvas && topData.length) {
      const cctx = catCanvas.getContext('2d');
      if (cctx) {
        const sliceColors = coresDistintasGrafico(topData);
        new Chart(cctx, {
          type: 'doughnut',
          data: {
            labels: topData.map((x) => x.nome),
            datasets: [
              {
                data: topData.map((x) => (Number.isFinite(Number(x.total)) ? Number(x.total) : 0)),
                backgroundColor: sliceColors,
                borderWidth: 2,
                borderColor: '#ffffff',
                hoverOffset: 8,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '68%',
            plugins: {
              legend: { display: false },
              tooltip: {
                callbacks: {
                  label(ctx) {
                    const pct = topData[ctx.dataIndex]?.pct;
                    const val = moedaTick(ctx.parsed);
                    return pct != null ? ` ${val} (${Math.round(pct)}%)` : ` ${val}`;
                  },
                },
              },
            },
          },
        });
        relayoutMasonry();
      }
    }
  }
});
