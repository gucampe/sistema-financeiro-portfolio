from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from django.contrib.auth import get_user_model

from categorias.models import Categoria
from categorizacao.models import RegraCategorizacao
from categorizacao.services.learning import processar_feedback_transacao
from categorizacao.services.normalizer import normalizar_padrao_regra
from contas.models import Conta
from transacoes.models import Transacao

User = get_user_model()

PERSONA_PREFIX = "avaliacao-cb"


@dataclass
class PersonaSpec:
    code: str
    nome: str
    email_suffix: str
    historico_transacoes: int = 0
    regras: list[tuple[str, str, str]] = field(default_factory=list)
    auto_aplicar: bool = False
    limiar_auto: float = 0.90


PERSONAS: list[PersonaSpec] = [
    PersonaSpec("CB-01", "Iniciante", "cb01", historico_transacoes=0),
    PersonaSpec("CB-02", "Historico Parcial", "cb02", historico_transacoes=30),
    PersonaSpec("CB-03", "Historico Consolidado", "cb03", historico_transacoes=80),
    PersonaSpec(
        "CB-04",
        "Categorias Custom",
        "cb04",
        historico_transacoes=5,
    ),
    PersonaSpec("CB-05", "Desorganizado", "cb05", historico_transacoes=20),
    PersonaSpec(
        "CB-06",
        "Avancado",
        "cb06",
        historico_transacoes=40,
        regras=[
            ("contains", "ifood", "Alimentação"),
            ("contains", "uber", "Transporte e locomoção"),
            ("merchant_exact", "netflix", "Serviços e Assinaturas"),
            ("contains", "pix maria", "Família"),
            ("contains", "droga", "Saúde"),
        ],
        auto_aplicar=True,
        limiar_auto=0.90,
    ),
    PersonaSpec("CB-07", "Corretor Compulsivo", "cb07", historico_transacoes=25),
    PersonaSpec("CB-08", "Ignorador", "cb08", historico_transacoes=15),
]

HISTORICO_SAMPLES = [
    ("UBER TRIP SP", "Transporte e locomoção", "despesa"),
    ("IFOOD RESTAURANTE", "Alimentação", "despesa"),
    ("NETFLIX COM", "Serviços e Assinaturas", "despesa"),
    ("CARREFOUR COMPRA", "Supermercado", "despesa"),
    ("DROGASIL FARMACIA", "Saúde", "despesa"),
    ("SPOTIFY PREMIUM", "Serviços e Assinaturas", "despesa"),
    ("SHELL POSTO", "Transporte e locomoção", "despesa"),
    ("MCDONALDS", "Restaurantes e bares", "despesa"),
    ("AMAZON COMPRA", "Compras", "despesa"),
    ("SALARIO EMPRESA", "Salário", "receita"),
]


def ensure_personas() -> dict[str, User]:
    users: dict[str, User] = {}
    for spec in PERSONAS:
        email = f"{PERSONA_PREFIX}-{spec.email_suffix}@avaliacao.local"
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"nome": f"Avaliacao {spec.nome}", "ativo": True},
        )
        if created:
            user.set_password("avaliacao12345")
            user.save()
        perfil = user.perfil
        perfil.categorizacao_auto_aplicar = spec.auto_aplicar
        perfil.categorizacao_limiar_auto = spec.limiar_auto
        perfil.save(
            update_fields=["categorizacao_auto_aplicar", "categorizacao_limiar_auto"]
        )
        conta, _ = Conta.objects.get_or_create(
            usuario=user,
            nome="Conta Avaliacao",
            defaults={"tipo": "corrente"},
        )
        if spec.code == "CB-04":
            Categoria.objects.get_or_create(
                usuario=user,
                nome="Comida",
                tipo="despesa",
                defaults={"ativa": True},
            )
        _seed_historico(user, conta, spec.historico_transacoes)
        _seed_regras(user, spec.regras)
        users[spec.code] = user
    return users


def _categoria(user, nome: str, tipo: str = "despesa") -> Categoria | None:
    return Categoria.objects.filter(
        nome__iexact=nome,
        tipo=tipo,
    ).filter(
        models_q_usuario_padrao(user),
    ).first()


def models_q_usuario_padrao(user):
    from django.db.models import Q
    return Q(usuario=user) | Q(padrao=True)


def _seed_historico(user, conta: Conta, n: int) -> None:
    if n <= 0:
        return
    existentes = Transacao.objects.filter(usuario=user).count()
    if existentes >= n:
        return
    from datetime import date, timedelta

    base = date(2025, 1, 1)
    for i in range(existentes, n):
        desc, cat_nome, tipo = HISTORICO_SAMPLES[i % len(HISTORICO_SAMPLES)]
        cat = _categoria(user, cat_nome, tipo)
        if not cat:
            continue
        Transacao.objects.create(
            usuario=user,
            conta=conta,
            categoria=cat,
            tipo=tipo,
            valor=Decimal("25.00"),
            data=base + timedelta(days=i % 90),
            descricao=f"{desc} #{i}",
        )


def _seed_regras(user, regras: list[tuple[str, str, str]]) -> None:
    for tipo_regra, padrao, cat_nome in regras:
        cat = _categoria(user, cat_nome)
        if not cat:
            continue
        padrao_norm = normalizar_padrao_regra(padrao)
        RegraCategorizacao.objects.get_or_create(
            usuario=user,
            padrao_normalizado=padrao_norm,
            tipo_regra=tipo_regra,
            defaults={
                "padrao": padrao,
                "categoria": cat,
                "prioridade": 100,
                "confianca_base": 0.95,
                "origem": "manual",
                "ativa": True,
            },
        )


def simular_aprendizado_cb07(user: User, conta: Conta) -> None:
    """CB-07: corrige mesma descrição 2x para gerar regra aprendida."""
    cat_errada = _categoria(user, "Diversos")
    cat_certa = _categoria(user, "Transporte e locomoção")
    if not cat_errada or not cat_certa:
        return
    desc = "UBER VIAGEM TRABALHO"
    for _ in range(2):
        tx = Transacao.objects.create(
            usuario=user,
            conta=conta,
            categoria=cat_certa,
            tipo="despesa",
            valor=Decimal("30.00"),
            data="2026-01-10",
            descricao=desc,
        )
        processar_feedback_transacao(
            usuario=user,
            transacao=tx,
            descricao=desc,
            categoria_final=cat_certa,
            categoria_sugerida_id=cat_errada.pk,
            confianca=0.75,
            fonte="fuzzy",
        )
