document.addEventListener("DOMContentLoaded", () => {
  const root = document.getElementById("header-user-menu");
  if (!root) return;

  const trigger = document.getElementById("header-user-menu-trigger");
  const panel = document.getElementById("header-user-menu-panel");
  if (!trigger || !panel) return;

  function abrir() {
    panel.classList.remove("hidden");
    trigger.setAttribute("aria-expanded", "true");
  }

  function fechar() {
    panel.classList.add("hidden");
    trigger.setAttribute("aria-expanded", "false");
  }

  function alternar() {
    if (panel.classList.contains("hidden")) {
      abrir();
    } else {
      fechar();
    }
  }

  trigger.addEventListener("click", (e) => {
    e.stopPropagation();
    alternar();
  });

  document.addEventListener("click", (e) => {
    if (!root.contains(e.target)) {
      fechar();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      fechar();
      trigger.focus();
    }
  });

  panel.querySelectorAll("a.header-user-menu-item").forEach((link) => {
    link.addEventListener("click", () => fechar());
  });
});
