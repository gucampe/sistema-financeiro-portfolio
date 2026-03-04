# transacoes/models.py

from django.conf import settings
from django.db import models

from categorias.models import Categoria
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
        blank=True,
        null=True,
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

    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data", "-id"]

    def __str__(self):
        return f"{self.tipo} - {self.categoria.nome} - {self.valor}"
