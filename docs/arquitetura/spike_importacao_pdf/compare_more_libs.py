#!/usr/bin/env python3
"""Spike: mais libs OSS (palavras + bbox) vs o mesmo interpretador.

Não é código de produção. Venv isolada /tmp/spike_pdf_venv.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from compare_assertiveness import (
    SYNTH_GOLD,
    Word,
    extract_words_pdfplumber,
    extract_words_pymupdf,
    interpret,
    score_identity,
)


def _pdfium_chars_to_words(page_i: int, page_h: float, textpage) -> list[Word]:
    n = textpage.count_chars()
    words: list[Word] = []
    buf_ch: list[str] = []
    buf_box: list[tuple[float, float, float, float]] = []

    def flush() -> None:
        if not buf_ch:
            return
        text = "".join(buf_ch)
        if text.strip():
            left = min(b[0] for b in buf_box)
            bottom = min(b[1] for b in buf_box)
            right = max(b[2] for b in buf_box)
            top = max(b[3] for b in buf_box)
            y0 = page_h - top
            y1 = page_h - bottom
            words.append(Word(page_i, left, y0, right, y1, text.strip()))
        buf_ch.clear()
        buf_box.clear()

    for i in range(n):
        ch = textpage.get_text_range(i, 1)
        box = textpage.get_charbox(i)
        if not ch or ch.isspace() or ch == "\x00":
            flush()
            continue
        buf_ch.append(ch)
        buf_box.append(box)
    flush()
    return words


def extract_words_pypdfium2(path: Path) -> list[Word] | dict:
    import pypdfium2 as pdfium

    try:
        doc = pdfium.PdfDocument(str(path))
    except Exception as exc:
        return {"error": type(exc).__name__}
    words: list[Word] = []
    try:
        for i, page in enumerate(doc):
            w, h = page.get_size()
            tp = page.get_textpage()
            words.extend(_pdfium_chars_to_words(i + 1, float(h), tp))
            tp.close()
    except Exception as exc:
        return {"error": type(exc).__name__, "detail": str(exc)[:160]}
    finally:
        doc.close()
    return words


def extract_words_pdf_oxide(path: Path) -> list[Word] | dict:
    from pdf_oxide import PdfDocument

    try:
        doc = PdfDocument(str(path))
    except Exception as exc:
        return {"error": type(exc).__name__, "detail": str(exc)[:160]}
    words: list[Word] = []
    try:
        for i, page in enumerate(doc):
            h = float(page.height)
            for w in page.words or []:
                x, y, ww, hh = w.bbox
                # bbox = (x, y_pdf_bottom, width, height)
                y0 = h - (float(y) + float(hh))
                y1 = h - float(y)
                words.append(
                    Word(
                        i + 1,
                        float(x),
                        y0,
                        float(x) + float(ww),
                        y1,
                        str(w.text or ""),
                    )
                )
    except Exception as exc:
        return {"error": type(exc).__name__, "detail": str(exc)[:160]}
    return words


def extract_words_pypdf(path: Path) -> list[Word] | dict:
    from pypdf import PdfReader, mult

    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        return {"error": type(exc).__name__, "detail": str(exc)[:160]}
    if getattr(reader, "is_encrypted", False):
        try:
            ok = reader.decrypt("")
            if not ok:
                return {"error": "encrypted"}
        except Exception:
            return {"error": "encrypted"}
    words: list[Word] = []
    try:
        for i, page in enumerate(reader.pages):
            h = float(page.mediabox.height)
            frags: list[Word] = []

            def vis(text, cm, tm, font_dict, font_size, _i=i, _h=h, _frags=frags):
                if not text or not str(text).strip():
                    return
                ctm = mult(tm, cm)
                x = float(ctm[4])
                y_pdf = float(ctm[5])
                y0 = _h - y_pdf
                # fragmento pode ser célula inteira; parte em tokens
                raw = str(text).replace("\n", " ").strip()
                x_cur = x
                for tok in raw.split():
                    w = max(4.0, len(tok) * 5.0)
                    _frags.append(Word(_i + 1, x_cur, y0, x_cur + w, y0 + 10, tok))
                    x_cur += w + 4

            page.extract_text(visitor_text=vis)
            words.extend(frags)
    except Exception as exc:
        return {"error": type(exc).__name__, "detail": str(exc)[:160]}
    return words


LIBS = [
    ("pymupdf", extract_words_pymupdf),
    ("pdfplumber", extract_words_pdfplumber),
    ("pypdfium2", extract_words_pypdfium2),
    ("pdf_oxide", extract_words_pdf_oxide),
    ("pypdf", extract_words_pypdf),
]


def eval_file(path: Path, gold, y_tol: float) -> dict:
    row = {"file": path.name}
    for name, fn in LIBS:
        t0 = time.perf_counter()
        raw = fn(path)
        elapsed = round(time.perf_counter() - t0, 4)
        if isinstance(raw, dict) and "error" in raw:
            row[name] = {"error": raw["error"], "elapsed_s": elapsed}
            continue
        cands = interpret(raw, y_tol)  # type: ignore
        block = {"n_words": len(raw), "n_pred": len(cands), "elapsed_s": elapsed}  # type: ignore
        if gold is not None:
            ident = score_identity(cands, gold)
            block["identity"] = ident
        row[name] = block
    return row


def main() -> None:
    corpus = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/spike_pdf_corpus")
    y_tol = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
    synth = []
    for name, gold in SYNTH_GOLD.items():
        p = corpus / name
        if not p.exists():
            continue
        synth.append(eval_file(p, gold, y_tol))

    real_dir = Path(
        "/home/gucampe/.cursor/projects/home-gucampe-Documentos-Projetos-sistema-financeiro/attachments/7a73b6ec-e9bc-4346-a398-ec4fcb74a361"
    )
    reals = []
    for label, fname in [
        ("santander", "ComprovanteSantander-1787356973725.pdf"),
        ("bradesco", "7ef1985f-09c4-4437-b40d-c369f62b9faa.pdf"),
        ("nubank", "extrato_nubank.pdf"),
        ("caixa", "extrato_caixa.pdf"),
        ("comprovante_2p", "comprovante2026-08-21_233033.pdf"),
        ("nubank_jul", "NU_7375439292_01JUL2025_31JUL2025.pdf"),
    ]:
        p = real_dir / fname
        if not p.exists():
            continue
        r = eval_file(p, None, y_tol)
        r["label"] = label
        reals.append(r)

    out = {"y_tol": y_tol, "synthetic": synth, "real": reals}
    out_path = corpus / "assertiveness_more_libs.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"wrote {out_path}")
    names = [n for n, _ in LIBS]
    print("\n=== SINTÉTICOS F1 identidade / n_pred / tempo(s) ===")
    hdr = f"{'arquivo':32}" + "".join(f" {n[:10]:>10}" for n in names)
    print(hdr)
    for r in synth:
        line = f"{r['file']:32}"
        for n in names:
            b = r.get(n) or {}
            if "error" in b:
                line += f" {'ERR':>10}"
            else:
                f1 = (b.get("identity") or {}).get("f1", "-")
                line += f" {str(f1):>10}"
        print(line)
        line = f"{'  n_pred/t':32}"
        for n in names:
            b = r.get(n) or {}
            if "error" in b:
                line += f" {b.get('error','err')[:10]:>10}"
            else:
                line += f" {b.get('n_pred')}@{b.get('elapsed_s')}s"
                line = line  # placeholder
        # reprint n_pred compact
        print(
            "  "
            + " | ".join(
                f"{n[:8]}={ (r.get(n) or {}).get('n_pred', (r.get(n) or {}).get('error')) }/{(r.get(n) or {}).get('elapsed_s')}"
                for n in names
            )
        )
    print("\n=== REAIS n_pred (sem gabarito) ===")
    for r in reals:
        print(
            r.get("label"),
            " | ".join(
                f"{n[:8]}={ (r.get(n) or {}).get('n_pred', (r.get(n) or {}).get('error')) } w={(r.get(n) or {}).get('n_words')} t={(r.get(n) or {}).get('elapsed_s')}"
                for n in names
            ),
        )


if __name__ == "__main__":
    main()
