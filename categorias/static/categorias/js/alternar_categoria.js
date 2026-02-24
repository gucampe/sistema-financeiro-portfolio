// categorias/static/categorias/js/alternar_categoria.js

document.addEventListener("DOMContentLoaded", () => {
  const btnDespesa = document.getElementById("btn-tab-despesa");
  const btnReceita = document.getElementById("btn-tab-receita");
  const tbodyDespesa = document.getElementById("tbody-despesa");
  const tbodyReceita = document.getElementById("tbody-receita");

  // Debug simples (abre o console e veja)
  console.log("[toggle] init", { btnDespesa, btnReceita, tbodyDespesa, tbodyReceita });

  if (!btnDespesa || !btnReceita || !tbodyDespesa || !tbodyReceita) return;

  const COLORS = {
    receita: { bg: "#2ECC71", text: "#FFFFFF", hover: "#27AE60" },
    despesa: { bg: "#E74C3C", text: "#FFFFFF", hover: "#C0392B" },
    inactive: { bg: "#FFFFFF", text: "#34495E", hoverBg: "rgba(189,195,199,.25)" }
  };

  function setButtonActive(btn, type) {
    btn.style.background = COLORS[type].bg;
    btn.style.color = COLORS[type].text;

    // hover
    btn.onmouseenter = () => (btn.style.background = COLORS[type].hover);
    btn.onmouseleave = () => (btn.style.background = COLORS[type].bg);
  }

  function setButtonInactive(btn) {
    btn.style.background = COLORS.inactive.bg;
    btn.style.color = COLORS.inactive.text;

    // hover
    btn.onmouseenter = () => (btn.style.background = COLORS.inactive.hoverBg);
    btn.onmouseleave = () => (btn.style.background = COLORS.inactive.bg);
  }

  function setActive(tab) {
    const isDespesa = tab === "despesa";

    // mostra/oculta
    tbodyDespesa.classList.toggle("hidden", !isDespesa);
    tbodyReceita.classList.toggle("hidden", isDespesa);

    // estilos
    if (isDespesa) {
      setButtonActive(btnDespesa, "despesa");
      setButtonInactive(btnReceita);
    } else {
      setButtonActive(btnReceita, "receita");
      setButtonInactive(btnDespesa);
    }

    console.log("[toggle] active:", tab);
  }

  btnDespesa.addEventListener("click", (e) => {
    e.preventDefault();
    setActive("despesa");
  });

  btnReceita.addEventListener("click", (e) => {
    e.preventDefault();
    setActive("receita");
  });

  // estado inicial
  setActive("despesa");
});