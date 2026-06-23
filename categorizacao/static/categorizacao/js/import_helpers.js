/**
 * Helpers compartilhados para sugestões de categorização na importação.
 */
(function () {
  function confiancaClasse(conf) {
    if (conf >= 0.85) return "border-emerald-400 bg-emerald-50/60";
    if (conf >= 0.70) return "border-amber-400 bg-amber-50/60";
    return "border-gray-300";
  }

  function aplicarSugestaoCategoriaSelect(sel, linha) {
    if (!sel || !linha) return;
    const sugId = linha.categoria_sugerida_id;
    if (!sugId) return;

    const conf = Number(linha.categoria_sugerida_confianca || 0);
    sel.dataset.sugestaoId = String(sugId);
    sel.dataset.sugestaoConfianca = String(conf);
    sel.dataset.sugestaoFonte = linha.categoria_sugerida_fonte || "";
    sel.dataset.sugestaoMerchant = linha.categoria_sugerida_merchant_key || "";
    sel.dataset.sugestaoExplicacao = linha.categoria_sugerida_explicacao || "";
    sel.title = linha.categoria_sugerida_explicacao || "";

    if (linha.categoria_sugerida_pre_preencher) {
      sel.value = String(sugId);
    }

    sel.classList.remove("border-gray-300", "border-emerald-400", "border-amber-400", "bg-emerald-50/60", "bg-amber-50/60");
    sel.classList.add(...confiancaClasse(conf).split(" "));

    const isLlm = (linha.categoria_sugerida_fonte || "") === "llm_gemini"
      && linha.categoria_sugerida_mostrar_badge_ia !== false;
    if (sel.nextElementSibling?.dataset?.sugestaoBadge) {
      sel.nextElementSibling.remove();
    }
    const badge = document.createElement("span");
    badge.dataset.sugestaoBadge = "1";
    if (isLlm) {
      badge.className = "ml-1 inline-flex items-center rounded-full bg-violet-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-violet-800";
      badge.textContent = "IA";
      badge.title = linha.categoria_sugerida_explicacao || "Sugestão por inteligência artificial (Gemini)";
    } else {
      badge.className = "ml-1 text-xs text-emerald-700";
      badge.textContent = "✨";
      badge.title = linha.categoria_sugerida_explicacao || "Sugestão automática";
    }
    sel.insertAdjacentElement("afterend", badge);
  }

  function metadadosSugestaoFromSelect(sel) {
    if (!sel || !sel.dataset.sugestaoId) return {};
    return {
      categoria_sugerida_id: Number(sel.dataset.sugestaoId),
      categoria_sugerida_confianca: Number(sel.dataset.sugestaoConfianca || 0),
      categoria_sugerida_fonte: sel.dataset.sugestaoFonte || "",
      categoria_sugerida_merchant_key: sel.dataset.sugestaoMerchant || "",
    };
  }

  window.CategorizacaoImport = {
    aplicarSugestaoCategoriaSelect,
    metadadosSugestaoFromSelect,
  };
})();
