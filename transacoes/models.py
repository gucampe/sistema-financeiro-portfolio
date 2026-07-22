# transacoes/models.py

from __future__ import annotations

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
        ("transferencia", "Transferência"),
    )

    PAPEL_TRANSFERENCIA_CHOICES = (
        ("origem", "Origem"),
        ("destino", "Destino"),
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

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)

    # chave obrigatória
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="transacoes",
    )

    valor = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.CharField(max_length=255)
    data = models.DateField()

    # Vínculo permanente das duas pernas de uma transferência (mesmo UUID).
    transfer_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Identificador compartilhado pelas duas transações de uma transferência.",
    )
    papel_transferencia = models.CharField(
        max_length=10,
        choices=PAPEL_TRANSFERENCIA_CHOICES,
        null=True,
        blank=True,
        help_text="origem = saída da conta; destino = entrada na conta.",
    )

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
            models.Index(
                fields=["usuario", "transfer_id"],
                name="transacao_user_transfer_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["conta", "ofx_fitid"],
                condition=models.Q(ofx_fitid__isnull=False) & ~models.Q(ofx_fitid=""),
                name="transacoes_transacao_uniq_conta_ofx_fitid",
            ),
            # No máximo uma origem e um destino por transfer_id.
            models.UniqueConstraint(
                fields=["transfer_id", "papel_transferencia"],
                condition=models.Q(transfer_id__isnull=False),
                name="transacoes_uniq_transfer_id_papel",
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

        if self.tipo == "transferencia":
            if not self.transfer_id:
                errors["transfer_id"] = "Transferência exige transfer_id."
            if self.papel_transferencia not in ("origem", "destino"):
                errors["papel_transferencia"] = "Transferência exige papel origem ou destino."
            if self.cartao_id or self.fatura_id or self.pagamento_de_fatura_id:
                errors["cartao"] = "Transferência entre contas não pode envolver cartão ou fatura."
        else:
            if self.transfer_id is not None:
                errors["transfer_id"] = "Apenas transferências podem ter transfer_id."
            if self.papel_transferencia is not None:
                errors["papel_transferencia"] = "Apenas transferências podem ter papel_transferencia."

        if errors:
            raise ValidationError(errors)

    def _sincronizar_fatura_e_competencia(self):
        if self.tipo == "transferencia":
            self.fatura_id = None
            self.data_competencia = None
            self.cartao_id = None
            self.pagamento_de_fatura_id = None
            return
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

    def contraparte(self) -> Transacao | None:
        """Retorna a outra perna da transferência vinculada pelo mesmo transfer_id."""
        if self.tipo != "transferencia" or not self.transfer_id:
            return None
        cached = getattr(self, "_contraparte_cache", None)
        if hasattr(self, "_contraparte_cache"):
            return cached
        return (
            Transacao.objects.filter(transfer_id=self.transfer_id, usuario_id=self.usuario_id)
            .exclude(pk=self.pk)
            .select_related("conta")
            .first()
        )

    def rotulo_historico_transferencia(self) -> str:
        """
        Texto do histórico: "Transferência para X" / "Recebida de Y".
        Usa contraparte() (com cache opcional de prefetch na listagem).
        """
        if self.tipo != "transferencia":
            return ""
        outra = self.contraparte()
        nome = outra.conta.nome if outra is not None and outra.conta_id else None
        if self.papel_transferencia == "origem":
            return f"Transferência para {nome}" if nome else "Transferência (saída)"
        if self.papel_transferencia == "destino":
            return f"Recebida de {nome}" if nome else "Transferência (entrada)"
        return "Transferência"

    def __str__(self):
        return f"{self.tipo} - {self.categoria.nome} - {self.valor}"


class TransferenciaIdempotencia(models.Model):
    """
    Registro de idempotência para criação de transferências.
    Mesma chave (por usuário) sempre resolve para o mesmo transfer_id.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transferencias_idempotencia",
    )
    key = models.UUIDField()
    transfer_id = models.UUIDField(db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "key"],
                name="transacoes_uniq_user_idempotency_key",
            ),
        ]
        indexes = [
            models.Index(fields=["usuario", "criado_em"], name="transf_idem_user_criado_idx"),
        ]

    def __str__(self):
        return f"{self.usuario_id}:{self.key} → {self.transfer_id}"
