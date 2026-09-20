/**
 * Experiência premium de categorização IA na importação (loading + reveal).
 */
(function () {
  const MESSAGES = [
    "Analisando padrões das suas transações…",
    "Buscando aprendizados anteriores…",
    "Aplicando regras personalizadas…",
    "Identificando recorrências…",
    "Classificando transações…",
  ];
  const MICRO_HINTS = [
    "Mapeando descrições similares…",
    "Conferindo histórico pessoal…",
    "Priorizando o que você já corrigiu…",
  ];
  const MIN_DURATION_MS = 1200;
  const MSG_INTERVAL_MS = 420;
  const REVEAL_DELAY_MS = 85;

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function startMessageCycle(msgEl, signal) {
    if (!msgEl) return () => {};
    let idx = 0;
    msgEl.textContent = MESSAGES[0];
    const timer = setInterval(() => {
      if (signal?.aborted) return;
      idx = (idx + 1) % MESSAGES.length;
      msgEl.textContent = MESSAGES[idx];
    }, MSG_INTERVAL_MS);
    return () => clearInterval(timer);
  }

  function startMicroHints(microEl, signal) {
    if (!microEl) return () => {};
    let idx = 0;
    microEl.innerHTML = "";
    const addLine = (text, highlight) => {
      const line = document.createElement("div");
      line.className = `flex items-center gap-2 text-xs transition-all duration-500 ${
        highlight ? "text-emerald-700 font-medium" : "text-gray-500"
      }`;
      line.innerHTML = `<span class="text-emerald-600">✦</span><span>${text}</span>`;
      microEl.appendChild(line);
      while (microEl.children.length > 4) {
        microEl.removeChild(microEl.firstChild);
      }
    };
    addLine(MICRO_HINTS[0]);
    const timer = setInterval(() => {
      if (signal?.aborted) return;
      idx = (idx + 1) % MICRO_HINTS.length;
      addLine(MICRO_HINTS[idx]);
    }, 550);
    return { stop: () => clearInterval(timer), addLine };
  }

  function renderMicroResultados(microEl, resumo) {
    if (!microEl || !resumo) return;
    microEl.innerHTML = "";
    const add = (text) => {
      const line = document.createElement("div");
      line.className =
        "flex items-center gap-2 text-xs text-emerald-700 font-medium animate-[fadeIn_0.4s_ease-out]";
      line.innerHTML = `<span class="text-emerald-500">✓</span><span>${text}</span>`;
      microEl.appendChild(line);
    };
    if (resumo.categorizadas != null) {
      add(`${resumo.categorizadas} transações organizadas`);
    }
    const porFonte = resumo.por_fonte || {};
    const hist = porFonte.historico || 0;
    if (hist > 0) add(`${hist} pelo seu histórico pessoal`);
    const regras = (porFonte.regra_usuario || 0) + (porFonte.regra_global || 0);
    if (regras > 0) add(`${regras} pelas suas regras`);
    if (resumo.sem_sugestao > 0) {
      const line = document.createElement("div");
      line.className = "text-xs text-gray-500 mt-1";
      line.textContent = `${resumo.sem_sugestao} aguardam sua escolha manual`;
      microEl.appendChild(line);
    }
  }

  function showOverlay(overlayEl, msgEl) {
    if (!overlayEl) return;
    overlayEl.classList.remove("hidden");
    overlayEl.setAttribute("aria-hidden", "false");
    if (msgEl) msgEl.textContent = MESSAGES[0];
  }

  function hideOverlay(overlayEl) {
    if (!overlayEl) return;
    overlayEl.classList.add("hidden");
    overlayEl.setAttribute("aria-hidden", "true");
  }

  async function fetchBatch({ url, csrfToken, linhas, contexto, signal }) {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({ linhas, contexto }),
      signal,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.status !== "ok") {
      throw new Error(data.message || `Erro ao categorizar (${res.status}).`);
    }
    return data;
  }

  async function categorizarBatch({
    url,
    cancelUrl,
    csrfToken,
    linhas,
    contexto,
    overlayEl,
    msgEl,
    microEl,
    signal,
  }) {
    const t0 = Date.now();
    showOverlay(overlayEl, msgEl);
    const stopMsgs = startMessageCycle(msgEl, signal);
    const micro = startMicroHints(microEl, signal);

    try {
      const fetchPromise = fetchBatch({ url, csrfToken, linhas, contexto, signal });
      const [data] = await Promise.all([fetchPromise, sleep(MIN_DURATION_MS * 0.6)]);

      if (data.resumo && microEl) {
        renderMicroResultados(microEl, data.resumo);
      }

      const elapsed = Date.now() - t0;
      const remaining = MIN_DURATION_MS - elapsed;
      if (remaining > 0) await sleep(remaining);

      return data;
    } catch (err) {
      if (signal?.aborted && cancelUrl) {
        fetch(cancelUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
            "X-Requested-With": "XMLHttpRequest",
          },
          body: JSON.stringify({ contexto, payload: { motivo: "abort" } }),
        }).catch(() => {});
      }
      throw err;
    } finally {
      stopMsgs();
      micro?.stop?.();
      await sleep(400);
      hideOverlay(overlayEl);
    }
  }

  async function revelarSugestoes({ container, linhasAtualizadas, selectClass, onLinhaRevelada }) {
    if (!container || !linhasAtualizadas?.length) return;
    window.ImportFeedUI?.setFeedCategorizado(container, true);
    const porIndice = new Map(linhasAtualizadas.map((l) => [String(l.indice), l]));
    const items = window.ImportFeedUI?.getItems(container) || [];

    for (const item of items) {
      const linha = porIndice.get(item.dataset.indice);
      if (!linha) continue;

      await sleep(REVEAL_DELAY_MS);

      const sel = item.querySelector(selectClass || "select");
      if (sel && linha?.categoria_sugerida_id) {
        window.CategorizacaoImport?.aplicarSugestaoCategoriaSelect(sel, linha, {
          animate: true,
          skipCard: true,
          nivel: linha.categoria_sugerida_nivel_confianca,
        });
      }
      window.ImportFeedUI?.updateCategoryMeta(item, linha, {
        animate: Boolean(linha?.categoria_sugerida_id),
      });
      onLinhaRevelada?.(item, linha);
    }
  }

  window.CategorizacaoImportWow = {
    MESSAGES,
    MIN_DURATION_MS,
    categorizarBatch,
    revelarSugestoes,
    showOverlay,
    hideOverlay,
    renderMicroResultados,
  };
})();
