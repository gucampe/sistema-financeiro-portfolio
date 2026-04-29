from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from contas.models import Conta
from transacoes.models import Transacao
from transacoes.views import modal_transacao_context

from .models import Cartao, Fatura
from .services.gestao_faturas import (
    atualizar_status_pagamento,
    mover_lancamento,
    pagar_fatura,
)


def _faturas_ordenadas_por_competencia(cartao, usuario):
    return list(
        Fatura.objects.filter(cartao=cartao, usuario=usuario).order_by("competencia", "data_vencimento", "id")
    )


def _fatura_adj_por_direcao(*, cartao, usuario, fatura_atual, direcao):
    faturas = _faturas_ordenadas_por_competencia(cartao, usuario)
    try:
        idx = next(i for i, f in enumerate(faturas) if f.pk == fatura_atual.pk)
    except StopIteration:
        return None
    if direcao == "anterior":
        destino_idx = idx - 1
    elif direcao == "proxima":
        destino_idx = idx + 1
    else:
        return None
    if destino_idx < 0 or destino_idx >= len(faturas):
        return None
    return faturas[destino_idx]


@login_required
def cartoes_home(request):
    cartoes = (
        Cartao.objects.filter(usuario=request.user, ativa=True)
        .select_related("conta_padrao")
        .order_by("nome")
    )
    contas_ativas = Conta.objects.filter(usuario=request.user, ativa=True).order_by("nome")

    icone_choices_instituicoes = [
        "nubank",
        "itau",
        "santander",
        "bradesco",
        "bb",
        "caixa",
        "inter",
        "sicredi",
        "sicoob",
        "picpay",
        "mercadopago",
    ]
    icone_choices_genericos = ["bank", "wallet", "cash", "piggy", "building", "briefcase"]
    icon_display_names = {
        "nubank": "Nubank",
        "itau": "Itaú",
        "santander": "Santander",
        "bradesco": "Bradesco",
        "bb": "Banco do Brasil",
        "caixa": "Caixa",
        "inter": "Inter",
        "sicredi": "Sicredi",
        "sicoob": "Sicoob",
        "picpay": "PicPay",
        "mercadopago": "Mercado Pago",
        "bank": "Banco",
        "wallet": "Carteira",
        "cash": "Dinheiro",
        "piggy": "Cofrinho",
        "building": "Empresa",
        "briefcase": "Maleta",
    }
    icon_filename_instituicoes = {"inter": "intermedium"}
    icon_list_instituicoes = [
        (s, icon_display_names.get(s, s), icon_filename_instituicoes.get(s, s))
        for s in icone_choices_instituicoes
    ]
    icon_list_genericos = [(s, icon_display_names.get(s, s), s) for s in icone_choices_genericos]

    return render(
        request,
        "cartoes/home.html",
        {
            "cartoes": cartoes,
            "contas_ativas": contas_ativas,
            "icone_choices_instituicoes": icone_choices_instituicoes,
            "icone_choices_genericos": icone_choices_genericos,
            "icon_list_instituicoes": icon_list_instituicoes,
            "icon_list_genericos": icon_list_genericos,
        },
    )


