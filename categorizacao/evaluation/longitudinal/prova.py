from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from categorizacao.evaluation.datasets import GoldenCase
from categorizacao.evaluation.longitudinal.constants import LONGITUDINAL_DIR, PROVA_HEADER


@dataclass(frozen=True)
class ProvaCase:
    id: str
    descricao: str
    tipo: str
    valor: str
    categoria_esperada: str
    categorias_aceitaveis: str
    bucket: str
    grupo: str
    notas: str = ""

    def to_golden(self) -> GoldenCase:
        return GoldenCase(
            id=self.id,
            descricao=self.descricao,
            tipo=self.tipo,
            valor=self.valor,
            categoria_esperada=self.categoria_esperada,
            categorias_aceitaveis=self.categorias_aceitaveis or self.categoria_esperada,
            bucket=self.bucket,
            banco_origem="prova_longitudinal",
            notas_avaliador=self.notas,
        )


def all_prova_cases() -> list[ProvaCase]:
    cases: list[ProvaCase] = []

    pix = [
        ("PL-P01", "PIX ENVIADO MARIA SILVA", "Família"),
        ("PL-P02", "PIX MARIA S", "Família"),
        ("PL-P03", "PIX TRANSF MARIA SILVA", "Família"),
        ("PL-P04", "PIX ENVIADO JOAO SILVA", "Outros"),
        ("PL-P05", "PIX JOAO", "Outros"),
        ("PL-P06", "PIX ANA SILVA", "Família"),
        ("PL-P07", "PIX RECEBIDO MARIA", "Família"),
        ("PL-P08", "PIX ENVIADO PEDRO", "Outros"),
        ("PL-P09", "PIX TRANSFERENCIA ANA", "Família"),
    ]
    for cid, desc, cat in pix:
        cases.append(
            ProvaCase(cid, desc, "despesa", "-80.00", cat, cat, "R2", "PIX-LEARN")
        )

    locais = [
        ("PL-L01", "PADARIA SAO JOSE", "Alimentação"),
        ("PL-L02", "LANCHONETE CENTRAL", "Alimentação"),
        ("PL-L03", "AUTO PECAS MARANHAO", "Transporte e locomoção"),
        ("PL-L04", "BARBEARIA DO ZE", "Cuidados pessoais"),
        ("PL-L05", "MERCADINHO DA VILA", "Supermercado"),
        ("PL-L06", "OFICINA MECANICA SILVA", "Transporte e locomoção"),
        ("PL-L07", "PET SHOP AMIGO", "Pets"),
        ("PL-L08", "ACADEMIA FORCA", "Esportes"),
        ("PL-L09", "LOJA ROUPAS BETA", "Compras"),
    ]
    for cid, desc, cat in locais:
        cases.append(
            ProvaCase(cid, desc, "despesa", "-45.00", cat, cat, "M3", "LOCAL-LEARN")
        )

    mut = [
        ("PL-M01", "UBER TRIP", "Transporte e locomoção"),
        ("PL-M02", "UBER*TRIP", "Transporte e locomoção"),
        ("PL-M03", "UBER TRIP SAO PAULO BR", "Transporte e locomoção"),
        ("PL-M04", "UBER DO BRASIL", "Transporte e locomoção"),
        ("PL-M05", "IFOOD RESTAURANTE", "Alimentação"),
        ("PL-M06", "IFOOD*REST", "Alimentação"),
        ("PL-M07", "NETFLIX COM", "Serviços e Assinaturas"),
        ("PL-M08", "NETFLIX.COM BR", "Serviços e Assinaturas"),
        ("PL-M09", "SPOTIFY PREMIUM BR", "Serviços e Assinaturas"),
    ]
    for cid, desc, cat in mut:
        cases.append(
            ProvaCase(cid, desc, "despesa", "-35.00", cat, cat, "MUT", "MUT-LEARN")
        )

    c1 = [
        ("PL-C01", "AMAZON BR", "Compras"),
        ("PL-C02", "MERCADO LIVRE", "Compras"),
        ("PL-C03", "MAGAZINE LUIZA", "Compras"),
        ("PL-C04", "AMAZON MARKETPLACE", "Compras|Supermercado"),
        ("PL-C05", "SHOPEE BR", "Compras"),
        ("PL-C06", "AMERICANAS COM", "Compras"),
        ("PL-C07", "CASAS BAHIA", "Compras"),
        ("PL-C08", "ALIEXPRESS", "Compras"),
        ("PL-C09", "SHEIN BR", "Compras"),
    ]
    for cid, desc, cat in c1:
        esperada = cat.split("|")[0]
        cases.append(
            ProvaCase(cid, desc, "despesa", "-120.00", esperada, cat, "C1", "C1-LEARN")
        )

    ctrl = [
        ("PL-G01", "IFOOD RESTAURANTE", "Alimentação"),
        ("PL-G02", "UBER TRIP", "Transporte e locomoção"),
        ("PL-G03", "NETFLIX COM", "Serviços e Assinaturas"),
        ("PL-G04", "DROGASIL", "Saúde"),
        ("PL-G05", "CARREFOUR", "Supermercado"),
        ("PL-G06", "SPOTIFY", "Serviços e Assinaturas"),
        ("PL-G07", "MCDONALDS", "Restaurantes e bares"),
        ("PL-G08", "SHELL POSTO", "Transporte e locomoção"),
        ("PL-G09", "ENEL SP", "Moradia"),
    ]
    for cid, desc, cat in ctrl:
        cases.append(
            ProvaCase(cid, desc, "despesa", "-50.00", cat, cat, "M1", "GLOBAL-CTRL")
        )

    return cases


def write_prova_csv(path: Path | None = None) -> Path:
    path = path or LONGITUDINAL_DIR / "datasets" / "prova_aprendizado_v1.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(PROVA_HEADER)
        for c in all_prova_cases():
            writer.writerow(
                [
                    c.id,
                    c.descricao,
                    c.tipo,
                    c.valor,
                    c.categoria_esperada,
                    c.categorias_aceitaveis,
                    c.bucket,
                    c.grupo,
                    c.notas,
                ]
            )
    return path


def load_prova_csv(path: Path | None = None) -> list[ProvaCase]:
    path = path or LONGITUDINAL_DIR / "datasets" / "prova_aprendizado_v1.csv"
    if not path.exists():
        write_prova_csv(path)
    cases: list[ProvaCase] = []
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append(
                ProvaCase(
                    id=row["id"],
                    descricao=row["descricao"],
                    tipo=row["tipo"],
                    valor=row["valor"],
                    categoria_esperada=row["categoria_esperada"],
                    categorias_aceitaveis=row["categorias_aceitaveis"],
                    bucket=row["bucket"],
                    grupo=row["grupo"],
                    notas=row.get("notas", ""),
                )
            )
    return cases


def load_reimport_cases() -> list[GoldenCase]:
    from categorizacao.evaluation.longitudinal.ledger import load_reimport_ledger

    return [row.to_golden() for row in load_reimport_ledger()]


def prova_as_golden() -> list[GoldenCase]:
    return [c.to_golden() for c in all_prova_cases()]
