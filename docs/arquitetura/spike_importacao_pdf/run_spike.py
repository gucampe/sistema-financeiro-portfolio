#!/usr/bin/env python3
"""Spike isolado: PyMuPDF vs pdfplumber. Não é código de produção.

Roda cada (lib, arquivo) em subprocesso para medir RSS de pico.
"""
from __future__ import annotations

import json
import os
import re
import resource
import sys
import time
import traceback
from pathlib import Path


DATE_RE = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")
MONEY_RE = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2}")


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def classify_pymupdf(doc) -> dict:
    pages = doc.page_count
    chars = 0
    images = 0
    words = 0
    pages_with_text = 0
    pages_image_only = 0
    for i in range(pages):
        page = doc[i]
        text = page.get_text("text") or ""
        chars += len(text.strip())
        if text.strip():
            pages_with_text += 1
        imgs = page.get_images() or []
        images += len(imgs)
        words += len(page.get_text("words") or [])
        if not text.strip() and imgs:
            pages_image_only += 1
    density = chars / max(pages, 1)
    if pages_image_only == pages:
        kind = "raster"
    elif density < 40 and images:
        kind = "raster_or_hybrid"
    else:
        kind = "textual"
    return {
        "pages": pages,
        "chars": chars,
        "words": words,
        "images": images,
        "pages_with_text": pages_with_text,
        "pages_image_only": pages_image_only,
        "chars_per_page": round(density, 1),
        "kind_guess": kind,
        "needs_password": bool(doc.is_encrypted),
    }


def run_pymupdf(path: str) -> dict:
    import pymupdf

    t0 = time.perf_counter()
    rss0 = rss_mb()
    out: dict = {"lib": "pymupdf", "ok": False}
    try:
        doc = pymupdf.open(path)
        if doc.is_encrypted:
            out["encrypted"] = True
            out["needs_password"] = True
            opened = doc.authenticate("")
            out["empty_password_ok"] = bool(opened)
            if not opened:
                out["elapsed_s"] = round(time.perf_counter() - t0, 4)
                out["rss_max_mb"] = round(rss_mb(), 2)
                out["rss_delta_mb"] = round(rss_mb() - rss0, 2)
                out["ok"] = True
                out["skipped"] = "encrypted"
                doc.close()
                return out
        info = classify_pymupdf(doc)
        out.update(info)
        page0 = doc[0]
        words = page0.get_text("words") or []
        out["page0_words"] = len(words)
        out["page0_word_sample"] = [
            {"x0": round(w[0], 1), "y0": round(w[1], 1), "t": w[4][:40]} for w in words[:8]
        ]
        dict_text = page0.get_text("dict")
        blocks = dict_text.get("blocks") or []
        out["page0_blocks"] = len(blocks)
        raw = page0.get_text("text") or ""
        out["page0_dates"] = DATE_RE.findall(raw)[:12]
        out["page0_money"] = MONEY_RE.findall(raw)[:12]
        tables = []
        try:
            for i in range(min(doc.page_count, 5)):
                found = doc[i].find_tables()
                tabs = found.tables if found else []
                for tb in tabs:
                    tables.append(
                        {
                            "page": i + 1,
                            "rows": tb.row_count,
                            "cols": tb.col_count,
                            "header": (tb.header.names if tb.header else None),
                        }
                    )
        except Exception as exc:
            out["find_tables_error"] = type(exc).__name__
        out["tables"] = tables
        out["n_tables"] = len(tables)
        # classificação estrutural
        if info["kind_guess"].startswith("raster"):
            structure = "raster"
        elif tables:
            structure = "textual_tabular"
        elif out["page0_words"] >= 20 and (out["page0_dates"] or out["page0_money"]):
            xs = [w[0] for w in words]
            if xs:
                span = max(xs) - min(xs)
                structure = "textual_aligned" if span > 120 else "textual_linear"
            else:
                structure = "textual_linear"
        else:
            structure = "textual_linear"
        out["structure_guess"] = structure
        out["ok"] = True
        doc.close()
    except Exception as exc:
        out["error"] = type(exc).__name__
        out["error_detail"] = str(exc)[:200]
    out["elapsed_s"] = round(time.perf_counter() - t0, 4)
    out["rss_max_mb"] = round(rss_mb(), 2)
    out["rss_delta_mb"] = round(max(0.0, rss_mb() - rss0), 2)
    return out


