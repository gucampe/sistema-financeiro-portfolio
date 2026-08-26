#!/usr/bin/env python3
"""Compara assertividade PyMuPDF vs pdfplumber (spike, não produção).

Mesmo interpretador (palavras + bbox → linhas candidatas) nas duas libs.
Sintéticos: P/R/F1 contra gabarito do gerador.
Reais: acordo entre libs + contagens; sem imprimir PII (descrição/valor/nome).

Uso (venv isolada):
  /tmp/spike_pdf_venv/bin/python compare_assertiveness.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

DATE_FULL = re.compile(r"^\d{2}/\d{2}/\d{4}$")
DATE_DM = re.compile(r"^\d{2}/\d{2}$")
DATE_DMY2 = re.compile(r"^\d{2}/\d{2}/\d{2}$")
MONEY = re.compile(
    r"^[+-]?(?:R\$\s*)?-?\d{1,3}(?:\.\d{3})*,\d{2}$|^[+-]?(?:R\$\s*)?\d+,\d{2}$"
)
MONTH = re.compile(
    r"^(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)$", re.I
)
HEADER_TOKENS = {
    "data",
    "historico",
    "histórico",
    "descricao",
    "descrição",
    "debito",
    "débito",
    "credito",
    "crédito",
    "valor",
    "saldo",
    "lançamento",
    "lancamento",
}
SKIP_DESC = re.compile(r"saldo\s+anterior", re.I)

# Espelha generate_corpus.py
MOVIMENTOS = [
    ("02/03/2026", "SALDO ANTERIOR", "", "", "1.250,00"),
    ("03/03/2026", "PIX ENVIADO JOAO SILVA", "85,00", "", "1.165,00"),
    ("03/03/2026", "PAGTO CONTA LUZ", "210,40", "", "954,60"),
    ("05/03/2026", "PIX RECEBIDO PADARIA CENTRAL", "", "40,00", "994,60"),
    ("07/03/2026", "TED ENVIADA FORNECEDOR ALFA", "1.100,00", "", "-105,40"),
    ("10/03/2026", "SALARIO EMPRESA BETA LTDA", "", "3.200,00", "3.094,60"),
    ("12/03/2026", "DEBITO CARTAO SUPERMERCADO", "327,90", "", "2.766,70"),
    ("15/03/2026", "PIX ENVIADO MARIA SOUZA", "50,00", "", "2.716,70"),
    ("18/03/2026", "RENDIMENTO CONTA", "", "1,12", "2.717,82"),
    ("20/03/2026", "TARIFA PACOTE SERVICOS", "29,90", "", "2.687,92"),
]
POUPANCA = [
    ("02/03/2026", "SALDO ANTERIOR", "", "", "5.000,00"),
    ("10/03/2026", "APLICACAO POUPANCA", "", "200,00", "5.200,00"),
    ("28/03/2026", "RENDIMENTO POUPANCA", "", "12,35", "5.212,35"),
]


def parse_brl(text: str) -> Decimal | None:
    s = (text or "").replace("\xa0", "").replace(" ", "").replace("R$", "")
    s = s.strip()
    if not s:
        return None
    neg = s.startswith("-") or (s.startswith("+") is False and s[:1] == "-")
    if s[0] in "+-":
        neg = s[0] == "-"
        s = s[1:]
    if not re.search(r"\d+,\d{2}$", s) and not re.search(r"\d+\.\d{2}$", s):
        return None
    try:
        if "," in s:
            d = Decimal(s.replace(".", "").replace(",", "."))
        else:
            d = Decimal(s)
    except InvalidOperation:
        return None
    return -d if neg else d


def is_money(text: str) -> bool:
    t = (text or "").replace("\xa0", "").replace(" ", "")
    return bool(MONEY.match(t)) or bool(re.match(r"^[+-]?R\$.*,\d{2}$", t))


def is_date(text: str) -> bool:
    t = (text or "").strip()
    return bool(DATE_FULL.match(t) or DATE_DM.match(t) or DATE_DMY2.match(t))


def norm_desc(text: str) -> str:
    s = (text or "").replace("\n", " ").strip().casefold()
    s = re.sub(r"\s+", " ", s)
    return s


def brl_key(v: Decimal) -> str:
    return f"{v:.2f}"


@dataclass(frozen=True)
class Word:
    page: int
    x0: float
    y0: float
    x1: float
    y1: float
    text: str


@dataclass
class Cand:
    page: int
    data: str
    valor: Decimal
    tipo: str
    desc: str

    def key(self, with_desc: bool = True) -> tuple:
        if with_desc:
            return (self.data, brl_key(self.valor), self.tipo, norm_desc(self.desc))
        return (self.data, brl_key(self.valor), self.tipo)


def gold_from_rows(rows, include_saldo=False) -> list[Cand]:
    out: list[Cand] = []
    for d, h, deb, cred, _saldo in rows:
        if not include_saldo and SKIP_DESC.search(h):
            continue
        if deb:
            valor, tipo = parse_brl(deb), "despesa"
        else:
            valor, tipo = parse_brl(cred), "receita"
        if valor is None:
            continue
        out.append(Cand(page=1, data=d, valor=abs(valor), tipo=tipo, desc=h))
    return out


def gold_05() -> list[Cand]:
    out = []
    saldo = 1000.0
    for i in range(80):
        deb = 10.0 + (i % 7)
        saldo -= deb
        d = f"{(i % 28) + 1:02d}/03/2026"
        desc = f"LANCAMENTO AUTOMATICO {i:03d} COM DESCRICAO EXTENSA PARA TESTE"
        out.append(
            Cand(page=1, data=d, valor=Decimal(f"{deb:.2f}"), tipo="despesa", desc=desc)
        )
    return out


def gold_04() -> list[Cand]:
    first = Cand(
        page=1,
        data="11/03/2026",
        valor=Decimal("85.00"),
        tipo="despesa",
        desc="PIX ENVIADO JOAO DA SILVA SANTOS CPF ***.111.222-**",
    )
    rest = gold_from_rows(MOVIMENTOS[2:5])
    return [first] + rest


def gold_13() -> list[Cand]:
    out = []
    for p in range(40):
        for i in range(32):
            out.append(
                Cand(
                    page=p + 1,
                    data="01/03/2026",
                    valor=Decimal("10.00"),
                    tipo="despesa",
                    desc=f"LANCAMENTO P{p:02d} L{i:02d}",
                )
            )
    return out


def gold_03() -> list[Cand]:
    out = []
    for d, h, deb, cred, _ in MOVIMENTOS[1:]:
        if deb:
            out.append(Cand(1, d, parse_brl(deb), "despesa", h))
        else:
            out.append(Cand(1, d, parse_brl(cred), "receita", h))
    return out


SYNTH_GOLD = {
    "01_structured_table.pdf": gold_from_rows(MOVIMENTOS),
    "02_no_title.pdf": gold_from_rows(MOVIMENTOS),
    "03_signed_amount.pdf": gold_03(),
    "04_multiline.pdf": gold_04(),
    "05_multipage_repeat_header.pdf": gold_05(),
    "06_multi_section.pdf": gold_from_rows(MOVIMENTOS) + gold_from_rows(POUPANCA),
    "07_aligned_text_no_tableobj.pdf": gold_from_rows(MOVIMENTOS),
    "08_draw_order_inverted.pdf": gold_from_rows(MOVIMENTOS),
    "09_linear_prose.pdf": gold_from_rows(MOVIMENTOS),
    "10_image_only.pdf": [],
    "13_many_pages_40.pdf": gold_13(),
    "14_vector_heavy.pdf": gold_from_rows(MOVIMENTOS),
}


def extract_words_pymupdf(path: Path) -> list[Word] | dict:
    import pymupdf

    try:
        doc = pymupdf.open(path)
    except Exception as exc:
        return {"error": type(exc).__name__}
    if doc.is_encrypted:
        ok = doc.authenticate("")
        if not ok:
            doc.close()
            return {"error": "encrypted"}
    words: list[Word] = []
    for i, page in enumerate(doc):
        for w in page.get_text("words") or []:
            words.append(
                Word(i + 1, float(w[0]), float(w[1]), float(w[2]), float(w[3]), str(w[4]))
            )
    doc.close()
    return words


def extract_words_pdfplumber(path: Path) -> list[Word] | dict:
    import pdfplumber

    try:
        pdf = pdfplumber.open(str(path))
    except Exception as exc:
        return {"error": type(exc).__name__, "detail": str(exc)[:120]}
    words: list[Word] = []
    try:
        for i, page in enumerate(pdf.pages):
            for w in page.extract_words() or []:
                words.append(
                    Word(
                        i + 1,
                        float(w["x0"]),
                        float(w["top"]),
                        float(w["x1"]),
                        float(w["bottom"]),
                        str(w.get("text") or ""),
                    )
                )
    except Exception as exc:
        pdf.close()
        return {"error": type(exc).__name__, "detail": str(exc)[:120]}
    pdf.close()
    return words


def cluster_rows(words: list[Word], y_tol: float) -> list[list[Word]]:
    by_page: dict[int, list[Word]] = defaultdict(list)
    for w in words:
        if not (w.text or "").strip():
            continue
        by_page[w.page].append(w)
    rows: list[list[Word]] = []
    for page in sorted(by_page):
        items = sorted(by_page[page], key=lambda w: (w.y0, w.x0))
        current: list[Word] = []
        y_ref = None
        for w in items:
            if y_ref is None or abs(w.y0 - y_ref) <= y_tol:
                current.append(w)
                if y_ref is None:
                    y_ref = w.y0
                else:
                    y_ref = (y_ref * (len(current) - 1) + w.y0) / len(current)
            else:
                rows.append(sorted(current, key=lambda x: x.x0))
                current = [w]
                y_ref = w.y0
        if current:
            rows.append(sorted(current, key=lambda x: x.x0))
    return rows


def merge_money_tokens(row: list[Word]) -> list[Word]:
    """Junta 'R$' + '10,00' ou '-' + '10,00' adjacentes."""
    out: list[Word] = []
    i = 0
    while i < len(row):
        t = row[i].text.strip()
        if i + 1 < len(row) and t in {"R$", "-", "+", "R$-"} :
            nxt = row[i + 1]
            combo = t + nxt.text.strip()
            if is_money(combo) or is_money(nxt.text):
                out.append(
                    Word(row[i].page, row[i].x0, row[i].y0, nxt.x1, nxt.y1, combo)
                )
                i += 2
                continue
        out.append(row[i])
        i += 1
    return out


def row_to_cand(row: list[Word], last_date: str | None, y_tol: float) -> Cand | None:
    row = merge_money_tokens(row)
    texts = [w.text.strip() for w in row]
    joined = " ".join(texts)
    if (
        sum(t.casefold() in HEADER_TOKENS for t in texts) >= 2
        and not any(is_date(t) or is_money(t) for t in texts)
    ):
        return None
    dates = [w for w in row if is_date(w.text.strip())]
    moneys = [w for w in row if is_money(w.text.strip())]
    months = [w for w in row if MONTH.match(w.text.strip())]
    day_toks = [w for w in row if re.fullmatch(r"\d{1,2}", w.text.strip())]

    data = dates[0].text.strip() if dates else None
    if data is None and months and day_toks:
        # Nubank-like: "12 jan 2026" no cabeçalho de grupo
        data = f"{int(day_toks[0].text):02d}/{months[0].text.lower()}"
    if data is None:
        data = last_date
    if not data or not moneys:
        return None
    if SKIP_DESC.search(joined):
        return None

    # Descarta linha que só é saldo corrido sem histórico (poucas palavras)
    non_num = [
        w
        for w in row
        if not is_date(w.text.strip()) and not is_money(w.text.strip())
    ]
    desc = " ".join(w.text for w in non_num)
    desc_n = norm_desc(desc)
    if not desc_n or desc_n in {"", "-", "r$"}:
        return None

    valores = []
    for w in moneys:
        v = parse_brl(w.text)
        if v is not None:
            valores.append((w, v))
    if not valores:
        return None

    # 1 valor: coluna única (com ou sem sinal).
    # 2 valores: movimento + saldo (saldo = mais à direita).
    # 3 valores: débito, crédito, saldo.
    if len(valores) >= 3:
        d_v, c_v = valores[0][1], valores[1][1]
        if d_v != 0 and c_v == 0:
            movement = valores[0]
            tipo_hint = "despesa"
        elif c_v != 0 and d_v == 0:
            movement = valores[1]
            tipo_hint = "receita"
        else:
            return None
    elif len(valores) == 2:
        movement = valores[0]
        tipo_hint = None
    else:
        movement = valores[0]
        tipo_hint = None

    w, v = movement
    if v < 0:
        tipo = "despesa"
        v = abs(v)
    elif tipo_hint:
        tipo = tipo_hint
    elif re.search(r"receb|salar|rendim|credito|crédito", desc_n):
        tipo = "receita"
    elif re.search(
        r"enviad|pagto|debito|débito|tarifa|pix enviado|ted|aplicacao|aplicação",
        desc_n,
    ):
        tipo = "despesa"
    elif len(valores) == 2:
        # D/C com crédito vazio: o único movimento à esquerda do saldo é débito
        tipo = "despesa"
    else:
        tipo = "receita"

    return Cand(page=row[0].page, data=data, valor=v, tipo=tipo, desc=desc)


def interpret(words: list[Word], y_tol: float = 4.0) -> list[Cand]:
    rows = cluster_rows(words, y_tol)
    cands: list[Cand] = []
    last_date = None
    for row in rows:
        # atualiza last_date mesmo em linhas sem dinheiro (cabeçalho Nubank)
        merged = merge_money_tokens(row)
        for w in merged:
            if is_date(w.text.strip()):
                last_date = w.text.strip()
            elif MONTH.match(w.text.strip()):
                days = [x for x in merged if re.fullmatch(r"\d{1,2}", x.text.strip())]
                if days:
                    last_date = f"{int(days[0].text):02d}/{w.text.lower()}"
        cand = row_to_cand(row, last_date, y_tol)
        if cand:
            cands.append(cand)
            last_date = cand.data
    return cands


def _multiset_score(gold_keys, pred_keys) -> dict:
    gold_c = Counter(gold_keys)
    pred_c = Counter(pred_keys)
    tp = 0
    for k, n in gold_c.items():
        tp += min(n, pred_c.get(k, 0))
    fp = sum(pred_c.values()) - tp
    fn = sum(gold_c.values()) - tp
    prec = tp / (tp + fp) if (tp + fp) else 1.0
    rec = tp / (tp + fn) if (tp + fn) else (1.0 if not gold_keys else 0.0)
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {
        "n_gold": len(gold_keys),
        "n_pred": len(pred_keys),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(prec, 3),
        "recall": round(rec, 3),
        "f1": round(f1, 3),
    }


def score(pred: list[Cand], gold: list[Cand], with_desc: bool) -> dict:
    return _multiset_score(
        [g.key(with_desc) for g in gold],
        [p.key(with_desc) for p in pred],
    )


def score_identity(pred: list[Cand], gold: list[Cand]) -> dict:
    """Data + valor, ignora tipo e descrição — 'achou o lançamento'."""
    return _multiset_score(
        [(g.data, brl_key(g.valor)) for g in gold],
        [(p.data, brl_key(p.valor)) for p in pred],
    )


def hashed_keys(cands: list[Cand]) -> set[str]:
    out = set()
    for c in cands:
        payload = f"{c.page}|{c.data}|{brl_key(c.valor)}|{c.tipo}"
        out.add(hashlib.sha256(payload.encode()).hexdigest()[:12])
    return out


def agreement(a: list[Cand], b: list[Cand]) -> dict:
    ka, kb = hashed_keys(a), hashed_keys(b)
    inter = ka & kb
    union = ka | kb
    jacc = len(inter) / len(union) if union else 1.0
    return {
        "n_a": len(a),
        "n_b": len(b),
        "n_inter": len(inter),
        "n_only_a": len(ka - kb),
        "n_only_b": len(kb - ka),
        "jaccard": round(jacc, 3),
    }


def run_file(path: Path, gold: list[Cand] | None, y_tol: float) -> dict:
    mu = extract_words_pymupdf(path)
    pl = extract_words_pdfplumber(path)
    row: dict = {"file": path.name, "y_tol": y_tol}
    for name, raw in (("pymupdf", mu), ("pdfplumber", pl)):
        if isinstance(raw, dict) and "error" in raw:
            row[name] = {"error": raw["error"], "n_words": 0}
            continue
        words: list[Word] = raw  # type: ignore
        cands = interpret(words, y_tol=y_tol)
        block = {
            "n_words": len(words),
            "n_pred": len(cands),
        }
        if gold is not None:
            block["identity"] = score_identity(cands, gold)
            block["with_tipo"] = score(cands, gold, False)
            block["with_desc"] = score(cands, gold, True)
        row[name] = block
        row[f"_{name}_cands"] = cands
    if not row.get("pymupdf", {}).get("error") and not row.get("pdfplumber", {}).get("error"):
        row["agreement"] = agreement(row["_pymupdf_cands"], row["_pdfplumber_cands"])
    row.pop("_pymupdf_cands", None)
    row.pop("_pdfplumber_cands", None)
    return row


def main() -> None:
    corpus = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/spike_pdf_corpus")
    y_tol = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
    synth = []
    for name, gold in SYNTH_GOLD.items():
        p = corpus / name
        if not p.exists():
            synth.append({"file": name, "error": "missing"})
            continue
        synth.append(run_file(p, gold, y_tol))

    real_dir = Path(
        "/home/gucampe/.cursor/projects/home-gucampe-Documentos-Projetos-sistema-financeiro/attachments/7a73b6ec-e9bc-4346-a398-ec4fcb74a361"
    )
    reals_spec = [
        ("santander", real_dir / "ComprovanteSantander-1787356973725.pdf"),
        ("bradesco", real_dir / "7ef1985f-09c4-4437-b40d-c369f62b9faa.pdf"),
        ("nubank", real_dir / "extrato_nubank.pdf"),
        ("caixa", real_dir / "extrato_caixa.pdf"),
        ("comprovante_2p", real_dir / "comprovante2026-08-21_233033.pdf"),
        ("nubank_jul", real_dir / "NU_7375439292_01JUL2025_31JUL2025.pdf"),
    ]
    reals = []
    for label, p in reals_spec:
        if not p.exists():
            reals.append({"file": label, "error": "missing"})
            continue
        r = run_file(p, None, y_tol)
        r["label"] = label
        reals.append(r)

    out = {"y_tol": y_tol, "synthetic": synth, "real": reals}
    out_path = corpus / "assertiveness.json"
    # strip nothing else — already no raw cands
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"wrote {out_path}")
    print("\n=== SINTÉTICOS (F1 identidade data+valor / +tipo / +desc) ===")
    print(
        f"{'arquivo':36} {'mu':>4} {'pl':>4} "
        f"{'id mu':>6} {'id pl':>6} {'tp mu':>6} {'tp pl':>6} {'dsc mu':>6} {'dsc pl':>6} {'jacc':>5}"
    )
    for r in synth:
        mu = r.get("pymupdf") or {}
        pl = r.get("pdfplumber") or {}
        ag = r.get("agreement") or {}

        def f1(b, k):
            s = b.get(k) or {}
            return s.get("f1", "err")

        print(
            f"{r.get('file','?'):36} {mu.get('n_pred', mu.get('error'))!s:>4} "
            f"{pl.get('n_pred', pl.get('error'))!s:>4} "
            f"{f1(mu,'identity')!s:>6} {f1(pl,'identity')!s:>6} "
            f"{f1(mu,'with_tipo')!s:>6} {f1(pl,'with_tipo')!s:>6} "
            f"{f1(mu,'with_desc')!s:>6} {f1(pl,'with_desc')!s:>6} "
            f"{ag.get('jaccard',''):>5}"
        )
    print("\n=== REAIS (sem gabarito; acordo entre libs; sem PII) ===")
    for r in reals:
        mu = r.get("pymupdf") or {}
        pl = r.get("pdfplumber") or {}
        ag = r.get("agreement") or {}
        print(
            f"{r.get('label', r.get('file')):12} words mu={mu.get('n_words')} pl={pl.get('n_words')}  "
            f"cands mu={mu.get('n_pred', mu.get('error'))} pl={pl.get('n_pred', pl.get('error'))}  "
            f"jacc={ag.get('jaccard')} only_mu={ag.get('n_only_a')} only_pl={ag.get('n_only_b')}"
        )


if __name__ == "__main__":
    main()
