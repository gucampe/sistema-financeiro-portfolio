// categorias/static/categorias/js/alternar_categoria.js

document.addEventListener("DOMContentLoaded", () => {
  const btnDespesa = document.getElementById("btn-tab-despesa");
  const btnReceita = document.getElementById("btn-tab-receita");
  const listaDespesa = document.getElementById("lista-despesa");
  const listaReceita = document.getElementById("lista-receita");
  const listaDespesaArquivadas = document.getElementById("lista-despesa-arquivadas");
  const listaReceitaArquivadas = document.getElementById("lista-receita-arquivadas");
  const secaoArquivadas = document.getElementById("secao-arquivadas");
  const contadorArquivadas = document.getElementById("contador-arquivadas");

  if (!btnDespesa || !btnReceita || !listaDespesa || !listaReceita) return;

  const TAB_ACTIVE = ["tab-cat--despesa-active", "tab-cat--receita-active"];
  const TAB_INACTIVE = "tab-cat--inactive";

  function resetTabButtonClasses(btn) {
    btn.classList.remove(...TAB_ACTIVE, TAB_INACTIVE);
  }

  function setButtonActive(btn, type) {
    resetTabButtonClasses(btn);
    btn.classList.add(type === "despesa" ? "tab-cat--despesa-active" : "tab-cat--receita-active");
  }

  function setButtonInactive(btn) {
    resetTabButtonClasses(btn);
    btn.classList.add(TAB_INACTIVE);
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

    listaDespesa.classList.toggle("hidden", !isDespesa);
    listaReceita.classList.toggle("hidden", isDespesa);

    if (listaDespesaArquivadas) listaDespesaArquivadas.classList.toggle("hidden", !isDespesa);
    if (listaReceitaArquivadas) listaReceitaArquivadas.classList.toggle("hidden", isDespesa);

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

  const btnToggleArquivadas = document.getElementById("btn-toggle-arquivadas");
  const conteudoArquivadas = document.getElementById("conteudo-arquivadas");
  const iconAccordion = document.getElementById("icon-accordion-arquivadas");

  if (btnToggleArquivadas && conteudoArquivadas) {
    btnToggleArquivadas.addEventListener("click", () => {
      const isOpen = !conteudoArquivadas.classList.contains("hidden");
      conteudoArquivadas.classList.toggle("hidden", isOpen);
      btnToggleArquivadas.setAttribute("aria-expanded", isOpen ? "false" : "true");
      if (iconAccordion) iconAccordion.style.transform = isOpen ? "rotate(0deg)" : "rotate(-180deg)";
    });
  }

  window.atualizarContadorArquivadas = function (tipo, delta) {
    if (!secaoArquivadas) return;
    const key = tipo === "receita" ? "countReceita" : "countDespesa";
    const current = parseInt(secaoArquivadas.dataset[key] || "0", 10);
    secaoArquivadas.dataset[key] = String(Math.max(0, current + (delta || 0)));
    const tabAtivo = listaDespesa && !listaDespesa.classList.contains("hidden") ? "despesa" : "receita";
    updateContadorArquivadas(tabAtivo);
  };

  window.getTipoAtivo = function () {
    return listaDespesa && !listaDespesa.classList.contains("hidden") ? "despesa" : "receita";
  };

  window.setTipoAtivo = function () {};
});
