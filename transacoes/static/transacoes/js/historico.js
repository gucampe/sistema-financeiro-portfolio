document.addEventListener("DOMContentLoaded", () => {
  const dropdownMeses = document.getElementById("dropdown-meses");
  const dropdownPersonalizado = document.getElementById("dropdown-personalizado");

  document.addEventListener("click", (e) => {
    if (dropdownMeses && !dropdownMeses.contains(e.target)) {
      dropdownMeses.removeAttribute("open");
    }
    if (dropdownPersonalizado && !dropdownPersonalizado.contains(e.target)) {
      dropdownPersonalizado.removeAttribute("open");
    }
  });

  const listRoot = document.querySelector("[data-bank-icon-fallback]");
  const fallbackUrl = listRoot?.dataset.bankIconFallback;
  if (fallbackUrl) {
    document.addEventListener(
      "error",
      (e) => {
        const el = e.target;
        if (el.tagName !== "IMG" || !el.classList.contains("conta-icone-dinamico")) {
          return;
        }
        el.src = fallbackUrl;
      },
      true
    );
  }
});
