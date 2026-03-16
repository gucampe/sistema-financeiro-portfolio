from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import TransacaoForm
from .models import Transacao
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from itertools import groupby
from datetime import date, datetime, timedelta

from categorias.models import Categoria
from contas.models import Conta


@login_required
def adicionar_transacao(request):
    ano = request.GET.get("ano")
    mes = request.GET.get("mes")
    hoje = date.today()
    ano = ano or hoje.year
    mes = mes or hoje.month
    ano = int(ano)
    mes = int(mes)
    data_mes = date(ano, mes, 1)

    if mes == 1:
        mes_anterior = 12
        ano_anterior = ano - 1
    else:
        mes_anterior = mes - 1
        ano_anterior = ano

    if mes == 12:
        mes_proximo = 1
        ano_proximo = ano + 1
    else:
        mes_proximo = mes + 1
        ano_proximo = ano

    data_inicial = None
    data_fim = None
    inicio_str = request.GET.get("inicio")
    fim_str = request.GET.get("fim")
    if inicio_str and fim_str:
        try:
            data_inicial = datetime.strptime(inicio_str, "%Y-%m-%d").date()
            data_fim = datetime.strptime(fim_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            data_inicial = None
            data_fim = None

    if data_inicial is None:
        periodo = request.GET.get("periodo")
        if periodo == "hoje":
            data_inicial = hoje
            data_fim = hoje
        elif periodo == "semana":
            # segunda-feira da semana atual (weekday: 0=segunda, 6=domingo)
            data_inicial = hoje - timedelta(days=hoje.weekday())
        elif periodo == "mes":
            data_inicial = date(hoje.year, hoje.month, 1)
        elif periodo == "ano":
            data_inicial = date(hoje.year, 1, 1)
        elif periodo == "3m":
            total_meses = hoje.year * 12 + (hoje.month - 1) - 3
            data_inicial = date(total_meses // 12, (total_meses % 12) + 1, 1)
        elif periodo == "12m":
            total_meses = hoje.year * 12 + (hoje.month - 1) - 12
            data_inicial = date(total_meses // 12, (total_meses % 12) + 1, 1)
        else:
            data_inicial = None

    if data_inicial is not None:
        filtro_periodo = {"usuario": request.user, "data__gte": data_inicial}
        if data_fim is not None:
            filtro_periodo["data__lte"] = data_fim
        transacoes = Transacao.objects.filter(
            **filtro_periodo
        ).select_related("categoria", "conta").order_by("-data", "-id")
    else:
        transacoes = Transacao.objects.filter(
            usuario=request.user,
            data__year=ano,
            data__month=mes,
        ).select_related("categoria", "conta").order_by("-data", "-id")

    transacoes_list = list(transacoes)
    transacoes_por_dia = [
        {"data": data, "transacoes": list(grupo)}
        for data, grupo in groupby(
            transacoes_list,
            key=lambda t: t.data if isinstance(t.data, date) else t.data.date(),
        )
    ]

    if data_inicial is not None:
        filtro_totais = {"usuario": request.user, "data__gte": data_inicial}
        if data_fim is not None:
            filtro_totais["data__lte"] = data_fim
        totais = Transacao.objects.filter(
            **filtro_totais
        ).aggregate(
            total_receitas=Sum("valor", filter=Q(tipo="receita")),
            total_despesas=Sum("valor", filter=Q(tipo="despesa")),
        )
    else:
        totais = Transacao.objects.filter(
            usuario=request.user,
            data__year=ano,
            data__month=mes,
        ).aggregate(
            total_receitas=Sum("valor", filter=Q(tipo="receita")),
            total_despesas=Sum("valor", filter=Q(tipo="despesa")),
        )
    total_receitas = totais["total_receitas"] or 0
    total_despesas = totais["total_despesas"] or 0
    saldo_mes = total_receitas - total_despesas

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

    hoje = date.today()
    ano_hoje = hoje.year
    mes_hoje = hoje.month

    datas_distintas = Transacao.objects.filter(
        usuario=request.user
    ).dates("data", "month", order="DESC")
    meses_dropdown = [
        {"ano": d.year, "mes": d.month, "data_mes": d}
        for d in datas_distintas
    ]

    context = {
        "transacoes_por_dia": transacoes_por_dia,
        "ano": ano,
        "mes": mes,
        "ano_hoje": ano_hoje,
        "mes_hoje": mes_hoje,
        "data_mes": data_mes,
        "mes_anterior": mes_anterior,
        "ano_anterior": ano_anterior,
        "mes_proximo": mes_proximo,
        "ano_proximo": ano_proximo,
        "form": form,
        "categorias_despesa": categorias_despesa,
        "categorias_receita": categorias_receita,
        "contas": contas,
        "total_receitas": total_receitas,
        "total_despesas": total_despesas,
        "saldo_mes": saldo_mes,
        "meses_dropdown": meses_dropdown,
    }
    return render(request, 'transacoes/partials/historico.html', context)


@login_required
def editar_transacao(request, pk):
    transacao = get_object_or_404(Transacao, pk=pk, usuario=request.user)

    if request.method == "POST":
        form = TransacaoForm(
            request.POST, instance=transacao, usuario=request.user, tipo_inicial=transacao.tipo
        )
        if form.is_valid():
            with transaction.atomic():
                form.save()

            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({'status': 'ok'})
            
            ano_atual = transacao.data.year
            mes_atual = transacao.data.month
            return redirect(f"/transacoes/?ano={ano_atual}&mes={mes_atual}")
        else:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    else:
        if request.GET.get("ajax"):
            # Retornar JSON com os dados da transação
            return JsonResponse({
                "id": transacao.id,
                "tipo": transacao.tipo,
                "valor": str(transacao.valor),
                "descricao": transacao.descricao,
                "data": transacao.data.strftime("%Y-%m-%d"),
                "categoria": {
                    "id": transacao.categoria.id,
                    "nome": transacao.categoria.nome
                },
                "conta": {
                    "id": transacao.conta.id,
                    "nome": transacao.conta.nome
                } if transacao.conta else None
            })

    form = TransacaoForm(instance=transacao, usuario=request.user, tipo_inicial=transacao.tipo)
    return render(request, "transacoes/editar_transacao.html", {"form": form, "transacao": transacao})


@require_POST
@login_required
def excluir_transacao(request, pk):
    transacao = get_object_or_404(Transacao, pk=pk, usuario=request.user)
    if request.method == "POST":
        ano_atual = transacao.data.year
        mes_atual = transacao.data.month
        with transaction.atomic():
            transacao.delete()
        return redirect(f"/transacoes/?ano={ano_atual}&mes={mes_atual}")
    ano_atual = transacao.data.year
    mes_atual = transacao.data.month
    return redirect(f"/transacoes/?ano={ano_atual}&mes={mes_atual}")


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
