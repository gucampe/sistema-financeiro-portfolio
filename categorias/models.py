# categorias/models.py
from django.db import models
from django.conf import settings  # <- Importante

class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True, null=True)
    cor = models.CharField(
        max_length=7,
        default="#4F46E5",
        help_text="Cor em formato hexadecimal (ex: #4F46E5)"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,   # <- Ajustado
        on_delete=models.CASCADE,
        related_name="categorias"
    )
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["nome"]

    def __str__(self):
        return self.nome
