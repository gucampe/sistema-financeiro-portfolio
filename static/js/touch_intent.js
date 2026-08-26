/**
 * Distingue toque (tap) de deslize (scroll) no mobile.
 * Usado para não abrir menus/modais no fim de um scroll.
 */
(function (global) {
  "use strict";

  var SLOP_PX = 10;
  var SUPPRESS_MS = 800;
  var startX = 0;
  var startY = 0;
  var moved = false;
  var suppressUntil = 0;

  function ponto(e) {
    if (e.changedTouches && e.changedTouches[0]) return e.changedTouches[0];
    if (e.touches && e.touches[0]) return e.touches[0];
    return e;
  }

  document.addEventListener(
    "touchstart",
    function (e) {
      var p = ponto(e);
      startX = p.clientX;
      startY = p.clientY;
      moved = false;
    },
    { capture: true, passive: true }
  );

  document.addEventListener(
    "touchmove",
    function (e) {
      var p = ponto(e);
      if (
        Math.abs(p.clientX - startX) > SLOP_PX ||
        Math.abs(p.clientY - startY) > SLOP_PX
      ) {
        moved = true;
      }
    },
    { capture: true, passive: true }
  );

  function encerrar() {
    if (moved) suppressUntil = Date.now() + SUPPRESS_MS;
    moved = false;
  }

  document.addEventListener("touchend", encerrar, { capture: true, passive: true });
  document.addEventListener("touchcancel", encerrar, { capture: true, passive: true });

  global.GranaGoTouch = {
    wasScroll: function () {
      return Date.now() < suppressUntil;
    },
  };
})(window);
