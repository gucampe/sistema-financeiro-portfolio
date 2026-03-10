# transacoes/services.py
from decimal import Decimal

from categorias.models import Categoria
from .models import Transacao


def criar_transacao_saldo_inicial(usuario, conta, valor, data):
    """
    Cria uma transação do tipo ajuste com descrição "Saldo inicial" para a conta.
    Usada quando uma conta é criada com saldo inicial diferente de zero.
    """
    if valor == Decimal("0.00"):
        return None
    categoria_ajuste, _ = Categoria.objects.get_or_create(
        usuario=None,
        padrao=True,
        tipo="receita",
        nome="Ajustes de saldo",
        defaults={
            "descricao": "Ajustes automáticos de saldo de contas",
            "cor": "#6B7280",
            "icone": "fa-ellipsis-h",
            "ativa": True,
        },
    )
    return Transacao.objects.create(
        usuario=usuario,
        conta=conta,
        tipo="ajuste",
        valor=valor,
        descricao="Saldo inicial",
        data=data,
        categoria=categoria_ajuste,
    )
