/**
 * Helpers compartilhados para sugestões de categorização na importação.
 */
(function () {
  function aplicarSugestaoCategoriaSelect(sel, linha, opts = {}) {
    if (!sel || !linha) return;
    const sugId = linha.categoria_sugerida_id;
    if (!sugId) return;

    const conf = Number(linha.categoria_sugerida_confianca || 0);
    const nivel =
      opts.nivel ||
      linha.categoria_sugerida_nivel_confianca ||
      (linha.categoria_sugerida_pre_preencher ? "alta" : "media");

    sel.dataset.sugestaoId = String(sugId);
    sel.dataset.sugestaoConfianca = String(conf);
    sel.dataset.sugestaoFonte = linha.categoria_sugerida_fonte || "";
    sel.dataset.sugestaoMerchant = linha.categoria_sugerida_merchant_key || "";
    sel.dataset.sugestaoExplicacao = linha.categoria_sugerida_explicacao || "";
    sel.dataset.sugestaoNivel = nivel;
    sel.dataset.sugestaoFonteLabel = linha.categoria_sugerida_fonte_label || "";
    sel.dataset.sugestaoBadge = linha.categoria_sugerida_badge_aprendizado || "";
    sel.title = linha.categoria_sugerida_explicacao || "";

    if (sugId) {
      sel.value = String(sugId);
    }

    const root = sel.closest("[data-combobox-root]");
    root?._feedCombobox?.sync?.();

    if (!opts.skipCard) {
      const item = sel.closest(".import-feed-item");
      if (item) {
        window.ImportFeedUI?.updateCategoryMeta(item, linha, opts);
      }
    }
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
