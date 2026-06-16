import calendar
import uuid
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from categorias.models import Categoria


def export_arquivo_upload_to(instance, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    uid = instance.token_download or uuid.uuid4()
    return f"exports/{instance.usuario_id}/{uid}.{ext}"


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
        if not self.ativo:
            return False
        return self.cadastrado_ate_mes(ano, mes)

    def cadastrado_ate_mes(self, ano: int, mes: int) -> bool:
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


class ExportJob(models.Model):
    """Job de exportação de dados ou relatório (processado fora do request web)."""

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_READY = "ready"
    STATUS_ERROR = "error"
    STATUS_CANCELLED = "cancelled"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pendente"),
        (STATUS_PROCESSING, "Processando"),
        (STATUS_READY, "Pronto"),
        (STATUS_ERROR, "Erro"),
        (STATUS_CANCELLED, "Cancelado"),
        (STATUS_EXPIRED, "Expirado"),
    )

    DOMINIO_TRANSACOES = "transacoes"
    DOMINIO_CONTAS = "contas"
    DOMINIO_CARTOES = "cartoes"
    DOMINIO_ORCAMENTOS = "orcamentos"
    DOMINIO_INVESTIMENTOS = "investimentos"
    DOMINIO_RELATORIO_PDF = "relatorio_pdf"
    DOMINIO_CHOICES = (
        (DOMINIO_TRANSACOES, "Transações"),
        (DOMINIO_CONTAS, "Contas"),
        (DOMINIO_CARTOES, "Cartões"),
        (DOMINIO_ORCAMENTOS, "Orçamentos"),
        (DOMINIO_INVESTIMENTOS, "Investimentos"),
        (DOMINIO_RELATORIO_PDF, "Relatório PDF"),
    )

    FORMATO_CSV = "csv"
    FORMATO_XLSX = "xlsx"
    FORMATO_PDF = "pdf"
    FORMATO_CHOICES = (
        (FORMATO_CSV, "CSV"),
        (FORMATO_XLSX, "Excel"),
        (FORMATO_PDF, "PDF"),
    )

    ORIGEM_MANUAL = "manual"
    ORIGEM_SCHEDULED = "scheduled"
    ORIGEM_CHOICES = (
        (ORIGEM_MANUAL, "Manual"),
        (ORIGEM_SCHEDULED, "Agendado"),
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="export_jobs",
    )
    dominio = models.CharField(max_length=32, choices=DOMINIO_CHOICES, default=DOMINIO_TRANSACOES)
    formato = models.CharField(max_length=8, choices=FORMATO_CHOICES, default=FORMATO_CSV)
    origem = models.CharField(max_length=16, choices=ORIGEM_CHOICES, default=ORIGEM_MANUAL)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    filtros_json = models.TextField(default="{}")
    arquivo = models.FileField(upload_to=export_arquivo_upload_to, blank=True, null=True)
    nome_arquivo = models.CharField(max_length=255, blank=True)
    tamanho_bytes = models.BigIntegerField(default=0)
    linhas_count = models.IntegerField(default=0)
    tentativas = models.SmallIntegerField(default=0)
    max_tentativas = models.SmallIntegerField(default=3)
    task_id = models.CharField(max_length=255, blank=True, db_index=True)
    idempotency_key = models.UUIDField(null=True, blank=True, unique=True)
    mensagem_erro = models.TextField(blank=True)
    erro_interno = models.TextField(blank=True)
    cancelado_em = models.DateTimeField(null=True, blank=True)
    iniciado_em = models.DateTimeField(null=True, blank=True)
    finalizado_em = models.DateTimeField(null=True, blank=True)
    expira_em = models.DateTimeField(null=True, blank=True, db_index=True)
    token_download = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["usuario", "status"]),
            models.Index(fields=["status", "iniciado_em"]),
        ]

    def __str__(self):
        return f"Export #{self.pk} ({self.dominio}/{self.formato} — {self.get_status_display()})"

    @property
    def download_filename(self) -> str:
        if self.nome_arquivo:
            return self.nome_arquivo
        if self.arquivo:
            return self.arquivo.name.split("/")[-1]
        return f"export_{self.pk}.{self.formato}"


# Alias retrocompatível
ExportRelatorioJob = ExportJob
