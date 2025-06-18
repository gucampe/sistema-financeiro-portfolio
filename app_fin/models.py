from django.db import models

# Create your models here.
class Usuario(models.Model):
    nome = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    data_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome
