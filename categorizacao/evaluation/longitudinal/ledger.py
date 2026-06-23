from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from categorizacao.evaluation.datasets import GoldenCase
from categorizacao.evaluation.longitudinal.constants import LEDGER_HEADER, LONGITUDINAL_DIR
from categorizacao.evaluation.longitudinal.personas_lx import PERSONAS_BY_CODE, PersonaLXSpec
from transacoes.tests.helpers.import_fixtures import build_ofx_bytes


@dataclass
class LedgerRow:
    tx_id: str
    persona: str
    semana_simulada: int
    data: str
    descricao: str
    tipo: str
    valor: str
    categoria_gold: str
    bucket: str
    merchant_mutacao: str
    eh_reimport: bool
    notas: str = ""

    def to_golden(self) -> GoldenCase:
        return GoldenCase(
            id=self.tx_id,
            descricao=self.descricao,
            tipo=self.tipo,
            valor=self.valor,
            categoria_esperada=self.categoria_gold,
            categorias_aceitaveis=self.categoria_gold,
            bucket=self.bucket,
            banco_origem="ledger_longitudinal",
            notas_avaliador=self.notas,
        )


DIGITAL = [
    ("IFOOD RESTAURANTE", "Alimentação", "M1"),
    ("UBER TRIP", "Transporte e locomoção", "M1"),
    ("NETFLIX COM", "Serviços e Assinaturas", "M1"),
    ("SPOTIFY PREMIUM", "Serviços e Assinaturas", "M1"),
    ("DROGASIL", "Saúde", "M1"),
    ("CARREFOUR", "Supermercado", "M1"),
    ("MCDONALDS", "Restaurantes e bares", "M1"),
    ("SHELL POSTO", "Transporte e locomoção", "M1"),
]

PIX_PATTERNS = [
    ("PIX ENVIADO MARIA SILVA", "Família"),
    ("PIX ENVIADO JOAO SILVA", "Outros"),
    ("PIX ANA SILVA", "Família"),
    ("PIX TRANSF PEDRO", "Outros"),
]

LOCALS = [
    ("PADARIA SAO JOSE", "Alimentação"),
    ("LANCHONETE CENTRAL", "Alimentação"),
    ("AUTO PECAS MARANHAO", "Transporte e locomoção"),
    ("BARBEARIA DO ZE", "Cuidados pessoais"),
    ("MERCADINHO DA VILA", "Supermercado"),
    ("OFICINA MECANICA SILVA", "Transporte e locomoção"),
    ("PET SHOP AMIGO", "Pets"),
    ("ACADEMIA FORCA", "Esportes"),
    ("LOJA ROUPAS BETA", "Compras"),
    ("RESTAURANTE SABOR", "Restaurantes e bares"),
    ("FARMACIA POPULAR", "Saúde"),
    ("PAPELARIA CENTRO", "Compras"),
    ("SALAO BELEZA", "Cuidados pessoais"),
    ("GAS E AGUA", "Moradia"),
    ("CONDOMINIO ED", "Moradia"),
]

MUTABLE_UBER = [
    (1, 3, "UBER TRIP"),
    (4, 6, "UBER*TRIP"),
    (7, 9, "UBER TRIP SAO PAULO BR"),
    (10, 12, "UBER DO BRASIL"),
]

SUBJETIVOS = [
    ("AMAZON BR", "Compras"),
    ("MERCADO LIVRE", "Compras"),
    ("MAGAZINE LUIZA", "Compras"),
    ("SHOPEE BR", "Compras"),
]

CLT = [
    ("SALARIO EMPRESA XYZ", "Salário", "receita"),
    ("ENEL SP", "Moradia", "despesa"),
    ("CLARO MOVEL", "Serviços e Assinaturas", "despesa"),
    ("ALUGUEL IMOB", "Moradia", "despesa"),
]

SAZONAL = [
    ("LATAM AIR", "Viagens", "despesa"),
    ("BOOKING COM", "Viagens", "despesa"),
    ("HOTEL IBIS", "Viagens", "despesa"),
]


def _seed_persona(persona: str) -> int:
    return int(hashlib.md5(persona.encode()).hexdigest()[:8], 16)


def _pick(pool: list, week: int, i: int, persona: str):
    s = _seed_persona(persona)
    return pool[(s + week * 17 + i) % len(pool)]


def _descricao_uber(semana: int) -> str:
    for wmin, wmax, desc in MUTABLE_UBER:
        if wmin <= semana <= wmax:
            return desc
    return "UBER TRIP"


