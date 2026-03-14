from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import TransacaoForm
from .models import Transacao
from django.shortcuts import redirect, render
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta

from categorias.models import Categoria
from contas.models import Conta


@login_required
def adicionar_transacao(request):
    transacoes = Transacao.objects.filter(
        usuario=request.user
    ).select_related("categoria", "conta").order_by("-data", "-id")

    from django.db.models import Q
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
    contas = Conta.objects.filter(usuario=request.user, ativa=True).order_by("nome")

    if request.method == 'POST':
        tipo_inicial = request.POST.get('tipo', 'despesa')
        form = TransacaoForm(request.POST, usuario=request.user, tipo_inicial=tipo_inicial)
        if form.is_valid():
            transacao = form.save(commit=False)
            transacao.usuario = request.user
            transacao.save()

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                resp = {
                    'status': 'ok',
                    'id': transacao.id,
                    'tipo': transacao.tipo,
                    'descricao': transacao.descricao,
                    'valor': str(transacao.valor),
                    'data': transacao.data.strftime('%Y-%m-%d'),
                    'categoria': {
                        'id': transacao.categoria.id,
                        'nome': transacao.categoria.nome,
                        'icone': transacao.categoria.icone,
                        'cor': transacao.categoria.cor,
                    }
                }
                if transacao.conta_id:
                    resp['conta'] = {
                        'id': transacao.conta.id,
                        'nome': transacao.conta.nome,
                        'icone': transacao.conta.icone,
                    }
                return JsonResponse(resp)

            return redirect('dashboard:home')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    else:
        form = TransacaoForm(usuario=request.user)

    context = {
        "transacoes": transacoes,
        "form": form,
        "categorias_despesa": categorias_despesa,
        "categorias_receita": categorias_receita,
        "contas": contas,
    }
    return render(request, 'transacoes/partials/historico.html', context)


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
