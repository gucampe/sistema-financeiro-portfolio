# categorias/models.py
from django.db import models
from django.conf import settings

class Categoria(models.Model):
    ICONES_CHOICES = [
        ("fa-utensils", "Alimentação"),
        ("fa-home", "Casa"),
        ("fa-car", "Transporte"),
        ("fa-briefcase", "Trabalho"),
        ("fa-gift", "Presentes"),
        ("fa-heart", "Saúde"),
        ("fa-graduation-cap", "Educação"),
        ("fa-paw", "Pets"),
        ("fa-shopping-cart", "Compras"),
        ("fa-ellipsis-h", "Outros"),
    ]

    CORES_CHOICES = [
        ("#4F46E5", "Roxo"),
        ("#10B981", "Verde"),
        ("#EF4444", "Vermelho"),
        ("#F59E0B", "Amarelo"),
        ("#3B82F6", "Azul"),
        ("#EC4899", "Rosa"),
        ("#6B7280", "Cinza"),
    ]

    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    cor = models.CharField(max_length=7, choices=CORES_CHOICES, default="#4F46E5")
    icone = models.CharField(max_length=50, choices=ICONES_CHOICES, default="fa-ellipsis-h")

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categorias",
        blank=True,
        null=True
    )
    padrao = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["nome"]
        unique_together = ("nome", "usuario")

    def __str__(self):
        return self.nome
