# categorias/models.py
from django.db import models
from django.conf import settings


class Categoria(models.Model):
    TIPO_CHOICES = [
        ("receita", "Receita"),
        ("despesa", "Despesa"),
    ]

    CORES_CHOICES = [
        # Azuis
        ("#1D4ED8", "Azul intenso"),
        ("#2563EB", "Azul"),
        ("#3B82F6", "Azul claro"),

        # Verdes
        ("#059669", "Verde escuro"),
        ("#10B981", "Verde"),
        ("#22C55E", "Verde claro"),

        # Roxos
        ("#4F46E5", "Roxo"),
        ("#6366F1", "Índigo"),

        # Vermelhos
        ("#DC2626", "Vermelho escuro"),
        ("#EF4444", "Vermelho"),

        # Laranja / Amarelo
        ("#F97316", "Laranja"),
        ("#F59E0B", "Amarelo"),

        # Rosa
        ("#EC4899", "Rosa"),

        # Neutros
        ("#4B5563", "Cinza escuro"),
        ("#6B7280", "Cinza"),
        ("#9CA3AF", "Cinza claro"),
    ]

    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        default="despesa",
        db_index=True,
    )

    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)

    # Mantém choices de cor (ok), mas deixa ícone livre (sem choices) pra aceitar qualquer FA
    cor = models.CharField(max_length=7, choices=CORES_CHOICES, default="#4F46E5")
    icone = models.CharField(max_length=50, default="fa-ellipsis-h")

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categorias",
        blank=True,
        null=True
    )

    padrao = models.BooleanField(default=False)
    ativa = models.BooleanField(default=True, db_index=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["tipo", "nome"]
        unique_together = ("nome", "usuario", "tipo")

    def __str__(self):
        return f"{self.nome} ({self.tipo})"