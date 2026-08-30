"""Catálogo da Ajuda in-app.

O conteúdo fica versionado no código para o time de produto editar
junto do frontend, sem depender de um CMS nesta fase.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal


TipoArtigo = Literal["entenda", "faca_comigo"]
GrupoArtigo = Literal["comece", "organize", "entenda"]


@dataclass(frozen=True)
class ArtigoAjuda:
    id: str
    titulo: str
    resumo: str
    tags: tuple[str, ...]
    tipo: TipoArtigo
    grupo: GrupoArtigo
    template: str
    mostra_resumo_no_card: bool = True
    destinos: tuple[str, ...] = field(default_factory=tuple)
    relacionados: tuple[str, ...] = field(default_factory=tuple)

    def artigos_relacionados(self) -> tuple["ArtigoAjuda", ...]:
        encontrados: list[ArtigoAjuda] = []
        for rid in self.relacionados:
            if rid == self.id:
                continue
            artigo = artigo_por_id(rid)
            if artigo is not None:
                encontrados.append(artigo)
        return tuple(encontrados)


ARTIGOS: tuple[ArtigoAjuda, ...] = (
    ArtigoAjuda(
        id="mapa",
        titulo="Como o GranaGo organiza seu dinheiro",
        resumo="Contas, transações, categorias, cartões, orçamentos e relatórios — o mapa em uma tela.",
        tags=(
            "conta",
            "contas",
            "transação",
            "transações",
            "categoria",
            "categorias",
            "cartão",
            "cartões",
            "orçamento",
            "orçamentos",
            "relatório",
            "relatórios",
            "mapa",
            "patrimônio",
            "patrimonio",
        ),
        tipo="entenda",
        grupo="comece",
        template="usuarios/ajuda/artigos/mapa.html",
        destinos=("relatorios:home",),
        relacionados=("transacao", "cartao"),
    ),
    ArtigoAjuda(
        id="adicionar-dados",
        titulo="Como adicionar seus dados",
        resumo="Lance uma transação ou importe o extrato. Escolha o caminho mais simples para você.",
        tags=(
            "lançar",
            "lançamento",
            "transação",
            "transações",
            "adicionar",
            "importar",
            "importação",
            "extrato",
            "ofx",
            "planilha",
            "dados",
            "começar",
        ),
        tipo="faca_comigo",
        grupo="comece",
        template="usuarios/ajuda/artigos/adicionar_dados.html",
        destinos=("transacoes:historico",),
        relacionados=("transacao", "corrigir-categoria"),
    ),
    ArtigoAjuda(
        id="transacao",
        titulo="Como funciona uma transação",
        resumo="Receitas registram entradas, despesas registram gastos e transferências apenas movem dinheiro entre suas contas.",
        tags=(
            "transação",
            "transações",
            "receita",
            "receitas",
            "despesa",
            "despesas",
            "transferência",
            "transferências",
            "lançamento",
            "lançamentos",
            "movimentação",
            "movimentações",
            "entrada",
            "saída",
        ),
        tipo="entenda",
        grupo="comece",
        template="usuarios/ajuda/artigos/transacao.html",
        destinos=("transacoes:historico",),
        relacionados=("adicionar-dados", "transferencia", "resultado"),
    ),
    ArtigoAjuda(
        id="corrigir-categoria",
        titulo="Como corrigir uma categoria",
        resumo="Se uma movimentação estiver na categoria errada, você pode corrigir e manter o controle das suas informações.",
        tags=(
            "categoria",
            "categorias",
            "corrigir",
            "correção",
            "categorização",
            "categorizar",
            "classificação",
            "sugestão",
        ),
        tipo="faca_comigo",
        grupo="organize",
        template="usuarios/ajuda/artigos/corrigir_categoria.html",
        mostra_resumo_no_card=False,
        destinos=("transacoes:historico",),
        relacionados=("adicionar-dados", "transacao"),
    ),
    ArtigoAjuda(
        id="transferencia",
        titulo="Como funcionam as transferências",
        resumo="Transferências apenas movem dinheiro entre suas contas. Elas não são receitas nem despesas.",
        tags=(
            "transferência",
            "transferências",
            "transferir",
            "contas",
            "saldo",
            "receita",
            "despesa",
            "movimentação",
        ),
        tipo="entenda",
        grupo="organize",
        template="usuarios/ajuda/artigos/transferencia.html",
        mostra_resumo_no_card=False,
        relacionados=("transacao", "resultado"),
    ),
    ArtigoAjuda(
        id="cartao",
        titulo="Como funciona o cartão de crédito",
        resumo="A compra vai para a fatura. O dinheiro sai da conta quando você paga.",
        tags=(
            "cartão",
            "cartões",
            "crédito",
            "fatura",
            "pagamento",
            "compra",
            "compras",
        ),
        tipo="entenda",
        grupo="entenda",
        template="usuarios/ajuda/artigos/cartao.html",
        mostra_resumo_no_card=False,
        relacionados=("pagar-fatura", "mapa"),
    ),
    ArtigoAjuda(
        id="pagar-fatura",
        titulo="Como pagar a fatura",
        resumo="A compra fica na fatura. O pagamento registra a saída do dinheiro da conta padrão do cartão.",
        tags=(
            "fatura",
            "pagar",
            "pagamento",
            "cartão",
            "cartao",
            "cartão de crédito",
            "crédito",
            "credito",
            "conta",
            "pagamento da fatura",
        ),
        tipo="faca_comigo",
        grupo="entenda",
        template="usuarios/ajuda/artigos/pagar_fatura.html",
        mostra_resumo_no_card=False,
        destinos=("cartoes:home",),
        relacionados=("cartao",),
    ),
    ArtigoAjuda(
        id="resultado",
        titulo="Como funciona o resultado",
        resumo="O resultado mostra a diferença entre receitas e despesas no período selecionado. Ele não é o dinheiro disponível nas suas contas.",
        tags=(
            "resultado",
            "resultados",
            "saldo",
            "saldo do período",
            "receitas",
            "receita",
            "despesas",
            "despesa",
            "período",
            "periodo",
            "dinheiro",
            "patrimônio",
            "patrimonio",
        ),
        tipo="entenda",
        grupo="entenda",
        template="usuarios/ajuda/artigos/resultado.html",
        mostra_resumo_no_card=False,
        relacionados=("transacao", "transferencia"),
    ),
)


def artigo_por_id(artigo_id: str | None) -> ArtigoAjuda | None:
    if not artigo_id:
        return None
    return next((artigo for artigo in ARTIGOS if artigo.id == artigo_id), None)


def artigos_por_grupo() -> dict[str, list[ArtigoAjuda]]:
    grupos: dict[str, list[ArtigoAjuda]] = {
        "comece_aqui": [],
        "organize": [],
        "entenda": [],
    }
    chave = {"comece": "comece_aqui", "organize": "organize", "entenda": "entenda"}
    for artigo in ARTIGOS:
        grupos[chave[artigo.grupo]].append(artigo)
    return grupos


def catalogo_ajuda_json() -> str:
    return json.dumps(
        [
            {
                "id": a.id,
                "titulo": a.titulo,
                "resumo": a.resumo,
                "tags": list(a.tags),
                "grupo": a.grupo,
                "tipo": a.tipo,
            }
            for a in ARTIGOS
        ],
        ensure_ascii=False,
    )