def _gerar_semana(spec: PersonaLXSpec, semana: int, start_id: int) -> list[LedgerRow]:
    rows: list[LedgerRow] = []
    base_date = date(2025, 1, 6) + timedelta(weeks=semana - 1)
    n = spec.txs_por_semana

    for i in range(n):
        r = _seed_persona(spec.code) + semana * 100 + i
        tipo = "despesa"
        valor = f"-{(20 + (r % 80))}.00"
        desc = ""
        cat = "Diversos"
        bucket = "M1"
        mut = "none"

        roll = (r % 100) / 100.0
        if spec.code == "LX-11":
            desc = _descricao_uber(semana)
            cat = "Transporte e locomoção"
            bucket = "MUT"
            mut = "typo" if semana >= 4 else "none"
        elif spec.code == "LX-12" and semana >= 10:
            item = _pick(SAZONAL, semana, i, spec.code)
            desc, cat, tipo = item[0], item[1], item[2]
            bucket = "M1"
        elif spec.code == "LX-03" and i % 4 == 0:
            item = _pick(CLT, semana, i, spec.code)
            desc, cat, tipo = item[0], item[1], item[2]
            bucket = "R3" if tipo == "receita" else "M1"
        elif roll < spec.pix_ratio:
            item = _pick(PIX_PATTERNS, semana, i, spec.code)
            desc, cat = item[0], item[1]
            bucket = "R2"
            if semana in (3, 7) and "MARIA" in desc:
                desc = "PIX MARIA S"
                mut = "pix_variante"
        elif roll < spec.pix_ratio + spec.local_ratio:
            item = _pick(LOCALS, semana, i, spec.code)
            desc, cat = item[0], item[1]
            bucket = "M3"
        elif roll < spec.pix_ratio + spec.local_ratio + 0.15 and spec.code == "LX-10":
            item = _pick(SUBJETIVOS, semana, i, spec.code)
            desc, cat = item[0], item[1]
            bucket = "C1"
        elif roll < spec.pix_ratio + spec.local_ratio + spec.digital_ratio + 0.15:
            item = _pick(DIGITAL, semana, i, spec.code)
            desc, cat, bucket = item[0], item[1], item[2]
        else:
            item = _pick(DIGITAL + [(d[0], d[1], "M1") for d in LOCALS[:5]], semana, i, spec.code)
            if len(item) == 3:
                desc, cat, bucket = item[0], item[1], item[2]
            else:
                desc, cat = item[0], item[1]

        if semana >= 8 and r % 5 == 0:
            desc = f"DEBITO COMPRA CARTAO {desc} SAO PAULO BR"
            mut = "prefixo_banco"
            bucket = "R1"

        tx_date = (base_date + timedelta(days=i % 7)).isoformat()
        rows.append(
            LedgerRow(
                tx_id=f"{spec.code}-w{semana:02d}-{start_id + i:04d}",
                persona=spec.code,
                semana_simulada=semana,
                data=tx_date,
                descricao=desc,
                tipo=tipo,
                valor=valor if tipo == "despesa" else valor.replace("-", ""),
                categoria_gold=cat,
                bucket=bucket,
                merchant_mutacao=mut,
                eh_reimport=False,
                notas=spec.feedback_policy,
            )
        )
    return rows


