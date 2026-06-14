import calendar
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

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

    def _data_criacao_local(self) -> date:
        criado = self.criado_em
        if criado is None:
            return timezone.localdate()
        if timezone.is_aware(criado):
            return timezone.localtime(criado).date()
        return criado.date()

    def vigente_em(self, ano: int, mes: int) -> bool:
        """Ativo e criado até o último dia do mês de referência."""
        if not self.ativo:
            return False
        return self.cadastrado_ate_mes(ano, mes)

    def cadastrado_ate_mes(self, ano: int, mes: int) -> bool:
        """Registro criado até o último dia do mês (independente de ativo)."""
        ultimo_dia = date(ano, mes, calendar.monthrange(ano, mes)[1])
        return self._data_criacao_local() <= ultimo_dia

    def clean(self):
        super().clean()
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
        return f"{self.categoria.nome}: {self.valor_planejado}/mês"


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
