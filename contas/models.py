from django.conf import settings
from django.db import models
from django.db.models import Case, DecimalField, F, Sum, When
from decimal import Decimal

class Conta(models.Model):
    TIPO_CHOICES = [
        ("corrente", "Corrente"),
        ("poupanca", "Poupança"),
        ("carteira", "Carteira"),
        ("investimento", "Investimento"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contas",
    )
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    icone = models.CharField(max_length=50, default="bank")
    ativa = models.BooleanField(default=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["usuario", "nome"]
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

    @property
    def saldo_atual_calc(self):
        """Saldo calculado a partir das transações (receita +, despesa -, ajuste +). Use quando não houver annotate."""
        from transacoes.models import Transacao

        qs = Transacao.objects.filter(conta=self, usuario=self.usuario)
        aggregate_expr = Sum(
            Case(
                When(tipo="receita", then=F("valor")),
                When(tipo="despesa", then=-F("valor")),
                When(tipo="ajuste", then=F("valor")),
                default=Decimal("0.00"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
        result = qs.aggregate(saldo=aggregate_expr)["saldo"]
        return result or Decimal("0.00")
