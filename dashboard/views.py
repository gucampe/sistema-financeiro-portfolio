from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from financeiro.models import Transacao
from financeiro.forms import TransacaoForm
from django.db.models import Sum
from categorias.models import Categoria
from django.db.models import Q

from datetime import date
import calendar


@login_required
def dashboard_view(request):
    transacoes = Transacao.objects.filter(usuario=request.user).order_by('-data')
    hoje = date.today()
    mes_atual = hoje.month
    ano_atual = hoje.year

    entradas_mes = transacoes.filter(
        tipo='receita',
        data__month=mes_atual,
        data__year=ano_atual
    ).aggregate(total=Sum('valor'))['total'] or 0

    saidas_mes = transacoes.filter(
        tipo='despesa',
        data__month=mes_atual,
        data__year=ano_atual
    ).aggregate(total=Sum('valor'))['total'] or 0

    saldo_total = entradas_mes - saidas_mes

    # Gráfico dos últimos 6 meses
    dados_entradas = []
    dados_saidas = []
    labels = []

    for i in range(5, -1, -1):
        mes = (hoje.month - i - 1) % 12 + 1
        ano = hoje.year if hoje.month - i > 0 else hoje.year - 1

        total_entrada = transacoes.filter(
            tipo='receita',
            data__month=mes,
            data__year=ano
        ).aggregate(Sum('valor'))['valor__sum'] or 0

        total_saida = transacoes.filter(
            tipo='despesa',
            data__month=mes,
            data__year=ano
        ).aggregate(Sum('valor'))['valor__sum'] or 0

        dados_entradas.append(float(total_entrada))
        dados_saidas.append(float(total_saida))
        labels.append(calendar.month_abbr[mes])

    ultimas_transacoes = transacoes[:5]

    # Categorias ativas por tipo (usuário + padrão)
    categorias_despesa = Categoria.objects.filter(
        Q(usuario=request.user) | Q(padrao=True),
        tipo="despesa",
        ativa=True
    ).order_by("nome")
    categorias_receita = Categoria.objects.filter(
        Q(usuario=request.user) | Q(padrao=True),
        tipo="receita",
        ativa=True
    ).order_by("nome")

    form = TransacaoForm(usuario=request.user, tipo_inicial="despesa")

    return render(request, 'dashboard/partials/home.html', {
        'saldo_total': saldo_total,
        'entradas_mes': entradas_mes,
        'saidas_mes': saidas_mes,
        'labels': labels,
        'dados_entradas': dados_entradas,
        'dados_saidas': dados_saidas,
        'ultimas_transacoes': ultimas_transacoes,
        'ano_atual': str(ano_atual),
        'mes_atual': str(mes_atual),

        'categorias_despesa': categorias_despesa,
        'categorias_receita': categorias_receita,
        'form': form,
    })
