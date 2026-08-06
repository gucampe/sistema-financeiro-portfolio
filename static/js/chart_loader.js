/**
 * Carrega Chart.js sob demanda (vendor local) uma única vez por página.
 * Passe a URL hasheada via data-chart-src no <script> do loader (produção).
 */
(function (global) {
  "use strict";

  const loaderEl = document.currentScript;
  const defaultSrc =
    (loaderEl && loaderEl.getAttribute("data-chart-src")) ||
    "/static/vendor/chart.js/chart.umd.min.js";

  let loading = null;

  function loadChartJs() {
    if (typeof global.Chart !== "undefined") {
      return Promise.resolve(global.Chart);
    }
    if (loading) return loading;
    loading = new Promise(function (resolve, reject) {
      const script = document.createElement("script");
      script.src = global.__GRANAGO_CHART_SRC || defaultSrc;
      script.onload = function () {
        if (typeof global.Chart === "undefined") {
          loading = null;
          reject(new Error("Chart.js carregou sem exportar Chart"));
          return;
        }
        resolve(global.Chart);
      };
      script.onerror = function () {
        loading = null;
        reject(new Error("Falha ao carregar Chart.js"));
      };
      document.head.appendChild(script);
    });
    return loading;
  }

  global.GranaGoChartLoader = { load: loadChartJs };
})(window);
