(function () {
  "use strict";

  const POLL_MS = 1500;
  const MAX_POLL = 120;

  function getRoot() {
    return document.getElementById("export-drawer-root");
  }

  function qs(sel) {
    const root = getRoot();
    return root ? root.querySelector(sel) : null;
  }

  function csrfToken() {
    const root = getRoot();
    const el =
      (root && root.querySelector("[name=csrfmiddlewaretoken]")) ||
      document.querySelector("[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  }

  async function parseJsonResponse(resp) {
    const contentType = resp.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      return resp.json();
    }
    if (resp.status === 403) {
      throw new Error("Não foi possível validar a sessão. Recarregue a página e tente novamente.");
    }
    throw new Error(`Erro ao comunicar com o servidor (${resp.status}).`);
  }

  function filtrosFromPage(btn) {
    const q = btn.getAttribute("data-filtros-query");
    if (q) return q.replace(/^\?/, "");
    const url = btn.getAttribute("data-filtros-url");
    if (url) {
      const idx = url.indexOf("?");
      return idx >= 0 ? url.slice(idx + 1) : "";
    }
    return window.location.search.replace(/^\?/, "");
  }

  function resetDrawerUi() {
    const status = qs("#export-status");
    const confirmar = qs("#export-btn-confirmar");
    const download = qs("#export-btn-download");
    if (status) {
      status.textContent = "";
      status.classList.add("hidden");
    }
    if (confirmar) {
      confirmar.classList.remove("hidden");
      confirmar.disabled = false;
    }
    if (download) {
      download.classList.add("hidden");
      download.removeAttribute("href");
    }
  }

  function abrirDrawer(dominio, filtrosQuery) {
    const root = getRoot();
    if (!root) return;
    const dominioEl = qs("#export-dominio");
    const filtrosEl = qs("#export-filtros-query");
    if (dominioEl) dominioEl.value = dominio || "transacoes";
    if (filtrosEl) filtrosEl.value = filtrosQuery || "";
    resetDrawerUi();
    root.classList.remove("hidden");
    root.setAttribute("aria-hidden", "false");
  }

  function fecharDrawer() {
    const root = getRoot();
    if (!root) return;
    root.classList.add("hidden");
    root.setAttribute("aria-hidden", "true");
    resetDrawerUi();
  }

  function formatoSelecionado() {
    const el = qs('input[name="export_formato"]:checked');
    return el ? el.value : "csv";
  }

  function dominioEfetivo() {
    const dominioEl = qs("#export-dominio");
    const dominio = dominioEl ? dominioEl.value : "transacoes";
    if (formatoSelecionado() === "pdf") return "relatorio_pdf";
    return dominio;
  }

  function setStatus(msg, isError) {
    const box = qs("#export-status");
    if (!box) return;
    box.textContent = msg;
    box.classList.remove("hidden");
    box.classList.toggle("text-red-600", !!isError);
    box.classList.toggle("bg-red-50", !!isError);
    box.classList.toggle("text-gray-700", !isError);
    box.classList.toggle("bg-gray-50", !isError);
  }

  function onFormatoChange() {
    const download = qs("#export-btn-download");
    const confirmar = qs("#export-btn-confirmar");
    if (download && !download.classList.contains("hidden")) {
      download.classList.add("hidden");
      download.removeAttribute("href");
    }
    if (confirmar) {
      confirmar.classList.remove("hidden");
      confirmar.disabled = false;
    }
    const status = qs("#export-status");
    if (status && status.textContent === "Arquivo pronto!") {
      status.classList.add("hidden");
      status.textContent = "";
    }
  }

  async function pollJob(jobId) {
    let attempts = 0;
    while (attempts < MAX_POLL) {
      const resp = await fetch(`/relatorios/api/export/jobs/${jobId}/`, {
        credentials: "same-origin",
      });
      if (!resp.ok) throw new Error("Erro ao consultar status.");
      const data = await parseJsonResponse(resp);
      if (data.status === "ready" && data.download_url) return data;
      if (data.status === "error") throw new Error(data.erro || "Falha na exportação.");
      if (data.status === "cancelled") throw new Error("Exportação cancelada.");
      setStatus(
        data.status === "processing" ? "Gerando arquivo…" : "Na fila…",
        false
      );
      await new Promise((r) => setTimeout(r, POLL_MS));
      attempts += 1;
    }
    throw new Error("Tempo esgotado. Tente novamente em Exportar.");
  }

  async function iniciarExport() {
    const btn = qs("#export-btn-confirmar");
    if (!btn) return;
    btn.disabled = true;
    setStatus("Preparando…", false);

    const token = csrfToken();
    if (!token) {
      setStatus("Token de segurança ausente. Recarregue a página.", true);
      btn.disabled = false;
      return;
    }

    const filtrosEl = qs("#export-filtros-query");
    const filtrosQuery = filtrosEl ? filtrosEl.value : "";
    const dominio = dominioEfetivo();
    const formato = formatoSelecionado();
    const url = `/relatorios/api/export/jobs/?${filtrosQuery}`;

    const download = qs("#export-btn-download");
    if (download) {
      download.classList.add("hidden");
      download.removeAttribute("href");
    }

    try {
      const resp = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": token,
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({ dominio, formato }),
      });
      const data = await parseJsonResponse(resp);
      if (!resp.ok) {
        throw new Error(data.detail || "Não foi possível iniciar a exportação.");
      }
      const jobId = data.job_id;
      if (data.linhas_estimadas) {
        setStatus(`Processando ~${data.linhas_estimadas.toLocaleString("pt-BR")} linhas…`, false);
      }
      const ready = await pollJob(jobId);
      setStatus("Arquivo pronto!", false);
      if (download) {
        download.href = ready.download_url;
        download.classList.remove("hidden");
      }
      btn.classList.add("hidden");
      if (download) download.click();
    } catch (err) {
      setStatus(err.message || "Erro desconhecido.", true);
      btn.disabled = false;
    }
  }

  document.addEventListener("click", function (e) {
    const abrir = e.target.closest(".js-abrir-export");
    if (abrir) {
      e.preventDefault();
      abrirDrawer(abrir.getAttribute("data-dominio"), filtrosFromPage(abrir));
      return;
    }
    if (e.target.closest(".js-fechar-export")) {
      fecharDrawer();
    }
  });

  document.addEventListener("change", function (e) {
    if (e.target.matches('#export-drawer-root input[name="export_formato"]')) {
      onFormatoChange();
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    const confirmar = qs("#export-btn-confirmar");
    if (confirmar) confirmar.addEventListener("click", iniciarExport);
  });
})();
