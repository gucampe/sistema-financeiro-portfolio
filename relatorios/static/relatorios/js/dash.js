
document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.getElementById('grafico-receitas-despesas');
  const ctx = canvas.getContext('2d');

  fetch(window.urlGraficoReceitasDespesas)
    .then(res => res.json())
    .then(data => {
      const gradReceitas = ctx.createLinearGradient(0, 0, 0, 160);
      gradReceitas.addColorStop(0, 'rgba(16,185,129,0.4)');
      gradReceitas.addColorStop(1, 'rgba(16,185,129,0.05)');
      const gradDespesas = ctx.createLinearGradient(0, 0, 0, 160);
      gradDespesas.addColorStop(0, 'rgba(239,68,68,0.4)');
      gradDespesas.addColorStop(1, 'rgba(239,68,68,0.05)');

      new Chart(ctx, {
        type: 'line',
        data: {
          labels: data.labels,
          datasets: [
            {
              label: 'Receitas',
              data: data.receitas,
              borderColor: '#10b981',
              backgroundColor: gradReceitas,
              pointRadius: 3,
              tension: 0.4,
              fill: true
            },
            {
              label: 'Despesas',
              data: data.despesas,
              borderColor: '#ef4444',
              backgroundColor: gradDespesas,
              pointRadius: 3,
              tension: 0.4,
              fill: true
            }
          ]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: '#1f2937',
              titleColor: '#fff',
              bodyColor: '#d1d5db',
              padding: 8
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: {
                callback: value => 'R$ ' + value.toLocaleString('pt-BR'),
                color: '#4b5563',
                font: { size: 10 }
              }
            },
            x: {
              ticks: {
                color: '#4b5563',
                font: { size: 10 }
              }
            }
          }
        }
      });
    });

  const ctxDonut = document.getElementById('grafico-donut').getContext('2d');
  new Chart(ctxDonut, {
    type: 'doughnut',
    data: {
      datasets: [{
        data: [74, 26],
        backgroundColor: ['#f97316', '#e5e7eb']
      }]
    },
    options: {
      responsive: false,
      cutout: '70%',
      plugins: { legend: { display: false } }
    }
  });
});
