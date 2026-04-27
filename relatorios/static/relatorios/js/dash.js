function queryStringFiltrosRelatorio() {
  const fromServer =
    typeof window.filtrosQueryString === 'string' ? window.filtrosQueryString.trim() : '';
  if (fromServer) return fromServer;
  const s = window.location.search || '';
  return s.startsWith('?') ? s.slice(1) : s;
}

document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('grafico-receitas-despesas');
  if (canvas && window.urlApiSerieTendencia) {
    const q = queryStringFiltrosRelatorio();
    const base = String(window.urlApiSerieTendencia).split('#')[0];
    const url = q ? `${base}?${q}` : base;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const msgErro = (texto) => {
      canvas.insertAdjacentHTML(
        'afterend',
        `<p class="text-sm text-red-600 mt-2" role="alert">${texto}</p>`,
      );
    };

    fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
      .then((res) => {
        if (res.type === 'opaqueredirect' || res.redirected) {
          window.location.assign(res.url || window.location.href);
          return null;
        }
        if (!res.ok) {
          return res.text().then((t) => {
            throw new Error(`HTTP ${res.status}: ${t.slice(0, 200)}`);
          });
        }
        const ct = res.headers.get('content-type') || '';
        if (!ct.includes('application/json')) {
          throw new Error('Resposta não é JSON (sessão expirou?)');
        }
        return res.json();
      })
      .then((data) => {
        if (data === null) return;
        if (data && data.erro && data.detail) {
          throw new Error(data.detail);
        }
        if (
          !data ||
          !Array.isArray(data.labels) ||
          !Array.isArray(data.receitas) ||
          !Array.isArray(data.despesas)
        ) {
          throw new Error('Resposta inválida da API de série');
        }
        if (typeof Chart === 'undefined') {
          throw new Error('Chart.js não carregou');
        }
        const despesas = data.despesas.map((v) => (Number.isFinite(Number(v)) ? Number(v) : 0));
        const receitas = data.receitas.map((v) => (Number.isFinite(Number(v)) ? Number(v) : 0));
        const ajustes = Array.isArray(data.ajustes)
          ? data.ajustes.map((v) => (Number.isFinite(Number(v)) ? Number(v) : 0))
          : [];

        const gradReceitas = ctx.createLinearGradient(0, 0, 0, 220);
        gradReceitas.addColorStop(0, 'rgba(16,185,129,0.4)');
        gradReceitas.addColorStop(1, 'rgba(16,185,129,0.05)');
        const gradDespesas = ctx.createLinearGradient(0, 0, 0, 220);
        gradDespesas.addColorStop(0, 'rgba(239,68,68,0.4)');
        gradDespesas.addColorStop(1, 'rgba(239,68,68,0.05)');

        const datasets = [
          {
            label: 'Receitas',
            data: receitas,
            borderColor: '#10b981',
            backgroundColor: gradReceitas,
            pointRadius: 3,
            tension: 0.35,
            fill: true,
          },
          {
            label: 'Despesas',
            data: despesas,
            borderColor: '#ef4444',
            backgroundColor: gradDespesas,
            pointRadius: 3,
            tension: 0.35,
            fill: true,
          },
        ];
        if (ajustes.some((v) => Number(v) !== 0)) {
          datasets.push({
            label: 'Ajustes',
            data: ajustes,
            borderColor: '#6b7280',
            backgroundColor: 'transparent',
            pointRadius: 2,
            tension: 0.35,
            fill: false,
          });
        }

        try {
          new Chart(ctx, {
            type: 'line',
            data: { labels: data.labels, datasets },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { display: true, position: 'bottom' },
                tooltip: {
                  backgroundColor: '#1f2937',
                  titleColor: '#fff',
                  bodyColor: '#d1d5db',
                  padding: 8,
                },
              },
              scales: {
                y: {
                  beginAtZero: true,
                  ticks: {
                    callback: (value) => 'R$ ' + Number(value).toLocaleString('pt-BR'),
                    color: '#4b5563',
                    font: { size: 10 },
                  },
                },
                x: {
                  ticks: { color: '#4b5563', font: { size: 10 }, maxRotation: 45 },
                },
              },
            },
          });
        } catch (e) {
          throw new Error(e && e.message ? e.message : 'Falha ao montar o gráfico');
        }
      })
      .catch((err) => {
        const det = err && err.message ? err.message : '';
        msgErro(
          det
            ? `Não foi possível carregar o gráfico de tendência. ${det}`
            : 'Não foi possível carregar o gráfico de tendência. Atualize a página ou verifique se está autenticado.',
        );
      });
  }

  const catCanvas = document.getElementById('grafico-categorias');
  const topEl = document.getElementById('top-despesas-data');
  if (catCanvas && topEl) {
    let topData = [];
    try {
      topData = JSON.parse(topEl.textContent);
    } catch {
      topData = [];
    }
    if (topData.length) {
      if (typeof Chart === 'undefined') return;
      const truncar = (s, max) => {
        const t = String(s ?? '').trim();
        if (t.length <= max) return t;
        return `${t.slice(0, Math.max(0, max - 1))}…`;
      };
      const valores = topData.map((x) => {
        const n = Number(x.total);
        return Number.isFinite(n) ? n : 0;
      });
      const maxVal = Math.max(...valores, 1);
      const labels = topData.map((x) => truncar(x.nome, 26));
      const cctx = catCanvas.getContext('2d');
      if (!cctx) return;
      new Chart(cctx, {
        type: 'bar',
        data: {
          labels,
          datasets: [
            {
              label: 'Despesas',
              data: valores,
              backgroundColor: topData.map((x) => x.cor || '#6B7280'),
              borderWidth: 0,
              // Eixo Y = categorias: altura da barra em px (barras horizontais).
              barThickness: 10,
            },
          ],
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          datasets: {
            bar: {
              categoryPercentage: 0.4,
              barPercentage: 0.65,
            },
          },
          layout: { padding: { left: 2, right: 10, top: 2, bottom: 2 } },
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                title(items) {
                  const i = items[0]?.dataIndex;
                  return i != null ? String(topData[i]?.nome ?? '') : '';
                },
                label(ctx) {
                  const v = ctx.parsed?.x;
                  return ` ${Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}`;
                },
              },
            },
          },
          scales: {
            x: {
              type: 'linear',
              beginAtZero: true,
              suggestedMax: maxVal * 1.06,
              ticks: {
                maxTicksLimit: 6,
                callback: (v) => 'R$ ' + Number(v).toLocaleString('pt-BR'),
                font: { size: 9 },
              },
              grid: { color: 'rgba(0,0,0,0.06)' },
            },
            y: {
              grid: { display: false },
              ticks: {
                font: { size: 9 },
                autoSkip: false,
                padding: 2,
              },
            },
          },
        },
      });
    } else {
      catCanvas.insertAdjacentHTML(
        'afterend',
        '<p class="text-sm text-gray-500 mt-2">Sem despesas por categoria neste período.</p>',
      );
    }
  }
});
