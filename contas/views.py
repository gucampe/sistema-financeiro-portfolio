from decimal import Decimal, InvalidOperation

from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db.models import Case, DecimalField, F, OuterRef, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from categorias.models import Categoria
from transacoes.models import Transacao
from .models import Conta


def _contas_queryset_com_saldo(usuario, *, ativa=None):
    """Queryset de Conta filtrado por usuario (e opcionalmente ativa) com saldo_atual anotado."""
    saldo_subquery = (
        Transacao.objects.filter(conta_id=OuterRef("pk"), usuario=usuario)
        .values("conta_id")
        .annotate(
            total=Sum(
                Case(
                    When(tipo="receita", then=F("valor")),
                    When(tipo="despesa", then=-F("valor")),
                    When(tipo="ajuste", then=F("valor")),
                    default=Value(Decimal("0.00")),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            )
        )
        .values("total")
    )
    qs = Conta.objects.filter(usuario=usuario)
    if ativa is not None:
        qs = qs.filter(ativa=ativa)
    return qs.annotate(
        saldo_atual=Coalesce(
            Subquery(saldo_subquery[:1]),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    ).order_by("nome")


@login_required
def contas_home(request):
    contas_ativas = _contas_queryset_com_saldo(request.user, ativa=True)
    contas_arquivadas = _contas_queryset_com_saldo(request.user, ativa=False)
    icone_choices_instituicoes = [
        "nubank", "itau", "santander", "bradesco", "bb", "caixa",
        "inter", "sicredi", "sicoob", "picpay", "mercadopago",
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
    # slug -> nome do arquivo (quando diferente do slug, ex.: inter -> intermedium.png)
    icon_filename_instituicoes = {"inter": "intermedium"}
    icon_list_instituicoes = [
        (s, icon_display_names.get(s, s), icon_filename_instituicoes.get(s, s))
        for s in icone_choices_instituicoes
    ]
    icon_list_genericos = [(s, icon_display_names.get(s, s), s) for s in icone_choices_genericos]
    return render(
        request,
        "contas/home.html",
        {
            "contas_ativas": contas_ativas,
            "contas_arquivadas": contas_arquivadas,
            "tipo_choices": Conta.TIPO_CHOICES,
            "icone_choices_instituicoes": icone_choices_instituicoes,
            "icone_choices_genericos": icone_choices_genericos,
            "icon_list_instituicoes": icon_list_instituicoes,
            "icon_list_genericos": icon_list_genericos,
        },
    )


@login_required
def salvar_conta(request):
    if request.method != "POST" or request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return JsonResponse({"status": "erro", "errors": "Método inválido"}, status=405)

    conta_id = request.POST.get("conta_id")
    nome = (request.POST.get("nome") or "").strip()
    tipo = (request.POST.get("tipo") or "").strip()
    icone = (request.POST.get("icone") or "bank").strip() or "bank"
    saldo_inicial_raw = (request.POST.get("saldo_inicial") or "0").strip()

    if not nome:
        return JsonResponse({"status": "erro", "errors": "Nome é obrigatório"}, status=400)

    tipos_validos = {t[0] for t in Conta.TIPO_CHOICES}
    if tipo not in tipos_validos:
        return JsonResponse({"status": "erro", "errors": "Tipo inválido"}, status=400)

    saldo_inicial = Decimal("0.00")
    if not conta_id:
        # Saldo inicial só é considerado na criação
        try:
            normalizado = saldo_inicial_raw.replace(".", "").replace(",", ".")
            saldo_inicial = Decimal(normalizado)
        except (InvalidOperation, ValueError, TypeError):
            saldo_inicial = Decimal("0.00")

    try:
        if conta_id:
            conta = get_object_or_404(Conta, id=conta_id, usuario=request.user)
            conta.nome = nome
            conta.tipo = tipo
            conta.icone = icone
            conta.save(update_fields=["nome", "tipo", "icone", "atualizada_em"])
        else:
            if Conta.objects.filter(usuario=request.user, nome=nome).exists():
                return JsonResponse(
                    {"status": "erro", "errors": "Você já possui uma conta com esse nome."},
                    status=409,
                )
            conta = Conta.objects.create(
                usuario=request.user,
                nome=nome,
                tipo=tipo,
                icone=icone,
            )
            if saldo_inicial != Decimal("0.00"):
                # cria transação de ajuste automática
                hoje = timezone.now().date()
                # tenta achar/ criar categoria padrão para ajustes
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
                Transacao.objects.create(
                    usuario=request.user,
                    conta=conta,
                    tipo="ajuste",
                    valor=saldo_inicial,
                    descricao="Saldo inicial",
                    data=hoje,
                    categoria=categoria_ajuste,
                )
        return JsonResponse(
            {
                "status": "ok",
                "id": conta.id,
                "nome": conta.nome,
                "tipo": conta.tipo,
                "tipo_display": conta.get_tipo_display(),
                "icone": conta.icone,
                "saldo": str(conta.saldo_atual_calc),
                "ativa": conta.ativa,
            }
        )
    except Exception as e:
        return JsonResponse({"status": "erro", "errors": str(e)}, status=500)


@login_required
@require_POST
def arquivar_conta(request, id):
    conta = get_object_or_404(Conta, id=id, usuario=request.user)
    conta.ativa = False
    conta.save(update_fields=["ativa", "atualizada_em"])
    return redirect("contas:home")


@login_required
@require_POST
def reativar_conta(request, id):
    conta = get_object_or_404(Conta, id=id, usuario=request.user)
    conta.ativa = True
    conta.save(update_fields=["ativa", "atualizada_em"])
    return redirect("contas:home")
