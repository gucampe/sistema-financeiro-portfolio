from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from categorias.models import Categoria


class OrcamentoCategoria(models.Model):
    """Regra recorrente de limite mensal por categoria de despesa."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orcamentos_categoria",
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        related_name="orcamentos",
    )
    valor_planejado = models.DecimalField(max_digits=12, decimal_places=2)
    ativo = models.BooleanField(default=True, db_index=True)
    inicio_ano = models.PositiveIntegerField()
    inicio_mes = models.PositiveSmallIntegerField()  # 1–12
    fim_ano = models.PositiveIntegerField(null=True, blank=True)
    fim_mes = models.PositiveSmallIntegerField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Orçamento por categoria"
        verbose_name_plural = "Orçamentos por categoria"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "categoria"],
                name="relatorios_orcamento_unico_usuario_categoria",
            ),
        ]
        ordering = ["categoria__nome"]

    def vigente_em(self, ano: int, mes: int) -> bool:
        if not self.ativo:
            return False
        ref = (ano, mes)
        if ref < (self.inicio_ano, self.inicio_mes):
            return False
        if self.fim_ano is not None and self.fim_mes is not None:
            if ref > (self.fim_ano, self.fim_mes):
                return False
        return True

    def clean(self):
        super().clean()
        if self.inicio_mes < 1 or self.inicio_mes > 12:
            raise ValidationError({"inicio_mes": "Mês de início inválido."})
        if self.fim_mes is not None and (self.fim_mes < 1 or self.fim_mes > 12):
            raise ValidationError({"fim_mes": "Mês de fim inválido."})
        if self.fim_ano is not None and self.fim_mes is not None:
            if (self.fim_ano, self.fim_mes) < (self.inicio_ano, self.inicio_mes):
                raise ValidationError({"fim_ano": "A vigência final deve ser posterior ao início."})
        if self.valor_planejado is not None and self.valor_planejado <= 0:
            raise ValidationError({"valor_planejado": "O valor deve ser maior que zero."})
        if self.categoria.tipo != "despesa":
            raise ValidationError({"categoria": "Orçamento só para categorias de despesa."})
        if self.usuario_id and not (self.categoria.padrao or self.categoria.usuario_id == self.usuario_id):
            raise ValidationError({"categoria": "Categoria inválida para este usuário."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        fim = ""
        if self.fim_ano and self.fim_mes:
            fim = f" até {self.fim_mes:02d}/{self.fim_ano}"
        return f"{self.categoria.nome} {self.inicio_mes:02d}/{self.inicio_ano}{fim}: {self.valor_planejado}"


class ExportRelatorioJob(models.Model):
    """Fila leve de exportação CSV (processamento em thread)."""

    STATUS_PENDING = "pending"
    STATUS_READY = "ready"
    STATUS_ERROR = "error"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pendente"),
        (STATUS_READY, "Pronto"),
        (STATUS_ERROR, "Erro"),
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="export_relatorio_jobs",
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    filtros_json = models.TextField(default="{}")
    arquivo = models.FileField(upload_to="exports/relatorios/", blank=True, null=True)
    mensagem_erro = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Export #{self.pk} ({self.get_status_display()})"
