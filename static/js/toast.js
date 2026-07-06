/**
 * Toasts GranaGo — portal no body para escapar stacking contexts e ficar acima de modais.
 *
 * Markup: .app-toast (opcional id próprio por página)
 * API:    GranaGoToast.portalize() | GranaGoToast.ensureRoot()
 */
(function (global) {
  const ROOT_ID = "app-toast-root";

  function ensureRoot() {
    let root = document.getElementById(ROOT_ID);
    if (!root) {
      root = document.createElement("div");
      root.id = ROOT_ID;
      root.className = "app-toast-root";
      root.setAttribute("aria-live", "polite");
      root.setAttribute("aria-atomic", "true");
      document.body.appendChild(root);
    }
    return root;
  }

  /** Move toasts para o portal global (fora de #mainContent e modais). */
  function portalize() {
    const root = ensureRoot();
    document.querySelectorAll(".app-toast").forEach((toast) => {
      if (toast.parentElement === root) return;
      toast.classList.remove(
        "fixed",
        "bottom-4",
        "right-4",
        "pointer-events-none"
      );
      root.appendChild(toast);
    });
  }

  function init() {
    portalize();
  }

  global.GranaGoToast = {
    ensureRoot,
    portalize,
    init,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  const observer = new MutationObserver(() => portalize());
  if (document.body) {
    observer.observe(document.body, { childList: true, subtree: true });
  } else {
    document.addEventListener("DOMContentLoaded", () => {
      observer.observe(document.body, { childList: true, subtree: true });
    });
  }
})(window);
