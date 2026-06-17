/**
 * Carrega Chart.js sob demanda (CDN) uma única vez por página.
 */
(function (global) {
  "use strict";

  let loading = null;

  function loadChartJs() {
    if (typeof global.Chart !== "undefined") {
      return Promise.resolve(global.Chart);
    }
    if (loading) return loading;
    loading = new Promise(function (resolve, reject) {
      const script = document.createElement("script");
      script.src =
        "https://cdn.jsdelivr.net/npm/chart.js@4.4.6/dist/chart.umd.min.js";
      script.defer = true;
      script.onload = function () {
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
