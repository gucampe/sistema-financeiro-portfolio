/**
 * UI de feed inteligente para preview de importação (OFX / planilha).
 * Combobox de categoria = mesmo padrão do modal adicionar transação (icon_combobox.js).
 */
(function () {
  const FEED_ITEM_CLASS = "import-feed-item";
  const COMBOBOX_TRIGGER_CLASS =
    "flex w-full max-w-full min-w-0 items-center gap-2 rounded-lg border border-gray-300 bg-white py-2 pl-3 pr-2 text-left text-sm text-fg shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500";
  const COMBOBOX_LIST_CLASS =
    "absolute left-0 right-0 z-[40] mt-1 hidden max-h-56 overflow-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg";

  const NIVEL = { ALTA: "alta", MEDIA: "media", BAIXA: "baixa" };

  let confirmResolver = null;

  function formatDataBR(iso) {
    if (!iso || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return "—";
    const [y, m, d] = iso.split("-");
    return `${d}/${m}/${y}`;
  }

  function formatValor(valor, tipo) {
    const n = Number.parseFloat(String(valor || "0").replace(",", "."));
    if (Number.isNaN(n)) return "—";
    const fmt = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
    const s = fmt.format(Math.abs(n));
    if (tipo === "despesa") return `− ${s}`;
    if (tipo === "receita") return `+ ${s}`;
    return s;
  }

  function isCategorizado(container) {
    return container?.dataset?.categorizado === "true";
  }

  function nivelConfianca(linha) {
    const nivel = linha?.categoria_sugerida_nivel_confianca;
    if (nivel === NIVEL.ALTA || nivel === NIVEL.MEDIA || nivel === NIVEL.BAIXA) return nivel;
    if (!linha?.categoria_sugerida_id) return null;
    if (linha?.categoria_sugerida_pre_preencher) return NIVEL.ALTA;
    return NIVEL.MEDIA;
  }

  function isSugestaoInteligente(fonte, fonteLabel) {
    if (fonte === "llm_gemini" || fonte === "ml") return true;
    const label = (fonteLabel || "").toLowerCase();
    return label === "ia" || label === "sugestão inteligente";
  }

  function badgesHtml(linha, nivel) {
    const parts = [];
    const badgeAprend = (linha?.categoria_sugerida_badge_aprendizado || "").trim();
    const fonteLabel = (linha?.categoria_sugerida_fonte_label || "").trim();
    const fonte = linha?.categoria_sugerida_fonte || "";
    const conf = Number(linha?.categoria_sugerida_confianca || 0);

    if (nivel === NIVEL.BAIXA) {
      parts.push(`<span class="import-feed-cat-badges__badge">Confiança baixa</span>`);
      return parts.join("");
    }

    if (badgeAprend) {
      parts.push(`<span class="import-feed-cat-badges__badge">${badgeAprend}</span>`);
    } else if (nivel === NIVEL.MEDIA) {
      parts.push(`<span class="import-feed-cat-badges__badge">Sugestão provável</span>`);
    } else if (isSugestaoInteligente(fonte, fonteLabel)) {
      parts.push(`<span class="import-feed-cat-badges__badge">Sugestão inteligente</span>`);
    } else if (fonteLabel && fonteLabel !== "Histórico") {
      parts.push(`<span class="import-feed-cat-badges__badge">${fonteLabel}</span>`);
    }

    if (nivel === NIVEL.ALTA && conf > 0) {
      parts.push(
        `<span class="import-feed-cat-badges__badge import-feed-cat-badges__badge--muted">${Math.round(conf * 100)}% de confiança</span>`
      );
    }

    return parts.length ? parts.join("") : "";
  }

  function hintSemPadrao() {
    return "Não encontramos um padrão confiável";
  }

  function aplicarEstadoVisualItem(itemEl) {
    if (!itemEl) return;
    itemEl.classList.remove("is-confianca-alta", "is-confianca-media", "is-confianca-baixa");
  }

  function marcarRevisado(itemEl) {
    if (!itemEl) return;
    itemEl.classList.add("is-revisado-flash");
    setTimeout(() => itemEl.classList.remove("is-revisado-flash"), 500);
  }

  function setFeedCategorizado(container, value) {
    if (!container) return;
    container.dataset.categorizado = value ? "true" : "false";
    if (!value) {
      getItems(container).forEach((item) => {
        item.dataset.confiancaNivel = "";
        const badgesSlot = item.querySelector("[data-cat-badges]");
        const hintSlot = item.querySelector("[data-cat-hint]");
        if (badgesSlot) {
          badgesSlot.innerHTML = "";
          badgesSlot.hidden = true;
        }
        if (hintSlot) {
          hintSlot.innerHTML = "";
          hintSlot.hidden = true;
        }
        aplicarEstadoVisualItem(item);
      });
    }
  }

  function criarComboboxCategoria(linha, listaCat, prefix) {
    const listId = `cb-list-${prefix}-cat-${linha.indice}`;

    const wrapper = document.createElement("div");
    wrapper.className = "import-feed-cat-combobox min-w-0";

    const root = document.createElement("div");
    root.className = "relative min-w-0";
    root.setAttribute("data-combobox-root", `${prefix}-categoria-${linha.indice}`);

    const sel = document.createElement("select");
    sel.className = `sr-only focus:outline-none ${prefix}-categoria`;
    sel.dataset.indice = String(linha.indice);
    sel.setAttribute("aria-label", "Categoria");

    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = "Selecione uma categoria";
    sel.appendChild(opt0);

    listaCat.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = String(c.id);
      opt.textContent = c.nome;
      if (c.icone != null) opt.dataset.icone = c.icone;
      if (c.cor != null) opt.dataset.cor = c.cor;
      sel.appendChild(opt);
    });

    if (listaCat.length === 1 && linha.categoria_sugerida_pre_preencher) {
      sel.value = String(listaCat[0].id);
    }

    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.setAttribute("data-combobox-trigger", "");
    trigger.className = COMBOBOX_TRIGGER_CLASS;
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    trigger.setAttribute("aria-controls", listId);
    trigger.innerHTML = `
      <span data-combobox-trigger-icon class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-gray-50"></span>
      <span data-combobox-trigger-label class="min-w-0 flex-1 truncate">Selecione uma categoria</span>
      <span data-combobox-chevron aria-hidden="true"></span>
    `;

    const list = document.createElement("div");
    list.id = listId;
    list.setAttribute("data-combobox-list", "");
    list.setAttribute("role", "listbox");
    list.className = COMBOBOX_LIST_CLASS;
    list.hidden = true;

    root.append(sel, trigger, list);

    const hintEl = document.createElement("p");
    hintEl.className = "import-feed-cat-hint";
    hintEl.dataset.catHint = "";
    hintEl.hidden = true;

    const badgesEl = document.createElement("div");
    badgesEl.className = "import-feed-cat-badges";
    badgesEl.dataset.catBadges = "";
    badgesEl.hidden = true;

    wrapper.append(root, hintEl, badgesEl);
    return { wrapper, sel, root, badgesEl, hintEl };
  }

  function isPortaledComboboxTarget(target) {
    return Boolean(
      target instanceof Element &&
        target.closest("[data-combobox-list].combobox-list--floating")
    );
  }

  function closeSiblingComboboxes(container, exceptRoot) {
    if (!container) return;
    container.querySelectorAll("[data-combobox-root]").forEach((root) => {
      if (root !== exceptRoot && root._feedCombobox?.close) {
        root._feedCombobox.close();
      }
    });
  }

  function initFeedCombobox(root, container, itemEl) {
    if (!root || !window.initIconCombobox) return null;
    const sel = root.querySelector("select");
    if (!sel) return null;
    const instance = window.initIconCombobox(sel, "category");
    root._feedCombobox = instance;
    const trigger = root.querySelector("[data-combobox-trigger]");
    trigger?.addEventListener("click", () => {
      closeSiblingComboboxes(container, root);
    });
    const list = root.querySelector("[data-combobox-list]");
    list?.addEventListener("click", () => {
      requestAnimationFrame(() => marcarRevisado(itemEl));
    });
    return instance;
  }

  function updateCategoryMeta(itemEl, linha, opts = {}) {
    const container = itemEl?.closest("[role='feed']");
    const sel = itemEl?.querySelector("select[class*='-categoria']");
    const badgesSlot = itemEl?.querySelector("[data-cat-badges]");
    const hintSlot = itemEl?.querySelector("[data-cat-hint]");
    const root = sel?.closest("[data-combobox-root]");
    if (!sel) return;

    const nivel = nivelConfianca(linha);
    const categorizado = isCategorizado(container);

    if (categorizado && nivel) {
      itemEl.dataset.confiancaNivel = nivel;
    }

    if (linha?.categoria_sugerida_id) {
      window.CategorizacaoImport?.aplicarSugestaoCategoriaSelect(sel, linha, {
        animate: opts.animate,
        skipCard: true,
        nivel,
      });
      root?._feedCombobox?.sync?.();
    }

    if (opts.animate && linha?.categoria_sugerida_id) {
      itemEl.classList.add("is-reveal-brief");
      setTimeout(() => itemEl.classList.remove("is-reveal-brief"), 900);
    }

    if (!badgesSlot || !hintSlot) return;

    if (!categorizado) {
      badgesSlot.innerHTML = "";
      badgesSlot.hidden = true;
      hintSlot.innerHTML = "";
      hintSlot.hidden = true;
      return;
    }

    if (nivel === NIVEL.BAIXA) {
      const temSug = Boolean(linha?.categoria_sugerida_id || sel?.dataset.sugestaoId);
      if (temSug) {
        hintSlot.innerHTML = "";
        hintSlot.hidden = true;
        const html = badgesHtml(linha, nivel);
        badgesSlot.innerHTML = html;
        badgesSlot.hidden = !html;
      } else {
        hintSlot.textContent = hintSemPadrao();
        hintSlot.hidden = false;
        badgesSlot.innerHTML = "";
        badgesSlot.hidden = true;
      }
      return;
    }

    if ((nivel === NIVEL.MEDIA || nivel === NIVEL.ALTA) && linha?.categoria_sugerida_id) {
      hintSlot.innerHTML = "";
      hintSlot.hidden = true;
      const html = badgesHtml(linha, nivel);
      if (html) {
        badgesSlot.innerHTML = html;
        badgesSlot.hidden = false;
      } else {
        badgesSlot.innerHTML = "";
        badgesSlot.hidden = true;
      }
      return;
    }

    hintSlot.innerHTML = "";
    hintSlot.hidden = true;
    badgesSlot.innerHTML = "";
    badgesSlot.hidden = true;
  }

  function syncDisplayFromInputs(itemEl, prefix) {
    const descInp = itemEl.querySelector(`.${prefix}-descricao`);
    const dataInp = itemEl.querySelector(`.${prefix}-data`);
    const valorInp = itemEl.querySelector(`.${prefix}-valor`);
    const descDisplay = itemEl.querySelector("[data-feed-desc]");
    const metaDisplay = itemEl.querySelector("[data-feed-meta]");

    if (descDisplay && descInp instanceof HTMLInputElement) {
      descDisplay.textContent = descInp.value || "—";
    }
    if (metaDisplay && dataInp instanceof HTMLInputElement) {
      const tipo = itemEl.dataset.tipo || "despesa";
      const dataFmt = formatDataBR(dataInp.value);
      let valorFmt = "—";
      let valorClass = "";
      if (valorInp) {
        const raw =
          window.MoedaInput?.parseToDecimalString?.(valorInp) ||
          valorInp.dataset.initialDecimal ||
          valorInp.value;
        valorFmt = formatValor(raw, tipo);
        valorClass =
          tipo === "despesa"
            ? "import-feed-item__meta-valor--despesa"
            : tipo === "receita"
              ? "import-feed-item__meta-valor--receita"
              : "";
      }
      metaDisplay.innerHTML = `<time>${dataFmt}</time><span aria-hidden="true">·</span><span class="${valorClass}">${valorFmt}</span>`;
    }
  }

  function montarFeed({ container, data, prefix }) {
    if (!container) return;
    container.innerHTML = "";
    container.dataset.categorizado = "false";

    const cats = data.categorias || {};
    const chaves = data.categorias_chave_por_tipo_transacao || {};

    data.linhas.forEach((linha) => {
      const dup = linha.duplicata_por_fitid || linha.duplicata_por_heuristica;
      const incluirDefault = !dup;
      const chaveCat = chaves[linha.tipo] || linha.tipo;
      const listaCat = cats[chaveCat] || [];
      const iso = linha.data && String(linha.data).slice(0, 10);
      const dataVal = /^\d{4}-\d{2}-\d{2}$/.test(iso) ? iso : "";

      const article = document.createElement("article");
      article.className = FEED_ITEM_CLASS;
      article.dataset.indice = String(linha.indice);
      article.dataset.tipo = linha.tipo;

      const avisoDup = linha.duplicata_por_heuristica
        ? `<span class="import-feed-item__tag import-feed-item__tag--warn">Possível duplicata</span>`
        : "";

      article.innerHTML = `
        <label class="import-feed-item__check" title="Incluir na importação">
          <input type="checkbox" class="${prefix}-incluir" data-indice="${linha.indice}" ${incluirDefault ? "checked" : ""} />
          <span class="import-feed-item__check-mark" aria-hidden="true">✓</span>
        </label>
        <div class="import-feed-item__body">
          <div class="import-feed-item__main">
            <div class="import-feed-item__head">
              <p class="import-feed-item__desc" data-feed-desc></p>
              <span class="import-feed-item__meta" data-feed-meta></span>
            </div>
            ${avisoDup ? `<div>${avisoDup}</div>` : ""}
            <button type="button" class="import-feed-item__edit-toggle feed-edit-toggle" aria-expanded="false">Editar</button>
            <div class="import-feed-item__edit-panel feed-edit-panel" hidden>
              <label class="field-label">Descrição</label>
              <input type="text" class="${prefix}-descricao" maxlength="255" autocomplete="off" data-indice="${linha.indice}" />
              <div class="import-feed-item__edit-grid">
                <div>
                  <label class="field-label">Data</label>
                  <input type="date" class="${prefix}-data" data-indice="${linha.indice}" />
                </div>
                <div>
                  <label class="field-label">Valor</label>
                  <input type="text" class="${prefix}-valor input input-moeda" data-moeda-input="1" inputmode="decimal" autocomplete="off" data-indice="${linha.indice}" />
                </div>
              </div>
            </div>
          </div>
          <div class="import-feed-item__cat-col" data-cat-col></div>
        </div>
      `;

      const descInp = article.querySelector(`.${prefix}-descricao`);
      const dataInp = article.querySelector(`.${prefix}-data`);
      const valorInp = article.querySelector(`.${prefix}-valor`);
      if (descInp) descInp.value = linha.descricao ?? "";
      if (dataInp) dataInp.value = dataVal;
      if (valorInp && linha.valor != null && linha.valor !== "") {
        valorInp.dataset.initialDecimal = String(linha.valor).trim();
        window.MoedaInput?.init(valorInp);
      }

      const catCol = article.querySelector("[data-cat-col]");
      const { wrapper, sel, root } = criarComboboxCategoria(linha, listaCat, prefix);
      catCol?.appendChild(wrapper);
      initFeedCombobox(root, container, article);

      container.appendChild(article);
      syncDisplayFromInputs(article, prefix);

      if (linha.categoria_sugerida_id) {
        updateCategoryMeta(article, linha);
      }
    });

    bindFeedInteractions(container, prefix);
  }

  function bindFeedInteractions(container, prefix) {
    if (!container.dataset.comboboxOutsideBound) {
      container.dataset.comboboxOutsideBound = "1";
      document.addEventListener("click", (e) => {
        if (container.contains(e.target)) return;
        if (isPortaledComboboxTarget(e.target)) return;
        closeSiblingComboboxes(container, null);
      });
    }

    if (!container.dataset.revisaoConfirmBound) {
      container.dataset.revisaoConfirmBound = "1";
      initConfirmModalHandlers();
    }

    container.querySelectorAll(`.${FEED_ITEM_CLASS}`).forEach((item) => {
      const editToggle = item.querySelector(".feed-edit-toggle");
      const editPanel = item.querySelector(".feed-edit-panel");
      editToggle?.addEventListener("click", () => {
        const open = editPanel?.hasAttribute("hidden");
        if (editPanel) {
          if (open) editPanel.removeAttribute("hidden");
          else editPanel.setAttribute("hidden", "");
        }
        editToggle.setAttribute("aria-expanded", open ? "true" : "false");
      });

      item.querySelectorAll(`.${prefix}-descricao, .${prefix}-data, .${prefix}-valor`).forEach((inp) => {
        inp.addEventListener("change", () => syncDisplayFromInputs(item, prefix));
        inp.addEventListener("blur", () => syncDisplayFromInputs(item, prefix));
      });

      const sel = item.querySelector(`select.${prefix}-categoria`);
      const root = sel?.closest("[data-combobox-root]");
      sel?.addEventListener("change", () => {
        marcarRevisado(item);
        root?._feedCombobox?.sync?.();
        if (!isCategorizado(container)) return;
        const linhaParcial = {
          categoria_sugerida_id: sel.value ? Number(sel.value) : null,
          categoria_sugerida_nome: sel.options[sel.selectedIndex]?.textContent || "",
          categoria_sugerida_confianca: Number(sel.dataset.sugestaoConfianca || 0),
          categoria_sugerida_fonte: sel.dataset.sugestaoFonte || "",
          categoria_sugerida_fonte_label: sel.dataset.sugestaoFonteLabel || "",
          categoria_sugerida_badge_aprendizado: sel.dataset.sugestaoBadge || "",
          categoria_sugerida_nivel_confianca: sel.dataset.sugestaoNivel || item.dataset.confiancaNivel,
          categoria_sugerida_pre_preencher: sel.dataset.sugestaoNivel === NIVEL.ALTA,
        };
        updateCategoryMeta(item, linhaParcial);
      });

      const incluir = item.querySelector(`.${prefix}-incluir`);
      const syncSelected = () => {
        item.classList.toggle("is-excluded", !incluir?.checked);
      };
      incluir?.addEventListener("change", syncSelected);
      syncSelected();
    });
  }

  function initConfirmModalHandlers() {
    const modal = document.getElementById("modal-import-revisar-categorias");
    const btnConfirmar = document.getElementById("btn-import-revisar-confirmar");
    const btnVoltar = document.getElementById("btn-import-revisar-voltar");
    if (!modal || modal.dataset.bound) return;
    modal.dataset.bound = "1";

    btnConfirmar?.addEventListener("click", () => {
      globalThis.GranaGoModal?.close("modal-import-revisar-categorias");
      confirmResolver?.(true);
      confirmResolver = null;
    });

    btnVoltar?.addEventListener("click", () => {
      globalThis.GranaGoModal?.close("modal-import-revisar-categorias");
      confirmResolver?.(false);
      confirmResolver = null;
    });

    globalThis.GranaGoModal?.bind?.(modal, {
      onClose: () => {
        if (confirmResolver) {
          confirmResolver(false);
          confirmResolver = null;
        }
      },
    });
  }

  function getItems(container) {
    return container ? [...container.querySelectorAll(`.${FEED_ITEM_CLASS}`)] : [];
  }

  function analisarResumoConfirmacao(container, prefix) {
    let provaveis = 0;
    let fracas = 0;
    let semPadrao = 0;
    let primeiroRevisar = null;

    getItems(container).forEach((item) => {
      const cb = item.querySelector(`.${prefix}-incluir`);
      if (!cb?.checked) return;

      const nivel = item.dataset.confiancaNivel;
      const sel = item.querySelector(`select.${prefix}-categoria`);
      const temSug = Boolean(sel?.dataset.sugestaoId);

      if (nivel === NIVEL.MEDIA) {
        provaveis += 1;
        if (!primeiroRevisar) primeiroRevisar = item;
      } else if (nivel === NIVEL.BAIXA && temSug) {
        fracas += 1;
        if (!primeiroRevisar) primeiroRevisar = item;
      } else if (nivel === NIVEL.BAIXA && !temSug) {
        semPadrao += 1;
        if (!primeiroRevisar) primeiroRevisar = item;
      }
    });

    const total = provaveis + fracas + semPadrao;
    return {
      provaveis,
      fracas,
      semPadrao,
      moderadas: provaveis,
      needsConfirm: total > 0,
      primeiroRevisar,
      primeiroPendente: primeiroRevisar,
    };
  }

  function solicitarConfirmacaoRevisao(summary) {
    initConfirmModalHandlers();
    const modal = document.getElementById("modal-import-revisar-categorias");
    const lista = document.getElementById("modal-import-revisar-lista");
    if (!modal || !lista) return Promise.resolve(true);

    lista.innerHTML = "";
    if (summary.provaveis > 0) {
      const li = document.createElement("li");
      li.className = "flex items-start gap-2";
      const textoProvaveis =
        summary.provaveis === 1
          ? "1 sugestão provável"
          : `${summary.provaveis} sugestões prováveis`;
      li.innerHTML = `<span class="text-gray-400" aria-hidden="true">•</span><span>${textoProvaveis}</span>`;
      lista.appendChild(li);
    }
    if (summary.fracas > 0) {
      const li = document.createElement("li");
      li.className = "flex items-start gap-2";
      li.innerHTML = `<span class="text-gray-400" aria-hidden="true">•</span><span>${summary.fracas} com confiança baixa</span>`;
      lista.appendChild(li);
    }
    if (summary.semPadrao > 0) {
      const li = document.createElement("li");
      li.className = "flex items-start gap-2";
      const textoSemPadrao =
        summary.semPadrao === 1
          ? "1 transação sem padrão claro"
          : `${summary.semPadrao} transações sem padrão claro`;
      li.innerHTML = `<span class="text-gray-400" aria-hidden="true">•</span><span>${textoSemPadrao}</span>`;
      lista.appendChild(li);
    }

    return new Promise((resolve) => {
      confirmResolver = (ok) => {
        if (!ok && summary.primeiroRevisar) {
          summary.primeiroRevisar.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        resolve(ok);
      };
      globalThis.GranaGoModal?.open("modal-import-revisar-categorias");
    });
  }

  function atualizarToolbar(toolbarEl, stats) {
    if (!toolbarEl) return;
    const {
      total = 0,
      categorizadas = 0,
      aprendidas = 0,
      categorizado = false,
    } = stats;

    const countEl = toolbarEl.querySelector("[data-toolbar-count]");
    const ctaEl = toolbarEl.querySelector("[data-toolbar-cta]");
    const resultEl = toolbarEl.querySelector("[data-toolbar-result]");

    if (countEl) {
      const n = total;
      countEl.textContent =
        n === 1 ? "1 transação importada" : `${n} transações importadas`;
    }

    if (categorizado) {
      if (ctaEl) {
        ctaEl.hidden = false;
        ctaEl.disabled = true;
        ctaEl.setAttribute("aria-disabled", "true");
      }
      if (resultEl) {
        let msg = `✨ ${categorizadas} organizada${categorizadas !== 1 ? "s" : ""}`;
        if (aprendidas > 0) {
          msg += ` · ${aprendidas} com base no seu histórico`;
        }
        resultEl.textContent = msg;
        resultEl.hidden = false;
      }
    } else {
      if (ctaEl) {
        ctaEl.hidden = false;
        ctaEl.disabled = false;
        ctaEl.removeAttribute("aria-disabled");
      }
      if (resultEl) resultEl.hidden = true;
    }

    toolbarEl.hidden = false;
    toolbarEl.classList.remove("hidden");
  }

  function calcularStatsLinhas(linhas) {
    let confSum = 0;
    let confN = 0;
    let aprendidas = 0;
    let categorizadas = 0;
    linhas.forEach((l) => {
      if (l.categoria_sugerida_id) {
        categorizadas += 1;
        const c = Number(l.categoria_sugerida_confianca || 0);
        if (c > 0) {
          confSum += c;
          confN += 1;
        }
        if (
          l.categoria_sugerida_badge_aprendizado ||
          l.categoria_sugerida_eh_aprendizado ||
          l.categoria_sugerida_fonte === "historico"
        ) {
          aprendidas += 1;
        }
      }
    });
    return {
      categorizadas,
      aprendidas,
      confiancaMedia: confN ? confSum / confN : 0,
    };
  }

  function coletarLinhasParaCategorizacao(container, stateLinhas, prefix) {
    const out = [];
    getItems(container).forEach((item) => {
      const indice = item.dataset.indice;
      const linha = stateLinhas.find((l) => String(l.indice) === indice);
      if (!linha) return;
      const inpDesc = item.querySelector(`.${prefix}-descricao`);
      const inpValor = item.querySelector(`.${prefix}-valor`);
      const descricao = (inpDesc instanceof HTMLInputElement ? inpDesc.value : linha.descricao ?? "").trim();
      let valor = linha.valor;
      if (inpValor && window.MoedaInput?.getDecimal) {
        const v = window.MoedaInput.getDecimal(inpValor);
        if (v != null && v !== "") valor = String(v);
      }
      out.push({ indice: linha.indice, descricao, tipo: linha.tipo, valor });
    });
    return out;
  }

  window.ImportFeedUI = {
    FEED_ITEM_CLASS,
    NIVEL,
    montarFeed,
    getItems,
    updateCategoryMeta,
    updateCategoryCard: (item, linha, opts) => updateCategoryMeta(item, linha, opts),
    setFeedCategorizado,
    marcarRevisado,
    analisarResumoConfirmacao,
    analisarRevisaoPendente: (container, prefix) => analisarResumoConfirmacao(container, prefix),
    solicitarConfirmacaoRevisao,
    atualizarToolbar,
    calcularStatsLinhas,
    coletarLinhasParaCategorizacao,
    syncDisplayFromInputs,
  };
})();
