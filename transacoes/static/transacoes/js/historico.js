document.addEventListener("DOMContentLoaded", () => {
  const dropdownMeses = document.getElementById("dropdown-meses");
  const dropdownPersonalizado = document.getElementById("dropdown-personalizado");
  const MQ_MOBILE = "(max-width: 767px)";

  function isMobileHistorico() {
    return window.matchMedia(MQ_MOBILE).matches;
  }

  function ativarToqueLancamento(e) {
    if (!isMobileHistorico()) return;
    if (e.target.closest("a, button, summary, input, select, label")) return;

    const faturaRow = e.target.closest(".historico-lancamento-fatura[data-fatura-url]");
    if (faturaRow) {
      window.location.href = faturaRow.dataset.faturaUrl;
      return;
    }

    const row = e.target.closest(".historico-lancamento[data-transacao-id]");
    if (!row) return;
    const id = row.dataset.transacaoId;
    if (!id || typeof window.abrirModalEditarTransacao !== "function") return;
    e.preventDefault();
    window.abrirModalEditarTransacao(id);
  }

  document.addEventListener("click", ativarToqueLancamento);

  document.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    if (!isMobileHistorico()) return;
    const faturaRow = e.target.closest(".historico-lancamento-fatura[data-fatura-url]");
    if (faturaRow) {
      e.preventDefault();
      window.location.href = faturaRow.dataset.faturaUrl;
      return;
    }
    const row = e.target.closest(".historico-lancamento[data-transacao-id]");
    if (!row) return;
    e.preventDefault();
    const id = row.dataset.transacaoId;
    if (id && typeof window.abrirModalEditarTransacao === "function") {
      window.abrirModalEditarTransacao(id);
    }
  });

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
