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

  const maxRadius = (x, y) =>
    Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y));

  const revealFallback = (tema, x, y, done) => {
    const overlay = document.createElement("div");
    const r = maxRadius(x, y);
    overlay.setAttribute("aria-hidden", "true");
    overlay.style.cssText = [
      "position:fixed",
      "inset:0",
      "z-index:2147483646",
      "pointer-events:none",
      `background:${tema === "escuro" ? "#101614" : "#f4f5f7"}`,
      `clip-path:circle(0px at ${x}px ${y}px)`,
    ].join(";");
    document.body.appendChild(overlay);
    requestAnimationFrame(() => {
      overlay.style.transition = "clip-path 1400ms cubic-bezier(0.22, 1, 0.36, 1)";
      overlay.style.clipPath = `circle(${r}px at ${x}px ${y}px)`;
    });
    const finish = () => {
      if (overlay.dataset.done === "1") return;
      overlay.dataset.done = "1";
      overlay.removeEventListener("transitionend", finish);
      done();
      overlay.remove();
    };
    overlay.addEventListener("transitionend", finish);
    window.setTimeout(finish, 1650);
  };

  const aplicar = async (tema, event) => {
    const next = tema === "escuro" ? "escuro" : "claro";
    if (next === atual()) return;
    const x = event && Number.isFinite(event.clientX) ? event.clientX : window.innerWidth / 2;
    const y = event && Number.isFinite(event.clientY) ? event.clientY : window.innerHeight / 2;
    const root = document.documentElement;
    const go = () => {
      root.classList.add("tema-animando");
      syncChrome(next);
    };
    const limparAnimacao = () => {
      window.setTimeout(() => root.classList.remove("tema-animando"), 1200);
    };

    if (REDUCED.matches) {
      syncChrome(next);
      persist(next);
      return;
    }

    if (typeof document.startViewTransition === "function") {
      try {
        const transition = document.startViewTransition(go);
        await transition.ready;
        const r = maxRadius(x, y);
        document.documentElement.animate(
          {
            clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${r}px at ${x}px ${y}px)`],
          },
          {
            duration: 1400,
            easing: "cubic-bezier(0.22, 1, 0.36, 1)",
            pseudoElement: "::view-transition-new(root)",
          }
        );
        persist(next);
        transition.finished.finally(limparAnimacao).catch(() => {});
        return;
      } catch {
        /* fallback abaixo */
      }
    }

    revealFallback(next, x, y, () => {
      go();
      limparAnimacao();
    });
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
