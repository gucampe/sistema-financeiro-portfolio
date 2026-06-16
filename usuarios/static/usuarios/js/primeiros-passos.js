/**
 * Central de Primeiros Passos — FAB no dashboard + interações na página dedicada.
 * Preferências em localStorage são escopadas por usuário (evita vazamento entre contas no mesmo navegador).
 */
(() => {
  const LS_SKIP_CARTAO_BASE = "granago_pp_skip_cartao";
  const LS_DISMISSED_BASE = "granago_pp_dismissed";
  const REDUCED_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const getUserId = () => {
    const fab = document.getElementById("pp-fab");
    const page = document.getElementById("pp-page");
    const fromEl = fab?.dataset.ppUserId || page?.dataset.ppUserId;
    if (fromEl) return String(fromEl);
    if (typeof window.__ppUserId !== "undefined" && window.__ppUserId !== "") {
      return String(window.__ppUserId);
    }
    return "";
  };

  const storageKey = (base) => {
    const uid = getUserId();
    return uid ? `${base}_${uid}` : base;
  };

  const loadServerData = () => {
    const dataEl = document.getElementById("primeiros-passos-data");
    if (!dataEl) return {};
    try {
      return JSON.parse(dataEl.textContent);
    } catch {
      return {};
    }
  };

  /** Chaves globais legadas (pré-escopo por usuário) — removidas para não afetar outras contas. */
  const purgeLegacyStorage = () => {
    try {
      localStorage.removeItem(LS_DISMISSED_BASE);
      localStorage.removeItem(LS_SKIP_CARTAO_BASE);
    } catch {
      /* ignore */
    }
  };

  const isCartaoSkipped = () => {
    try {
      return localStorage.getItem(storageKey(LS_SKIP_CARTAO_BASE)) === "1";
    } catch {
      return false;
    }
  };

  const etapaConcluida = (id, serverConcluida) => {
    if (id === "cartao" && isCartaoSkipped()) return true;
    return serverConcluida;
  };

  const calcProgress = (serverData) => {
    const etapas = serverData.etapas || [];
    let concluidas = 0;
    etapas.forEach((e) => {
      if (etapaConcluida(e.id, e.concluida)) concluidas += 1;
    });
    const total = serverData.total || etapas.length || 3;
    const percentual = total ? Math.round((concluidas / total) * 100) : 100;
    return {
      concluidas,
      total,
      percentual,
      totalCompleto: concluidas >= total,
    };
  };

  const isDismissed = () => {
    try {
      return localStorage.getItem(storageKey(LS_DISMISSED_BASE)) === "1";
    } catch {
      return false;
    }
  };

  const markDismissButtons = () => {
    document.querySelectorAll(".pp-btn-dismiss").forEach((btn) => {
      btn.classList.add("is-dismissed");
      btn.setAttribute("aria-disabled", "true");
      if (btn.tagName === "BUTTON") btn.disabled = true;
      btn.textContent = "Atalho ocultado";
    });
    const feedback = document.getElementById("pp-dismiss-feedback");
    feedback?.classList.remove("hidden");

    let toast = document.getElementById("pp-dismiss-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "pp-dismiss-toast";
      toast.className = "pp-dismiss-toast";
      toast.setAttribute("role", "status");
      toast.setAttribute("aria-live", "polite");
      toast.innerHTML =
        '<i class="fa-solid fa-circle-check" aria-hidden="true"></i><span>Atalho ocultado no dashboard</span>';
      document.body.appendChild(toast);
    }
    toast.classList.add("pp-dismiss-toast--visible");
    window.setTimeout(() => toast.classList.remove("pp-dismiss-toast--visible"), 3200);
  };

  const setDismissed = ({ showFeedback = false } = {}) => {
    try {
      localStorage.setItem(storageKey(LS_DISMISSED_BASE), "1");
    } catch {
      /* ignore */
    }
    document.documentElement.classList.add("pp-dismissed");
    const fab = document.getElementById("pp-fab");
    fab?.classList.add("pp-fab--hidden");
    if (showFeedback) markDismissButtons();
  };

  const updateFab = (fab, serverData) => {
    const { concluidas, total, totalCompleto } = calcProgress(serverData);
    const badge = fab.querySelector(".pp-fab__badge");
    if (badge) {
      badge.textContent = `${concluidas}/${total}`;
      badge.classList.toggle("pp-fab__badge--complete", totalCompleto);
    }
    fab.setAttribute(
      "aria-label",
      `Primeiros passos — ${concluidas} de ${total} concluídas`
    );

    fab.classList.remove("pp-fab--novo", "pp-fab--pulse", "pp-fab--minimized");
    if (concluidas === 0) {
      fab.classList.add("pp-fab--novo");
      if (!REDUCED_MOTION) fab.classList.add("pp-fab--pulse");
    } else if (totalCompleto) {
      fab.classList.add("pp-fab--minimized");
    }
  };

  purgeLegacyStorage();

  /* ---------- FAB (dashboard) ---------- */
  const fab = document.getElementById("pp-fab");
  if (fab && !document.getElementById("pp-page")) {
    if (isDismissed()) {
      document.documentElement.classList.add("pp-dismissed");
      fab.classList.add("pp-fab--hidden");
      return;
    }

    const serverData = loadServerData();
    updateFab(fab, serverData);
    return;
  }

  /* ---------- Página dedicada ---------- */
  const page = document.getElementById("pp-page");
  if (!page) return;

  let serverData = loadServerData();

  const progressLabel = document.getElementById("pp-progress-label");
  const progressPct = document.getElementById("pp-progress-pct");
  const progressBar = document.getElementById("pp-progress-bar");
  const progressFill = document.getElementById("pp-progress-fill");
  const doneBanner = document.getElementById("pp-done-banner");
  const btnDismissDone = document.getElementById("pp-btn-dismiss-done");
  const btnDismissEssencial = document.getElementById("pp-btn-dismiss-essencial");

  const markCardDone = (card) => {
    card.dataset.concluida = "1";
    card.classList.add("pp-card--done", "border-emerald-200/80", "bg-emerald-50/30");
    card.classList.remove(
      "border-gray-200/80",
      "bg-white",
      "shadow-sm",
      "hover:border-gray-300/90",
      "hover:shadow-md",
      "active:scale-[0.99]"
    );
    if (!REDUCED_MOTION) {
      card.classList.add("pp-card--just-done");
      setTimeout(() => card.classList.remove("pp-card--just-done"), 400);
    }

    const icon = card.querySelector(".pp-card__icon");
    if (icon) {
      icon.className =
        "pp-card__icon flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-600";
      icon.innerHTML = '<i class="fa-solid fa-check text-base"></i>';
    }

    const badge = card.querySelector(".pp-card__badge");
    if (badge) {
      badge.className =
        "pp-card__badge rounded-full bg-emerald-100 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700";
      badge.textContent = "Concluído";
    }

    card.querySelector(".pp-card__actions")?.classList.add("hidden");
  };

  const updateUI = () => {
    const { concluidas, total, percentual, totalCompleto } = calcProgress(serverData);

    if (progressLabel) {
      progressLabel.textContent = `${concluidas} de ${total} etapas concluídas`;
    }
    if (progressPct) progressPct.textContent = `${percentual}%`;
    if (progressFill) progressFill.style.width = `${percentual}%`;
    if (progressBar) progressBar.setAttribute("aria-valuenow", String(percentual));

    page.querySelectorAll("[data-pp-etapa]").forEach((card) => {
      const id = card.dataset.ppEtapa;
      const etapa = (serverData.etapas || []).find((e) => e.id === id);
      if (!etapa) return;
      if (etapaConcluida(id, etapa.concluida) && card.dataset.concluida !== "1") {
        markCardDone(card);
      }
    });

    if (totalCompleto) {
      doneBanner?.classList.remove("hidden");
    }

    if (totalCompleto && !document.getElementById("pp-btn-dismiss-essencial")) {
      const footer = page.querySelector(".pp-page-footer .flex");
      if (footer) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.id = "pp-btn-dismiss-essencial";
        btn.className =
          "pp-btn-dismiss text-sm font-medium text-brand-600 hover:text-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40 rounded px-1";
        btn.textContent = "Não mostrar o atalho novamente";
        btn.addEventListener("click", () => setDismissed({ showFeedback: true }));
        footer.appendChild(btn);
      }
    }
  };

  const onDismissClick = () => setDismissed({ showFeedback: true });

  page.addEventListener("click", (e) => {
    const skipBtn = e.target.closest("[data-pp-skip-cartao]");
    if (!skipBtn) return;
    e.preventDefault();
    try {
      localStorage.setItem(storageKey(LS_SKIP_CARTAO_BASE), "1");
    } catch {
      /* ignore */
    }
    updateUI();
  });

  btnDismissDone?.addEventListener("click", onDismissClick);
  btnDismissEssencial?.addEventListener("click", onDismissClick);

  if (isDismissed()) {
    markDismissButtons();
  }

  updateUI();
})();
