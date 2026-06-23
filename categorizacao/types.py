from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from categorias.models import Categoria
    from usuarios.models import Usuario


@dataclass(frozen=True)
class ContextoCategorizacao:
    usuario: Usuario
    descricao: str
    tipo: str
    valor: Decimal | None = None
    descricao_normalizada: str = ""
    merchant_key: str = ""


@dataclass(frozen=True)
class PredicaoCategorizacao:
    categoria_id: int
    categoria_nome: str
    confianca: float
    fonte: str
    merchant_key: str | None
    explicacao: str
    contexto: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SugestaoCategorizacao:
    categoria_id: int
    categoria_nome: str
    confianca: float
    fonte: str
    merchant_key: str | None
    explicacao: str
    auto_aplicar: bool
    contexto: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        from django.conf import settings

        payload = {
            "categoria_id": self.categoria_id,
            "categoria_nome": self.categoria_nome,
            "confianca": round(self.confianca, 4),
            "fonte": self.fonte,
            "merchant_key": self.merchant_key,
            "explicacao": self.explicacao,
            "auto_aplicar": self.auto_aplicar,
        }
        if self.contexto:
            payload["contexto"] = self.contexto
        if self.fonte == "llm_gemini":
            payload["mostrar_badge_ia"] = bool(
                getattr(settings, "CATEGORIZACAO_LLM_MOSTRAR_BADGE", True)
            )
        return payload


@dataclass
class PreferenciasCategorizacao:
    auto_aplicar: bool = False
    limiar_auto: float = 0.90
    contribuir_globais: bool = False

    @classmethod
    def from_usuario(cls, usuario: Usuario) -> PreferenciasCategorizacao:
        perfil = getattr(usuario, "perfil", None)
        if perfil is None:
            return cls()
        return cls(
            auto_aplicar=bool(getattr(perfil, "categorizacao_auto_aplicar", False)),
            limiar_auto=float(getattr(perfil, "categorizacao_limiar_auto", 0.90) or 0.90),
            contribuir_globais=bool(
                getattr(perfil, "categorizacao_contribuir_globais", False)
            ),
        )


LIMIARES_FONTE = {
    "regra_usuario": {"auto": 0.95, "preencher": 0.80, "hint": 0.60},
    "regra_global": {"auto": 0.90, "preencher": 0.75, "hint": 0.55},
    "fuzzy": {"auto": 0.88, "preencher": 0.70, "hint": 0.50},
    "historico": {"auto": 0.85, "preencher": 0.65, "hint": 0.0},
    "ml": {"auto": 0.75, "preencher": 0.60, "hint": 0.0},
    "pg_trgm": {"auto": 0.82, "preencher": 0.68, "hint": 0.0},
    "llm_gemini": {"auto": 0.85, "preencher": 0.60, "hint": 0.45},
}


def predicao_para_sugestao(
    predicao: PredicaoCategorizacao,
    prefs: PreferenciasCategorizacao,
) -> SugestaoCategorizacao:
    limiares = LIMIARES_FONTE.get(predicao.fonte, LIMIARES_FONTE["fuzzy"])
    limiar_auto = prefs.limiar_auto if prefs.auto_aplicar else limiares["auto"]
    auto_aplicar = prefs.auto_aplicar and predicao.confianca >= limiar_auto
    if predicao.fonte == "llm_gemini":
        auto_aplicar = False
    return SugestaoCategorizacao(
        categoria_id=predicao.categoria_id,
        categoria_nome=predicao.categoria_nome,
        confianca=predicao.confianca,
        fonte=predicao.fonte,
        merchant_key=predicao.merchant_key,
        explicacao=predicao.explicacao,
        auto_aplicar=auto_aplicar,
        contexto=dict(predicao.contexto),
    )
