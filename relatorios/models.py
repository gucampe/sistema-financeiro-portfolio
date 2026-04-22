from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from categorias.models import Categoria


class OrcamentoCategoria(models.Model):
    """Planejamento mensal por categoria de despesa."""

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
    ano = models.PositiveIntegerField()
    mes = models.PositiveSmallIntegerField()  # 1–12
    valor_planejado = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Orçamento por categoria"
        verbose_name_plural = "Orçamentos por categoria"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "categoria", "ano", "mes"],
                name="relatorios_orcamento_unico_usuario_categoria_ano_mes",
            ),
        ]
        ordering = ["-ano", "-mes", "categoria__nome"]

    def clean(self):
        super().clean()
        if self.mes < 1 or self.mes > 12:
            raise ValidationError({"mes": "Mês inválido."})
        if self.categoria.tipo != "despesa":
            raise ValidationError({"categoria": "Orçamento só para categorias de despesa."})
        if not (self.categoria.padrao or self.categoria.usuario_id == self.usuario_id):
            raise ValidationError({"categoria": "Categoria inválida para este usuário."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.categoria.nome} {self.mes:02d}/{self.ano}: {self.valor_planejado}"


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
