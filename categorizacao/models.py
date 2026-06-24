from __future__ import annotations

from django.conf import settings
from django.db import models

from categorias.models import Categoria


class MerchantGlobal(models.Model):
    TIPO_CHOICES = [
        ("receita", "Receita"),
        ("despesa", "Despesa"),
    ]

    canonical_name = models.CharField(max_length=120, unique=True, db_index=True)
    aliases = models.JSONField(default=list, blank=True)
    categoria_padrao_nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default="despesa")
    ativo = models.BooleanField(default=True, db_index=True)
    prioridade = models.SmallIntegerField(default=0)

    class Meta:
        verbose_name = "Merchant global"
        verbose_name_plural = "Merchants globais"
        ordering = ["-prioridade", "canonical_name"]

    def __str__(self):
        return self.canonical_name


class RegraCategorizacao(models.Model):
    TIPO_REGRA_CHOICES = [
        ("contains", "Contém"),
        ("startswith", "Começa com"),
        ("regex", "Expressão regular"),
        ("merchant_exact", "Merchant exato"),
    ]
    ORIGEM_CHOICES = [
        ("manual", "Manual"),
        ("aprendida", "Aprendida"),
        ("seed", "Seed"),
    ]
    TIPO_TRANSACAO_CHOICES = [
        ("receita", "Receita"),
        ("despesa", "Despesa"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="regras_categorizacao",
        null=True,
        blank=True,
    )
    tipo_regra = models.CharField(max_length=20, choices=TIPO_REGRA_CHOICES)
    padrao = models.CharField(max_length=255)
    padrao_normalizado = models.CharField(max_length=255, db_index=True)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        related_name="regras_categorizacao",
    )
    tipo_transacao = models.CharField(
        max_length=10,
        choices=TIPO_TRANSACAO_CHOICES,
        null=True,
        blank=True,
    )
    prioridade = models.IntegerField(default=0)
    confianca_base = models.FloatField(default=0.95)
    origem = models.CharField(max_length=20, choices=ORIGEM_CHOICES, default="manual")
    ativa = models.BooleanField(default=True, db_index=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Regra de categorização"
        verbose_name_plural = "Regras de categorização"
        ordering = ["-prioridade", "-confianca_base"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "padrao_normalizado", "tipo_regra"],
                condition=models.Q(ativa=True),
                name="categorizacao_regra_unica_ativa",
            ),
        ]
        indexes = [
            models.Index(
                fields=["usuario", "ativa"],
                name="cat_regra_user_ativa_idx",
            ),
        ]

    def __str__(self):
        escopo = self.usuario_id or "global"
        return f"[{escopo}] {self.tipo_regra}: {self.padrao}"


class MemoriaMerchantUsuario(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memorias_merchant",
    )
    merchant_key = models.CharField(max_length=120)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        related_name="memorias_merchant",
    )
    confirmacoes = models.PositiveIntegerField(default=0)
    correcoes = models.PositiveIntegerField(default=0)
    score = models.FloatField(default=0.0)
    ultima_confirmacao = models.DateTimeField(null=True, blank=True)
    origem = models.CharField(
        max_length=20,
        choices=[
            ("human", "Humano confirmado"),
            ("llm_pending", "Pendente LLM"),
            ("import_passive", "Import passivo"),
        ],
        default="human",
    )

    class Meta:
        verbose_name = "Memória merchant do usuário"
        verbose_name_plural = "Memórias merchant dos usuários"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "merchant_key"],
                name="categorizacao_memoria_merchant_unica",
            ),
        ]
        indexes = [
            models.Index(
                fields=["usuario", "merchant_key"],
                name="cat_mem_user_merch_idx",
            ),
        ]

    def recalcular_score(self) -> None:
        total = self.confirmacoes + self.correcoes
        self.score = (self.confirmacoes / total) if total else 0.0

    def __str__(self):
        return f"{self.usuario_id}:{self.merchant_key} → {self.categoria_id}"


class EventoCategorizacao(models.Model):
    ACAO_CHOICES = [
        ("sugerida", "Sugerida"),
        ("aceita", "Aceita"),
        ("corrigida", "Corrigida"),
        ("ignorada", "Ignorada"),
        ("auto_aplicada", "Auto-aplicada"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="eventos_categorizacao",
    )
    transacao = models.ForeignKey(
        "transacoes.Transacao",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_categorizacao",
    )
    descricao_original = models.CharField(max_length=255, blank=True)
    merchant_key = models.CharField(max_length=120, blank=True)
    categoria_sugerida = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_sugeridos",
    )
    categoria_final = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_finais",
    )
    confianca = models.FloatField(null=True, blank=True)
    fonte = models.CharField(max_length=30, blank=True)
    acao = models.CharField(max_length=20, choices=ACAO_CHOICES)
    contexto = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Evento de categorização"
        verbose_name_plural = "Eventos de categorização"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(
                fields=["usuario", "criado_em"],
                name="cat_evento_user_dt_idx",
            ),
        ]

    def __str__(self):
        return f"{self.acao} ({self.usuario_id})"


class ModeloClassificacaoUsuario(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="modelo_classificacao",
    )
    artefato = models.BinaryField(null=True, blank=True)
    versao = models.PositiveIntegerField(default=0)
    amostras_treino = models.PositiveIntegerField(default=0)
    metricas = models.JSONField(default=dict, blank=True)
    treinado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Modelo de classificação do usuário"
        verbose_name_plural = "Modelos de classificação dos usuários"

    def __str__(self):
        return f"Modelo ML usuário {self.usuario_id} v{self.versao}"


class AgregacaoMerchantGlobal(models.Model):
    """Agregação anonimizada merchant→categoria (opt-in dos usuários)."""

    merchant_key = models.CharField(max_length=120, db_index=True)
    categoria_padrao_nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, default="despesa")
    ocorrencias = models.PositiveIntegerField(default=0)
    usuarios_distintos = models.PositiveIntegerField(default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Agregação merchant global"
        verbose_name_plural = "Agregações merchant globais"
        constraints = [
            models.UniqueConstraint(
                fields=["merchant_key", "categoria_padrao_nome", "tipo"],
                name="categorizacao_agreg_merchant_cat",
            ),
        ]

    def __str__(self):
        return f"{self.merchant_key} → {self.categoria_padrao_nome} ({self.ocorrencias})"


class LLMRequestLog(models.Model):
    """Auditoria de chamadas LLM (sem descrição bruta)."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="llm_request_logs",
    )
    model = models.CharField(max_length=80)
    latency_ms = models.FloatField(default=0)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    success = models.BooleanField(default=False)
    cache_hit = models.BooleanField(default=False)
    gate_reason = models.CharField(max_length=60, blank=True)
    descricao_hash = models.CharField(max_length=64, blank=True)
    cost_usd_estimated = models.FloatField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Log de requisição LLM"
        verbose_name_plural = "Logs de requisições LLM"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["usuario", "criado_em"], name="cat_llm_log_user_dt_idx"),
        ]

    def __str__(self):
        return f"LLM {self.model} ({self.usuario_id})"
