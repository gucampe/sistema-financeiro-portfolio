from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from contas.models import Conta

from .models import Cartao


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
