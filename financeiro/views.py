# financeiro/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import TransacaoForm
from .models import Transacao
from django.db.models import Sum
from django.http import JsonResponse
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta

@login_required
def adicionar_transacao(request):
    if request.method == 'POST':
        form = TransacaoForm(request.POST)
        if form.is_valid():
            transacao = form.save(commit=False)
            transacao.usuario = request.user
            transacao.save()
            return redirect('dashboard:home')  # ou outro nome da sua URL principal
    else:
        form = TransacaoForm()

    return render(request, 'financeiro/partials/adicionar_transacao.html', {'form': form})


@login_required
def dados_grafico_receitas_despesas(request):
    transacoes = (
        Transacao.objects.filter(usuario=request.user)
        .annotate(mes=TruncMonth('data'))
        .values('mes', 'tipo')
        .annotate(total=Sum('valor'))
        .order_by('mes')
    )

    dados = {}
    for item in transacoes:
        mes_str = item['mes'].strftime('%b %Y')
        if mes_str not in dados:
            dados[mes_str] = {'receita': 0, 'despesa': 0}
        dados[mes_str][item['tipo']] = float(item['total'])

    meses_labels = []
    receitas = []
    despesas = []

    hoje = datetime.today().replace(day=1)
    for i in range(11, -1, -1):
        mes_data = hoje - timedelta(days=30 * i)
        mes_label = mes_data.strftime('%b %Y')
        meses_labels.append(mes_label)
        receitas.append(dados.get(mes_label, {}).get('receita', 0))
        despesas.append(dados.get(mes_label, {}).get('despesa', 0))

    return JsonResponse({
        'labels': meses_labels,
        'receitas': receitas,
        'despesas': despesas,
    })