def generate_reimport_ledger() -> list[LedgerRow]:
    """Lote fixo 60 tx: 15 M3, 15 R2, 10 MUT, 10 C1, 10 M1."""
    rows: list[LedgerRow] = []
    idx = 0
    for desc, cat in LOCALS[:15]:
        rows.append(
            LedgerRow(
                f"REIMP-{idx:03d}", "ALL", 0, "2025-06-01",
                desc, "despesa", "-40.00", cat, "M3", "none", True,
            )
        )
        idx += 1
    for desc, cat in (PIX_PATTERNS * 4)[:15]:
        rows.append(
            LedgerRow(
                f"REIMP-{idx:03d}", "ALL", 0, "2025-06-01",
                desc, "despesa", "-60.00", cat, "R2", "none", True,
            )
        )
        idx += 1
    for desc, cat, _ in [
        ("UBER TRIP", "Transporte e locomoção", "MUT"),
        ("UBER*TRIP", "Transporte e locomoção", "MUT"),
        ("UBER DO BRASIL", "Transporte e locomoção", "MUT"),
        ("IFOOD RESTAURANTE", "Alimentação", "MUT"),
        ("IFOOD*REST", "Alimentação", "MUT"),
        ("NETFLIX COM", "Serviços e Assinaturas", "MUT"),
        ("SPOTIFY", "Serviços e Assinaturas", "MUT"),
        ("UBER TRIP SP BR", "Transporte e locomoção", "MUT"),
        ("UBER EATS", "Alimentação", "MUT"),
        ("RAPPI BR", "Alimentação", "MUT"),
    ]:
        rows.append(
            LedgerRow(
                f"REIMP-{idx:03d}", "ALL", 0, "2025-06-01",
                desc, "despesa", "-35.00", cat, "MUT", "typo", True,
            )
        )
        idx += 1
    for desc, cat in SUBJETIVOS * 2 + SUBJETIVOS[:2]:
        rows.append(
            LedgerRow(
                f"REIMP-{idx:03d}", "ALL", 0, "2025-06-01",
                desc, "despesa", "-90.00", cat, "C1", "none", True,
            )
        )
        idx += 1
    for desc, cat, bucket in (DIGITAL * 2)[:10]:
        rows.append(
            LedgerRow(
                f"REIMP-{idx:03d}", "ALL", 0, "2025-06-01",
                desc, "despesa", "-50.00", cat, bucket, "none", True,
            )
        )
        idx += 1
    return rows[:60]


def generate_persona_ledger(spec: PersonaLXSpec, weeks: int = 12) -> list[LedgerRow]:
    rows: list[LedgerRow] = []
    tx_id = 0
    for semana in range(1, weeks + 1):
        sem_rows = _gerar_semana(spec, semana, tx_id)
        rows.extend(sem_rows)
        tx_id += len(sem_rows)
    return rows


def write_ledger_csv(rows: list[LedgerRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(LEDGER_HEADER)
        for r in rows:
            writer.writerow(
                [
                    r.tx_id,
                    r.persona,
                    r.semana_simulada,
                    r.data,
                    r.descricao,
                    r.tipo,
                    r.valor,
                    r.categoria_gold,
                    r.bucket,
                    r.merchant_mutacao,
                    "true" if r.eh_reimport else "false",
                    r.notas,
                ]
            )


def load_ledger_csv(path: Path) -> list[LedgerRow]:
    rows: list[LedgerRow] = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(
                LedgerRow(
                    tx_id=row["tx_id"],
                    persona=row["persona"],
                    semana_simulada=int(row["semana_simulada"]),
                    data=row["data"],
                    descricao=row["descricao"],
                    tipo=row["tipo"],
                    valor=row["valor"],
                    categoria_gold=row["categoria_gold"],
                    bucket=row["bucket"],
                    merchant_mutacao=row["merchant_mutacao"],
                    eh_reimport=row["eh_reimport"].lower() == "true",
                    notas=row.get("notas", ""),
                )
            )
    return rows


def load_reimport_ledger() -> list[LedgerRow]:
    path = LONGITUDINAL_DIR / "lotes_reimport" / "lote_reimport_60.csv"
    if not path.exists():
        write_all_datasets(weeks=12)
    return load_ledger_csv(path)


def write_reimport_ofx(path: Path | None = None) -> Path:
    path = path or LONGITUDINAL_DIR / "lotes_reimport" / "lote_reimport_60.ofx"
    rows = generate_reimport_ledger()
    txs = [
        {
            "fitid": r.tx_id,
            "trnamt": r.valor,
            "name": r.descricao,
            "dtposted": r.data.replace("-", "") + "120000",
            "trntype": "CREDIT" if r.tipo == "receita" else "DEBIT",
        }
        for r in rows
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_ofx_bytes(txs))
    return path


def write_all_datasets(weeks: int = 12) -> dict[str, Path]:
    from categorizacao.evaluation.longitudinal.prova import write_prova_csv

    paths: dict[str, Path] = {}
    ledger_dir = LONGITUDINAL_DIR / "ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)

    reimport = generate_reimport_ledger()
    reimport_path = LONGITUDINAL_DIR / "lotes_reimport" / "lote_reimport_60.csv"
    write_ledger_csv(reimport, reimport_path)
    paths["reimport"] = reimport_path
    paths["reimport_ofx"] = write_reimport_ofx()

    for spec in PERSONAS_BY_CODE.values():
        rows = generate_persona_ledger(spec, weeks=weeks)
        p = ledger_dir / f"{spec.code.lower()}_ledger.csv"
        write_ledger_csv(rows, p)
        paths[spec.code] = p

    paths["prova"] = write_prova_csv()
    return paths
