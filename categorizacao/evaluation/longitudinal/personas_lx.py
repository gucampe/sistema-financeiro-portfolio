from __future__ import annotations

from dataclasses import dataclass, field

from django.contrib.auth import get_user_model

from categorias.models import Categoria
from categorizacao.evaluation.longitudinal.constants import PERSONA_PREFIX
from contas.models import Conta

User = get_user_model()


@dataclass
class PersonaLXSpec:
    code: str
    nome: str
    email_suffix: str
    feedback_policy: str
    txs_por_semana: int = 18
    perfil: str = ""
    pix_ratio: float = 0.0
    local_ratio: float = 0.0
    digital_ratio: float = 0.3
    auto_aplicar: bool = False


PERSONAS_LX: list[PersonaLXSpec] = [
    PersonaLXSpec("LX-01", "Digital", "lx01", "aceitar_sugestao", 15, "iFood/Uber/Netflix", digital_ratio=0.7),
    PersonaLXSpec("LX-02", "Muitos PIX", "lx02", "corrigir_para_gold", 20, "PIX pessoais", pix_ratio=0.45),
    PersonaLXSpec("LX-03", "CLT", "lx03", "aceitar_sugestao", 16, "Salario + contas fixas"),
    PersonaLXSpec("LX-04", "Autonomo", "lx04", "corrigir_para_gold", 22, "Receitas variadas", pix_ratio=0.25, local_ratio=0.2),
    PersonaLXSpec("LX-05", "Desorganizado", "lx05", "aceitar_tudo", 18, "Aceita tudo incl. erros"),
    PersonaLXSpec("LX-06", "Recorrente", "lx06", "aceitar_sugestao", 20, "10 merchants fixos", digital_ratio=0.5),
    PersonaLXSpec("LX-07", "Locais", "lx07", "corrigir_para_gold", 18, "15 merchants M3", local_ratio=0.55),
    PersonaLXSpec("LX-08", "Corretor", "lx08", "corrigir_para_gold", 20, "Corrige 80% erros"),
    PersonaLXSpec("LX-09", "Ignorador", "lx09", "ignorar", 16, "Sempre Diversos"),
    PersonaLXSpec("LX-10", "Subjetivo", "lx10", "corrigir_para_gold", 17, "Amazon→Compras", digital_ratio=0.4),
    PersonaLXSpec("LX-11", "Mutavel", "lx11", "aceitar_sugestao", 18, "UBER variantes"),
    PersonaLXSpec("LX-12", "Sazonal", "lx12", "aceitar_sugestao", 19, "Picos viagem Dez"),
    PersonaLXSpec("LX-CTRL-0", "Controle Zero", "lxctrl0", "ignorar", 15, "Nunca feedback"),
    PersonaLXSpec("LX-CTRL-ML", "Controle ML", "lxctrlml", "aceitar_sugestao", 25, "Volume sem correcao"),
    PersonaLXSpec("LX-CTRL-CORR", "Controle Corretor", "lxctrlcorr", "corrigir_para_gold", 22, "Max correcoes"),
]

PERSONAS_BY_CODE = {p.code: p for p in PERSONAS_LX}


def ensure_personas_lx(codes: list[str] | None = None) -> dict[str, User]:
    codes = codes or [p.code for p in PERSONAS_LX]
    users: dict[str, User] = {}
    for spec in PERSONAS_LX:
        if spec.code not in codes:
            continue
        email = f"{PERSONA_PREFIX}-{spec.email_suffix}@avaliacao.local"
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"nome": f"Longitudinal {spec.nome}", "ativo": True},
        )
        if created:
            user.set_password("avaliacao12345")
            user.save()
        perfil = user.perfil
        perfil.categorizacao_auto_aplicar = spec.auto_aplicar
        perfil.save(update_fields=["categorizacao_auto_aplicar"])
        Conta.objects.get_or_create(
            usuario=user,
            nome="Conta Longitudinal",
            defaults={"tipo": "corrente"},
        )
        if spec.code == "LX-10":
            Categoria.objects.get_or_create(
                usuario=user,
                nome="Comida",
                tipo="despesa",
                defaults={"ativa": True},
            )
        users[spec.code] = user
    return users


def reset_persona_state(user: User) -> None:
    """Limpa histórico de aprendizado para replay T0."""
    from categorizacao.models import (
        EventoCategorizacao,
        MemoriaMerchantUsuario,
        ModeloClassificacaoUsuario,
        RegraCategorizacao,
    )
    from transacoes.models import Transacao

    Transacao.objects.filter(usuario=user).delete()
    EventoCategorizacao.objects.filter(usuario=user).delete()
    MemoriaMerchantUsuario.objects.filter(usuario=user).delete()
    RegraCategorizacao.objects.filter(usuario=user).delete()
    ModeloClassificacaoUsuario.objects.filter(usuario=user).delete()
