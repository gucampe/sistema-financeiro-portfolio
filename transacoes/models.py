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
    fatura = models.ForeignKey(
        "cartoes.Fatura",
        on_delete=models.SET_NULL,
        related_name="lancamentos",
        null=True,
        blank=True,
    )
    pagamento_de_fatura = models.ForeignKey(
        "cartoes.Fatura",
        on_delete=models.SET_NULL,
        related_name="pagamentos",
        null=True,
        blank=True,
    )
    data_competencia = models.DateField(
        null=True,
        blank=True,
        help_text="Para cartão: data de vencimento da fatura (lista e competência); senão igual à data da compra.",
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
            models.Index(fields=["usuario", "data_competencia"], name="transacao_user_comp_idx"),
            models.Index(fields=["usuario", "tipo", "data"], name="transacao_user_tipo_data_idx"),
            models.Index(fields=["usuario", "conta", "data"], name="transacao_user_conta_data_idx"),
            models.Index(fields=["usuario", "fatura"], name="transacao_user_fatura_idx"),
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
        if self.fatura_id and self.cartao_id and self.fatura.cartao_id != self.cartao_id:
            errors["fatura"] = "A fatura deve ser do mesmo cartão da transação."
        if self.fatura_id and self.usuario_id and self.fatura.usuario_id != self.usuario_id:
            errors["fatura"] = "A fatura deve pertencer ao usuário da transação."
        if (
            self.pagamento_de_fatura_id
            and self.usuario_id
            and self.pagamento_de_fatura.usuario_id != self.usuario_id
        ):
            errors["pagamento_de_fatura"] = (
                "A fatura de pagamento deve pertencer ao usuário da transação."
            )
        if self.categoria_id and self.usuario_id:
            if not (self.categoria.padrao or self.categoria.usuario_id == self.usuario_id):
                errors["categoria"] = "A categoria deve ser padrão ou pertencer ao usuário da transação."
        if errors:
            raise ValidationError(errors)

    def _sincronizar_fatura_e_competencia(self):
        if self.pagamento_de_fatura_id:
            return
        if self.cartao_id and self.data:
            from cartoes.services.faturas import obter_ou_criar_fatura

            f = obter_ou_criar_fatura(self.cartao, self.data)
            self.fatura_id = f.pk
            self.data_competencia = f.data_vencimento
        else:
            self.fatura_id = None
            self.data_competencia = None

    def save(self, *args, **kwargs):
        self._sincronizar_fatura_e_competencia()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo} - {self.categoria.nome} - {self.valor}"
