"""Catálogo estático da Ajuda — sem CMS.

Checkpoint pós Fases 0–1: ⓘ e empty states explicam o conceito no lugar,
mas o mapa mental, o caminho para colocar dados e o modelo do cartão
ainda justificam os 3 artigos MVP. “Corrigir categoria” fica só como
âncora (não entra no catálogo). Sidebar Relatórios permanece.
"""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ArtigoAjuda:
    id: str
    titulo: str
    grupo: str  # comece | entenda
    tipo: str  # faca_comigo | entenda
    tags: tuple[str, ...]
    resumo: str
    template: str
    cta_label: str = ""
    cta_acao: str = ""


ARTIGOS: tuple[ArtigoAjuda, ...] = (
    ArtigoAjuda(
        id="mapa",
        titulo="Como o GranaGo organiza seu dinheiro",
        grupo="comece",
        tipo="entenda",
        tags=("conta", "transação", "categoria", "cartão", "orçamento", "relatório", "mapa"),
        resumo="Contas, transações, categorias, cartões, orçamentos e relatórios — o mapa em uma tela.",
        template="usuarios/ajuda/artigos/mapa.html",
        cta_label="Ver minha visão geral",
        cta_acao="relatorios_home",
    ),
    ArtigoAjuda(
        id="adicionar-dados",
        titulo="Como adicionar seus dados",
        grupo="comece",
        tipo="faca_comigo",
        tags=("lançar", "transação", "importar", "extrato", "ofx", "planilha"),
        resumo="Lance na mão ou importe o extrato. O OFX é um dos formatos, não o único caminho.",
        template="usuarios/ajuda/artigos/adicionar_dados.html",
        cta_label="Adicionar transação",
        cta_acao="transacoes",
    ),
    ArtigoAjuda(
        id="cartao",
        titulo="Como funciona o cartão",
        grupo="entenda",
        tipo="entenda",
        tags=("cartão", "fatura", "crédito", "pagamento"),
        resumo="A compra vai para a fatura. O dinheiro sai da conta quando você paga.",
        template="usuarios/ajuda/artigos/cartao.html",
        cta_label="Entendi",
        cta_acao="fechar",
    ),
)


def artigo_por_id(artigo_id: str) -> ArtigoAjuda | None:
    for artigo in ARTIGOS:
        if artigo.id == artigo_id:
            return artigo
    return None


def artigos_por_grupo() -> dict[str, tuple[ArtigoAjuda, ...]]:
    return {
        "comece_aqui": tuple(a for a in ARTIGOS if a.grupo == "comece"),
        "entenda": tuple(a for a in ARTIGOS if a.grupo == "entenda"),
    }


def catalogo_ajuda_json() -> str:
    return json.dumps(
        [
            {
                "id": a.id,
                "titulo": a.titulo,
                "resumo": a.resumo,
                "tags": list(a.tags),
            }
            for a in ARTIGOS
        ],
        ensure_ascii=False,
    )


def artigos_para_template() -> list[dict]:
    return [
        {
            "id": a.id,
            "titulo": a.titulo,
            "grupo": a.grupo,
            "tipo": a.tipo,
            "tags": " ".join(a.tags),
            "resumo": a.resumo,
            "cta_label": a.cta_label,
            "cta_acao": a.cta_acao,
        }
        for a in ARTIGOS
    ]