@login_required
def salvar_cartao(request):
    if request.method != "POST" or request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return JsonResponse({"status": "erro", "errors": "Método inválido"}, status=405)

    cartao_id = request.POST.get("cartao_id")
    nome = (request.POST.get("nome") or "").strip()
    icone = (request.POST.get("icone") or "bank").strip() or "bank"
    limite_raw = (request.POST.get("limite") or "0").strip()
    dia_fechamento_raw = (request.POST.get("dia_fechamento") or "").strip()
    dia_vencimento_raw = (request.POST.get("dia_vencimento") or "").strip()
    conta_padrao_id = (request.POST.get("conta_padrao") or "").strip()

    if not nome:
        return JsonResponse({"status": "erro", "errors": "Nome é obrigatório"}, status=400)
    if not conta_padrao_id:
        return JsonResponse({"status": "erro", "errors": "Conta padrão é obrigatória"}, status=400)

    try:
        limite = Decimal(limite_raw.replace(".", "").replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return JsonResponse({"status": "erro", "errors": "Limite inválido"}, status=400)

    try:
        dia_fechamento = int(dia_fechamento_raw)
        dia_vencimento = int(dia_vencimento_raw)
    except (TypeError, ValueError):
        return JsonResponse({"status": "erro", "errors": "Dias devem ser numéricos"}, status=400)

    if not (1 <= dia_fechamento <= 31) or not (1 <= dia_vencimento <= 31):
        return JsonResponse({"status": "erro", "errors": "Dias devem estar entre 1 e 31"}, status=400)

    conta_padrao = get_object_or_404(Conta, id=conta_padrao_id, usuario=request.user, ativa=True)

    try:
        if cartao_id:
            cartao = get_object_or_404(Cartao, id=cartao_id, usuario=request.user, ativa=True)
            cartao.nome = nome
            cartao.icone = icone
            cartao.limite = limite
            cartao.dia_fechamento = dia_fechamento
            cartao.dia_vencimento = dia_vencimento
            cartao.conta_padrao = conta_padrao
            cartao.save(
                update_fields=[
                    "nome",
                    "icone",
                    "limite",
                    "dia_fechamento",
                    "dia_vencimento",
                    "conta_padrao",
                    "atualizada_em",
                ]
            )
        else:
            if Cartao.objects.filter(usuario=request.user, nome=nome).exists():
                return JsonResponse(
                    {"status": "erro", "errors": "Você já possui um cartão com esse nome."},
                    status=409,
                )
            cartao = Cartao.objects.create(
                usuario=request.user,
                nome=nome,
                icone=icone,
                limite=limite,
                dia_fechamento=dia_fechamento,
                dia_vencimento=dia_vencimento,
                conta_padrao=conta_padrao,
            )

        return JsonResponse(
            {
                "status": "ok",
                "id": cartao.id,
                "nome": cartao.nome,
                "icone": cartao.icone,
                "limite": str(cartao.limite),
                "dia_fechamento": cartao.dia_fechamento,
                "dia_vencimento": cartao.dia_vencimento,
                "conta_padrao_id": cartao.conta_padrao_id,
                "conta_padrao_nome": cartao.conta_padrao.nome,
            }
        )
    except Exception as exc:
        return JsonResponse({"status": "erro", "errors": str(exc)}, status=500)


@login_required
@require_POST
def excluir_cartao(request, id):
    cartao = get_object_or_404(Cartao, id=id, usuario=request.user, ativa=True)
    cartao.ativa = False
    cartao.save(update_fields=["ativa", "atualizada_em"])
    return JsonResponse({"status": "ok", "id": id})


@login_required
def faturas_cartao(request, cartao_id):
    cartao = get_object_or_404(Cartao, pk=cartao_id, usuario=request.user, ativa=True)
    faturas = (
        Fatura.objects.filter(cartao=cartao, usuario=request.user)
        .annotate(total_despesas=Sum("lancamentos__valor", filter=Q(lancamentos__tipo="despesa")))
        .order_by("-competencia")
    )
    for f in faturas:
        atualizar_status_pagamento(f)
    hoje = timezone.localdate()
    fatura_destaque = (
        Fatura.objects.filter(
            cartao=cartao,
            usuario=request.user,
            data_inicio_compras__lte=hoje,
            data_fim_compras__gte=hoje,
        ).order_by("-competencia")
        .first()
    )
    if fatura_destaque is None:
        fatura_destaque = faturas.first()

    total_destaque = None
    if fatura_destaque is not None:
        total_destaque = (
            Transacao.objects.filter(
                usuario=request.user, fatura=fatura_destaque, tipo="despesa"
            ).aggregate(s=Sum("valor"))["s"]
            or Decimal("0")
        )

    ctx = {
        "cartao": cartao,
        "faturas": faturas,
        "fatura_destaque": fatura_destaque,
        "total_destaque": total_destaque,
    }
    ctx.update(modal_transacao_context(request, pre_select_cartao_id=cartao.id))
    return render(request, "cartoes/faturas_cartao.html", ctx)


@login_required
def fatura_detalhe(request, cartao_id, fatura_id):
    cartao = get_object_or_404(Cartao, pk=cartao_id, usuario=request.user, ativa=True)
    fatura = get_object_or_404(Fatura, pk=fatura_id, cartao=cartao, usuario=request.user)
    lancamentos = (
        Transacao.objects.filter(usuario=request.user, fatura=fatura)
        .select_related("categoria", "conta", "cartao")
        .order_by("-data", "-id")
    )
    total = (
        Transacao.objects.filter(usuario=request.user, fatura=fatura, tipo="despesa").aggregate(
            s=Sum("valor")
        )["s"]
        or Decimal("0")
    )
    resumo_pagamento = atualizar_status_pagamento(fatura)
    faturas = _faturas_ordenadas_por_competencia(cartao, request.user)
    faturas_destino = [f for f in faturas if f.pk != fatura.pk]
    fatura_anterior = _fatura_adj_por_direcao(
        cartao=cartao,
        usuario=request.user,
        fatura_atual=fatura,
        direcao="anterior",
    )
    fatura_proxima = _fatura_adj_por_direcao(
        cartao=cartao,
        usuario=request.user,
        fatura_atual=fatura,
        direcao="proxima",
    )
    ctx = {
        "cartao": cartao,
        "fatura": fatura,
        "lancamentos": lancamentos,
        "total_despesas": total,
        "faturas_destino": faturas_destino,
        "fatura_proxima": fatura_proxima,
        "fatura_anterior": fatura_anterior,
        "valor_pago": resumo_pagamento.pago,
        "saldo_restante": resumo_pagamento.saldo,
        "status_pagamento": resumo_pagamento.status_pagamento,
    }
    ctx.update(modal_transacao_context(request, pre_select_cartao_id=cartao.id))
    return render(request, "cartoes/fatura_detalhe.html", ctx)


@login_required
@require_POST
def pagar_fatura_view(request, cartao_id, fatura_id):
    cartao = get_object_or_404(Cartao, pk=cartao_id, usuario=request.user, ativa=True)
    fatura = get_object_or_404(Fatura, pk=fatura_id, cartao=cartao, usuario=request.user)
    valor_raw = (request.POST.get("valor") or "").strip().replace(".", "").replace(",", ".")
    valor = None
    if valor_raw:
        try:
            valor = Decimal(valor_raw)
        except (InvalidOperation, ValueError):
            return JsonResponse({"status": "erro", "errors": "Valor inválido."}, status=400)
    try:
        pagar_fatura(fatura=fatura, valor=valor)
    except ValidationError as exc:
        return JsonResponse({"status": "erro", "errors": exc.messages[0]}, status=400)
    return redirect("cartoes:fatura_detalhe", cartao_id=cartao.id, fatura_id=fatura.id)


@login_required
@require_POST
def mover_lancamento_fatura_view(request, cartao_id, fatura_id, transacao_id):
    cartao = get_object_or_404(Cartao, pk=cartao_id, usuario=request.user, ativa=True)
    fatura = get_object_or_404(Fatura, pk=fatura_id, cartao=cartao, usuario=request.user)
    transacao = get_object_or_404(
        Transacao,
        pk=transacao_id,
        usuario=request.user,
        fatura=fatura,
    )
    direcao = (request.POST.get("direcao") or "").strip().lower()
    if direcao in {"anterior", "proxima"}:
        fatura_destino = _fatura_adj_por_direcao(
            cartao=cartao,
            usuario=request.user,
            fatura_atual=fatura,
            direcao=direcao,
        )
        if fatura_destino is None:
            return JsonResponse({"status": "erro", "errors": "Não existe fatura disponível nessa direção."}, status=400)
    else:
        fatura_destino_id = request.POST.get("fatura_destino")
        fatura_destino = get_object_or_404(
            Fatura,
            pk=fatura_destino_id,
            usuario=request.user,
            cartao=cartao,
        )
    try:
        mover_lancamento(transacao=transacao, fatura_destino=fatura_destino)
    except ValidationError as exc:
        return JsonResponse({"status": "erro", "errors": exc.messages[0]}, status=400)
    return redirect("cartoes:fatura_detalhe", cartao_id=cartao.id, fatura_id=fatura.id)
