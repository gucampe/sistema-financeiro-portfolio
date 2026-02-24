// categorias/static/categorias/js/alternar_categoria.js

document.addEventListener("DOMContentLoaded", () => {
  const btnDespesa = document.getElementById("btn-tab-despesa");
  const btnReceita = document.getElementById("btn-tab-receita");
  const tbodyDespesa = document.getElementById("tbody-despesa");
  const tbodyReceita = document.getElementById("tbody-receita");
  const tbodyDespesaArquivadas = document.getElementById("tbody-despesa-arquivadas");
  const tbodyReceitaArquivadas = document.getElementById("tbody-receita-arquivadas");
  const secaoArquivadas = document.getElementById("secao-arquivadas");
  const contadorArquivadas = document.getElementById("contador-arquivadas");

  if (!btnDespesa || !btnReceita || !tbodyDespesa || !tbodyReceita) return;

  const COLORS = {
    receita: { bg: "#2ECC71", text: "#FFFFFF", hover: "#27AE60" },
    despesa: { bg: "#E74C3C", text: "#FFFFFF", hover: "#C0392B" },
    inactive: { bg: "#FFFFFF", text: "#34495E", hoverBg: "rgba(189,195,199,.25)" }
  };

  function setButtonActive(btn, type) {
    btn.style.background = COLORS[type].bg;
    btn.style.color = COLORS[type].text;
    btn.onmouseenter = () => (btn.style.background = COLORS[type].hover);
    btn.onmouseleave = () => (btn.style.background = COLORS[type].bg);
  }

  function setButtonInactive(btn) {
    btn.style.background = COLORS.inactive.bg;
    btn.style.color = COLORS.inactive.text;
    btn.onmouseenter = () => (btn.style.background = COLORS.inactive.hoverBg);
    btn.onmouseleave = () => (btn.style.background = COLORS.inactive.bg);
  }

  function updateContadorArquivadas(tab) {
    if (secaoArquivadas && contadorArquivadas) {
      const count = tab === "despesa"
        ? parseInt(secaoArquivadas.dataset.countDespesa || "0", 10)
        : parseInt(secaoArquivadas.dataset.countReceita || "0", 10);
      contadorArquivadas.textContent = count;
    }
  }

  function setActive(tab) {
    const isDespesa = tab === "despesa";

    tbodyDespesa.classList.toggle("hidden", !isDespesa);
    tbodyReceita.classList.toggle("hidden", isDespesa);

    if (tbodyDespesaArquivadas) tbodyDespesaArquivadas.classList.toggle("hidden", !isDespesa);
    if (tbodyReceitaArquivadas) tbodyReceitaArquivadas.classList.toggle("hidden", isDespesa);

    if (isDespesa) {
      setButtonActive(btnDespesa, "despesa");
      setButtonInactive(btnReceita);
    } else {
      setButtonActive(btnReceita, "receita");
      setButtonInactive(btnDespesa);
    }

    updateContadorArquivadas(tab);

    if (typeof window.setTipoAtivo === "function") window.setTipoAtivo(tab);
  }

  btnDespesa.addEventListener("click", (e) => {
    e.preventDefault();
    setActive("despesa");
  });

  btnReceita.addEventListener("click", (e) => {
    e.preventDefault();
    setActive("receita");
  });

  setActive("despesa");
  updateContadorArquivadas("despesa");

  // Accordion Arquivadas
  const btnToggleArquivadas = document.getElementById("btn-toggle-arquivadas");
  const conteudoArquivadas = document.getElementById("conteudo-arquivadas");
  const iconAccordion = document.getElementById("icon-accordion-arquivadas");

  if (btnToggleArquivadas && conteudoArquivadas) {
    btnToggleArquivadas.addEventListener("click", () => {
      const isOpen = !conteudoArquivadas.classList.contains("hidden");
      conteudoArquivadas.classList.toggle("hidden", isOpen);
      if (iconAccordion) iconAccordion.style.transform = isOpen ? "rotate(0deg)" : "rotate(-180deg)";
    });
  }

  window.atualizarContadorArquivadas = function (tipo, delta) {
    if (!secaoArquivadas) return;
    const key = tipo === "receita" ? "countReceita" : "countDespesa";
    const current = parseInt(secaoArquivadas.dataset[key] || "0", 10);
    secaoArquivadas.dataset[key] = String(Math.max(0, current + (delta || 0)));
    const tabAtivo = tbodyDespesa && !tbodyDespesa.classList.contains("hidden") ? "despesa" : "receita";
    updateContadorArquivadas(tabAtivo);
  };

  window.getTipoAtivo = function () {
    return tbodyDespesa && !tbodyDespesa.classList.contains("hidden") ? "despesa" : "receita";
  };

  window.setTipoAtivo = function () {};
});
