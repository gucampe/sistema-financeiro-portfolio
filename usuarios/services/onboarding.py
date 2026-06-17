"""Inferência de progresso da Central de Primeiros Passos — sem persistência em banco."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from django.conf import settings
from django.core.cache import cache

from cartoes.models import Cartao
from contas.models import Conta
from transacoes.models import Transacao
from usuarios.models import Usuario

ONBOARDING_CACHE_TTL = 0 if settings.DEBUG else 60


def usuario_tem_conta_ativa(user: Usuario) -> bool:
    return Conta.objects.filter(usuario=user, ativa=True).exists()


def usuario_tem_movimentacao(user: Usuario) -> bool:
    """Receita/despesa apenas — ajuste de saldo inicial não conta."""
    return Transacao.objects.filter(usuario=user, tipo__in=["receita", "despesa"]).exists()


def usuario_tem_cartao_ativo(user: Usuario) -> bool:
    return Cartao.objects.filter(usuario=user, ativa=True).exists()


@dataclass(frozen=True)
class EtapaOnboarding:
    id: str
    titulo: str
    descricao: str
    icone: str
    obrigatoria: bool
    cta_label: str
    cta_acao: str
    verificar: Callable[[Usuario], bool]


ETAPAS_REGISTRY: tuple[EtapaOnboarding, ...] = (
    EtapaOnboarding(
        id="conta",
        titulo="Conta financeira",
        descricao="Cadastre onde seu dinheiro fica.",
        icone="fa-solid fa-building-columns",
        obrigatoria=True,
        cta_label="Adicionar conta",
        cta_acao="link_conta",
        verificar=usuario_tem_conta_ativa,
    ),
    EtapaOnboarding(
        id="movimentacao",
        titulo="Primeira movimentação",
        descricao="Registre manualmente ou importe via OFX ou planilha.",
        icone="fa-solid fa-arrow-right-arrow-left",
        obrigatoria=True,
        cta_label="Ir para transações",
        cta_acao="link_transacoes",
        verificar=usuario_tem_movimentacao,
    ),
    EtapaOnboarding(
        id="cartao",
        titulo="Cartão de crédito",
        descricao="Controle gastos do seu cartão.",
        icone="fa-solid fa-credit-card",
        obrigatoria=False,
        cta_label="Configurar cartão",
        cta_acao="link_cartao",
        verificar=usuario_tem_cartao_ativo,
    ),
)


def _etapa_para_dict(etapa: EtapaOnboarding, *, concluida: bool) -> dict[str, Any]:
    return {
        "id": etapa.id,
        "titulo": etapa.titulo,
        "descricao": etapa.descricao,
        "icone": etapa.icone,
        "obrigatoria": etapa.obrigatoria,
        "cta_label": etapa.cta_label,
        "cta_acao": etapa.cta_acao,
        "concluida": concluida,
    }


def progresso_primeiros_passos(user: Usuario) -> dict[str, Any]:
    """Retorna estado do checklist inferido dos dados existentes."""
    cache_key = f"onboarding:progress:{user.pk}"
    if ONBOARDING_CACHE_TTL > 0:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    etapas: list[dict[str, Any]] = []
    concluidas = 0

    for etapa in ETAPAS_REGISTRY:
        concluida = etapa.verificar(user)
        if concluida:
            concluidas += 1
        etapas.append(_etapa_para_dict(etapa, concluida=concluida))

    total = len(ETAPAS_REGISTRY)
    percentual = round((concluidas / total) * 100) if total else 100

    essencial_ids = ("conta", "movimentacao")
    essencial_completo = all(
        next(e for e in etapas if e["id"] == etapa_id)["concluida"]
        for etapa_id in essencial_ids
    )

    resultado = {
        "etapas": etapas,
        "concluidas": concluidas,
        "total": total,
        "percentual": percentual,
        "essencial_completo": essencial_completo,
        "total_completo": concluidas >= total,
    }
    if ONBOARDING_CACHE_TTL > 0:
        cache.set(cache_key, resultado, ONBOARDING_CACHE_TTL)
    return resultado
