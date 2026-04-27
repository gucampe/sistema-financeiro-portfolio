# transacoes/models.py

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from categorias.models import Categoria
from cartoes.models import Cartao
from contas.models import Conta


class Transacao(models.Model):
    TIPO_CHOICES = (
        ("receita", "Receita"),
        ("despesa", "Despesa"),
        ("ajuste", "Ajuste"),
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transacoes",
    )

    conta = models.ForeignKey(
        Conta,
        on_delete=models.PROTECT,
        related_name="transacoes",
    )
    cartao = models.ForeignKey(
        Cartao,
        on_delete=models.SET_NULL,
        related_name="transacoes",
        null=True,
        blank=True,
    )

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)

    # chave obrigatória
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="transacoes",
    )

    valor = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.CharField(max_length=255)
    data = models.DateField()

    # Identificador OFX (FITID), quando existir no extrato — usado para deduplicação forte.
    ofx_fitid = models.CharField(max_length=255, null=True, blank=True, db_index=True)

    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data", "-id"]
        indexes = [
            models.Index(fields=["usuario", "data"], name="transacao_usuario_data_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["conta", "ofx_fitid"],
                condition=models.Q(ofx_fitid__isnull=False) & ~models.Q(ofx_fitid=""),
                name="transacoes_transacao_uniq_conta_ofx_fitid",
            ),
        ]

    def clean(self):
        if self.ofx_fitid is not None and not str(self.ofx_fitid).strip():
            self.ofx_fitid = None
        errors = {}
        if self.conta_id and self.usuario_id and self.conta.usuario_id != self.usuario_id:
            errors["conta"] = "A conta deve pertencer ao usuário da transação."
        if self.cartao_id and self.usuario_id and self.cartao.usuario_id != self.usuario_id:
            errors["cartao"] = "O cartão deve pertencer ao usuário da transação."
        if self.categoria_id and self.usuario_id:
            if not (self.categoria.padrao or self.categoria.usuario_id == self.usuario_id):
                errors["categoria"] = "A categoria deve ser padrão ou pertencer ao usuário da transação."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo} - {self.categoria.nome} - {self.valor}"
