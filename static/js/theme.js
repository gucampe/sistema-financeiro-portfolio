/**
 * Tema claro/escuro do SaaS.
 * Só muda se a pessoa escolher — nunca segue o sistema operacional.
 */
(() => {
  const COOKIE = "granago_tema";
  const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)");

  const csrfToken = () => {
    const el = document.querySelector("[name=csrfmiddlewaretoken]");
    if (el && el.value) return el.value;
    const m = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  };

  const isEscuro = () => document.documentElement.classList.contains("dark");

  const atual = () => (isEscuro() ? "escuro" : "claro");

  const coresGrafico = () => {
    const dark = isEscuro();
    return {
      doughnutBorder: dark ? "#1a211e" : "#ffffff",
      tick: dark ? "#8b9a94" : "#6b7280",
      tickStrong: dark ? "#c5d0ca" : "#4b5563",
      grid: dark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.04)",
      legend: dark ? "#c5d0ca" : "#6b7280",
      saldo: dark ? "#6b7a74" : "#d1d5db",
    };
  };

  const setCookie = (tema) => {
    const secure = window.location.protocol === "https:" ? "; Secure" : "";
    document.cookie = `${COOKIE}=${tema}; path=/; max-age=${60 * 60 * 24 * 400}; SameSite=Lax${secure}`;
  };

  const syncChrome = (tema) => {
    const root = document.documentElement;
    root.classList.toggle("dark", tema === "escuro");
    root.setAttribute("data-tema", tema);
    try {
      localStorage.setItem("granago_tema", tema);
    } catch {
      /* private mode */
    }
    setCookie(tema);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.setAttribute("content", tema === "escuro" ? "#101614" : "#f4f5f7");
    }
    document.querySelectorAll("[data-tema-toggle]").forEach((btn) => {
      const dark = tema === "escuro";
      btn.setAttribute("aria-pressed", dark ? "true" : "false");
      btn.setAttribute("aria-label", dark ? "Ativar modo claro" : "Ativar modo escuro");
      btn.title = dark ? "Modo claro" : "Modo escuro";
    });
    document.querySelectorAll("[data-tema-opcao]").forEach((el) => {
      const on = el.getAttribute("data-tema-opcao") === tema;
      el.setAttribute("aria-pressed", on ? "true" : "false");
      el.classList.toggle("ring-2", on);
      el.classList.toggle("ring-brand-500", on);
      el.classList.toggle("border-brand-500", on);
      el.classList.toggle("border-gray-200", !on);
    });
    document.querySelectorAll("[data-tema-icon='lua']").forEach((el) => {
      el.classList.toggle("hidden", tema === "escuro");
    });
    document.querySelectorAll("[data-tema-icon='sol']").forEach((el) => {
      el.classList.toggle("hidden", tema !== "escuro");
    });
    document.dispatchEvent(new CustomEvent("granago:tema", { detail: { tema } }));
  };

  const persist = (tema) => {
    const url = document.documentElement.getAttribute("data-tema-url");
    if (!url) return;
    const token = csrfToken();
    fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": token,
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({ tema }),
    }).catch(() => {});
  };

  const viewportSize = () => {
    const vv = window.visualViewport;
    return {
      w: vv && vv.width ? vv.width : window.innerWidth,
      h: vv && vv.height ? vv.height : window.innerHeight,
    };
  };

  const pontoOrigem = (event) => {
    const alvo = event && event.target && event.target.closest
      ? event.target.closest("[data-tema-toggle], [data-tema-opcao]")
      : null;
    if (alvo) {
      const b = alvo.getBoundingClientRect();
      return { x: b.left + b.width / 2, y: b.top + b.height / 2 };
    }
    if (event && Number.isFinite(event.clientX) && Number.isFinite(event.clientY) && (event.clientX > 0 || event.clientY > 0)) {
      return { x: event.clientX, y: event.clientY };
    }
    const { w, h } = viewportSize();
    return { x: w / 2, y: h / 2 };
  };

  const maxRadius = (x, y) => {
    const { w, h } = viewportSize();
    return Math.hypot(Math.max(x, w - x), Math.max(y, h - y));
  };

  const DURACAO_MS = 1700;
  const EASE_REVEAL = "cubic-bezier(0.45, 0, 0.55, 1)";

  const prepararReveal = (x, y) => {
    const root = document.documentElement;
    root.style.setProperty("--tema-cx", `${Math.round(x)}px`);
    root.style.setProperty("--tema-cy", `${Math.round(y)}px`);
    root.style.setProperty("--tema-r", `${Math.ceil(maxRadius(x, y))}px`);
  };

  const revealFallback = (tema, apply, done) => {
    const overlay = document.createElement("div");
    const anterior = tema === "escuro" ? "#f4f5f7" : "#101614";
    overlay.setAttribute("aria-hidden", "true");
    overlay.style.cssText = [
      "position:fixed",
      "inset:0",
      "z-index:2147483646",
      "pointer-events:none",
      `background:${anterior}`,
      "opacity:1",
    ].join(";");
    document.body.appendChild(overlay);
    apply();
    requestAnimationFrame(() => {
      overlay.style.transition = `opacity ${DURACAO_MS}ms ${EASE_REVEAL}`;
      overlay.style.opacity = "0";
    });
    const finish = () => {
      if (overlay.dataset.done === "1") return;
      overlay.dataset.done = "1";
      overlay.removeEventListener("transitionend", finish);
      overlay.remove();
      done();
    };
    overlay.addEventListener("transitionend", finish);
    window.setTimeout(finish, DURACAO_MS + 200);
  };

  let animando = false;

  const aplicar = async (tema, event) => {
    const next = tema === "escuro" ? "escuro" : "claro";
    if (next === atual() || animando) return;
    const { x, y } = pontoOrigem(event);
    const root = document.documentElement;
    const go = () => syncChrome(next);
    const limparAnimacao = () => {
      root.classList.remove("tema-animando");
      animando = false;
    };

    if (REDUCED.matches) {
      syncChrome(next);
      persist(next);
      return;
    }

    animando = true;
    root.classList.add("tema-animando");
    prepararReveal(x, y);

    if (typeof document.startViewTransition === "function") {
      try {
        const transition = document.startViewTransition(go);
        persist(next);
        Promise.all([
          transition.finished.catch(() => {}),
          new Promise((resolve) => window.setTimeout(resolve, DURACAO_MS)),
        ]).finally(limparAnimacao);
        return;
      } catch {
        /* fallback abaixo */
      }
    }

    revealFallback(next, go, limparAnimacao);
    persist(next);
  };

  const onToggle = (event) => {
    aplicar(isEscuro() ? "claro" : "escuro", event);
  };

  document.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-tema-toggle]");
    if (toggle) {
      event.preventDefault();
      onToggle(event);
      return;
    }
    const opcao = event.target.closest("[data-tema-opcao]");
    if (opcao) {
      event.preventDefault();
      aplicar(opcao.getAttribute("data-tema-opcao"), event);
    }
  });

  window.GranaGoTema = {
    atual,
    aplicar,
    coresGrafico,
    isEscuro,
  };

  syncChrome(atual());
})();
