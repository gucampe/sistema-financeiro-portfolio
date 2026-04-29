from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from contas.models import Conta


class Cartao(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cartoes",
    )
    nome = models.CharField(max_length=100)
    icone = models.CharField(max_length=50, default="bank")
    limite = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    dia_fechamento = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    dia_vencimento = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    conta_padrao = models.ForeignKey(
        Conta,
        on_delete=models.PROTECT,
        related_name="cartoes_padrao",
    )
    ativa = models.BooleanField(default=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome"]
        unique_together = ["usuario", "nome"]

    def __str__(self):
        return self.nome


class Fatura(models.Model):
    """Ciclo de faturamento mensal de um cartão (MVP: sem parcelamento nem pagamento de fatura)."""

    class Status(models.TextChoices):
        ABERTA = "aberta", "Aberta"
        FECHADA = "fechada", "Fechada"

    class StatusPagamento(models.TextChoices):
        VAZIA = "vazia", "Vazia"
        PENDENTE = "pendente", "Pendente"
        PARCIAL = "parcial", "Parcial"
        PAGO = "pago", "Pago"
        ATRASADO = "atrasado", "Atrasado"

    class StatusTemporal(models.TextChoices):
        FUTURA = "futura", "Futura"
        ABERTA = "aberta", "Aberta"
        FECHADA = "fechada", "Fechada"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="faturas_cartao",
    )
    cartao = models.ForeignKey(
        Cartao,
        on_delete=models.PROTECT,
        related_name="faturas",
    )
    competencia = models.DateField(
        help_text="Primeiro dia do mês de competência (ex.: fatura de abril/2026 → 2026-04-01).",
    )
    data_fechamento = models.DateField(help_text="Data de fechamento deste ciclo.")
    data_vencimento = models.DateField(help_text="Data de vencimento desta fatura.")
    data_inicio_compras = models.DateField()
    data_fim_compras = models.DateField()
    valor_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cache opcional; total pode ser calculado pelas transações.",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ABERTA,
    )
    status_ciclo = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ABERTA,
    )
    status_pagamento = models.CharField(
        max_length=10,
        choices=StatusPagamento.choices,
        default=StatusPagamento.PENDENTE,
    )
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-competencia", "-data_vencimento"]
        constraints = [
            models.UniqueConstraint(
                fields=["cartao", "competencia"],
                name="cartoes_fatura_uniq_cartao_competencia",
            ),
        ]
        indexes = [
            models.Index(fields=["cartao", "data_vencimento"], name="cartoes_fatura_cartao_venc_idx"),
            models.Index(fields=["usuario", "data_vencimento"], name="cartoes_fatura_user_venc_idx"),
        ]

    def __str__(self):
        return f"{self.cartao.nome} — {self.competencia:%m/%Y}"

    def get_status_temporal(self, hoje=None) -> str:
        """
        Status temporal derivado (não persistido):
        - futura: antes do início do ciclo
        - aberta: durante o ciclo de compras
        - fechada: após fechamento do ciclo
        """
        hoje = hoje or timezone.localdate()
        if hoje < self.data_inicio_compras:
            return self.StatusTemporal.FUTURA
        if hoje <= self.data_fim_compras:
            return self.StatusTemporal.ABERTA
        return self.StatusTemporal.FECHADA

    @property
    def status_temporal(self) -> str:
        return self.get_status_temporal()

    def get_status_temporal_display(self) -> str:
        return self.StatusTemporal(self.get_status_temporal()).label