def run_pdfplumber(path: str) -> dict:
    import pdfplumber

    t0 = time.perf_counter()
    rss0 = rss_mb()
    out: dict = {"lib": "pdfplumber", "ok": False}
    try:
        with pdfplumber.open(path) as pdf:
            if getattr(pdf, "is_encrypted", False):
                out["encrypted"] = True
            pages = len(pdf.pages)
            chars = 0
            words_n = 0
            tables = []
            page0_words = []
            raw0 = ""
            for i, page in enumerate(pdf.pages[: min(pages, 5)]):
                raw = page.extract_text() or ""
                chars += len(raw)
                ws = page.extract_words() or []
                words_n += len(ws)
                if i == 0:
                    raw0 = raw
                    page0_words = ws
                try:
                    extracted = page.extract_tables() or []
                except Exception as exc:
                    out["extract_tables_error"] = type(exc).__name__
                    extracted = []
                for tb in extracted:
                    tables.append(
                        {
                            "page": i + 1,
                            "rows": len(tb) if tb else 0,
                            "cols": len(tb[0]) if tb and tb[0] else 0,
                            "header": tb[0][:8] if tb else None,
                        }
                    )
            # remaining pages: text only for char count
            for page in pdf.pages[5:]:
                chars += len(page.extract_text() or "")
            out["pages"] = pages
            out["chars"] = chars
            out["words"] = words_n
            out["page0_words"] = len(page0_words)
            out["page0_word_sample"] = [
                {"x0": round(w.get("x0", 0), 1), "y0": round(w.get("top", 0), 1), "t": str(w.get("text", ""))[:40]}
                for w in page0_words[:8]
            ]
            out["page0_dates"] = DATE_RE.findall(raw0)[:12]
            out["page0_money"] = MONEY_RE.findall(raw0)[:12]
            out["tables"] = tables
            out["n_tables"] = len(tables)
            if tables:
                structure = "textual_tabular"
            elif out["page0_words"] >= 20:
                xs = [w.get("x0", 0) for w in page0_words]
                structure = "textual_aligned" if xs and (max(xs) - min(xs) > 120) else "textual_linear"
            else:
                structure = "textual_linear"
            out["structure_guess"] = structure
            out["ok"] = True
    except Exception as exc:
        out["error"] = type(exc).__name__
        out["error_detail"] = str(exc)[:200]
    out["elapsed_s"] = round(time.perf_counter() - t0, 4)
    out["rss_max_mb"] = round(rss_mb(), 2)
    out["rss_delta_mb"] = round(max(0.0, rss_mb() - rss0), 2)
    return out


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "--one":
        lib, path = sys.argv[2], sys.argv[3]
        fn = run_pymupdf if lib == "pymupdf" else run_pdfplumber
        print(json.dumps(fn(path), ensure_ascii=False))
        return

    corpus = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/spike_pdf_corpus")
    files = sorted(corpus.glob("*.pdf"))
    results = []
    import subprocess

    for pdf in files:
        size = pdf.stat().st_size
        row = {"file": pdf.name, "bytes": size}
        for lib in ("pymupdf", "pdfplumber"):
            proc = subprocess.run(
                [sys.executable, "-W", "ignore", __file__, "--one", lib, str(pdf)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            if proc.returncode != 0:
                row[lib] = {
                    "ok": False,
                    "error": "subprocess",
                    "stderr": stderr[-400:],
                    "stdout": stdout[-400:],
                }
            else:
                try:
                    payload = stdout.strip().splitlines()[-1] if stdout.strip() else ""
                    row[lib] = json.loads(payload)
                except json.JSONDecodeError:
                    row[lib] = {
                        "ok": False,
                        "stdout": stdout[:400],
                        "stderr": stderr[-400:],
                    }
        results.append(row)

    out_path = corpus / "spike_results.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(json.dumps({"n": len(results), "out": str(out_path)}, indent=2))
    for row in results:
        pm = row.get("pymupdf") or {}
        pp = row.get("pdfplumber") or {}
        print(
            f"{row['file']:40} {row['bytes']:8}B  "
            f"mu t={pm.get('elapsed_s')}s rss={pm.get('rss_max_mb')}MB tab={pm.get('n_tables')} st={pm.get('structure_guess')} enc={pm.get('needs_password') or pm.get('encrypted')} err={pm.get('error')}  "
            f"pl t={pp.get('elapsed_s')}s rss={pp.get('rss_max_mb')}MB tab={pp.get('n_tables')} st={pp.get('structure_guess')} err={pp.get('error')}"
        )


if __name__ == "__main__":
    main()
