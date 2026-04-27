from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

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
