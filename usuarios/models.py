from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from .managers import UsuarioManager  # Manager customizado

class Usuario(AbstractUser):
    username = None  # remove o campo username
    first_name = None  # remove first_name herdado
    last_name = None   # remove last_name herdado
    date_joined = None # substituído por 'criado_em'
    

    email = models.EmailField(_('E-mail'), unique=True)
    nome = models.CharField(_('Nome completo'), max_length=100)
    data_nascimento = models.DateField(_('Data de nascimento'), null=True, blank=True)
    criado_em = models.DateTimeField(_('Criado em'), auto_now_add=True)
    atualizado_em = models.DateTimeField(_('Atualizado em'), auto_now=True)
    ativo = models.BooleanField(_('Usuário ativo'), default=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']

    objects = UsuarioManager()

    def __str__(self):
        return f'{self.nome} <{self.email}>'
