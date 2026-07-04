# categorias/views.py
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from .models import Categoria
from .defaults import ICONES_DISPONIVEIS


@login_required
def categorias_view(request):
    base = Categoria.objects.filter(usuario=request.user)
    categorias_ativas_despesa = base.filter(tipo="despesa", ativa=True).order_by("nome")
    categorias_ativas_receita = base.filter(tipo="receita", ativa=True).order_by("nome")
    categorias_arquivadas_despesa = base.filter(tipo="despesa", ativa=False).order_by("nome")
    categorias_arquivadas_receita = base.filter(tipo="receita", ativa=False).order_by("nome")

    return render(request, "categorias/home.html", {
        "categorias_ativas_despesa": categorias_ativas_despesa,
        "categorias_ativas_receita": categorias_ativas_receita,
        "categorias_arquivadas_despesa": categorias_arquivadas_despesa,
        "categorias_arquivadas_receita": categorias_arquivadas_receita,
        "icones": ICONES_DISPONIVEIS,
        "cores": Categoria.CORES_CHOICES,
        "tipos": Categoria.TIPO_CHOICES,
    })


@login_required
def adicionar_categoria(request):
    if request.method != "POST" or request.headers.get("x-requested-with") != "XMLHttpRequest":
        return JsonResponse({"status": "erro", "errors": "Método inválido"}, status=405)

    categoria_id = request.POST.get("categoria_id")
    nome = (request.POST.get("nome") or "").strip()
    icone = (request.POST.get("icone") or "fa-ellipsis-h").strip()
    cor = (request.POST.get("cor") or "#4F46E5").strip()
    tipo = request.POST.get("tipo") or "despesa"

    if not nome:
        return JsonResponse({"status": "erro", "errors": "Nome é obrigatório"}, status=400)

    icones_validos = set(ICONES_DISPONIVEIS)
    cores_validas = {c[0] for c in Categoria.CORES_CHOICES}
    if icone not in icones_validos:
        return JsonResponse({"status": "erro", "errors": "Ícone inválido"}, status=400)
    if cor not in cores_validas:
        return JsonResponse({"status": "erro", "errors": "Cor inválida"}, status=400)

    tipos_validos = {t[0] for t in Categoria.TIPO_CHOICES}
    if tipo not in tipos_validos:
        return JsonResponse({"status": "erro", "errors": "Tipo inválido"}, status=400)

    try:
        if categoria_id:
            # Edição (somente categorias do usuário)
            categoria = get_object_or_404(Categoria, id=categoria_id, usuario=request.user)
            categoria.nome = nome
            categoria.icone = icone
            categoria.cor = cor
            categoria.tipo = tipo
            categoria.save()

            return JsonResponse({
                "status": "ok",
                "id": categoria.id,
                "nome": categoria.nome,
                "icone": categoria.icone,
                "cor": categoria.cor,
                "tipo": categoria.tipo,
            })

        # Criação
        categoria = Categoria.objects.create(
            nome=nome,
            icone=icone,
            cor=cor,
            tipo=tipo,
            usuario=request.user,
            padrao=False,
        )

        return JsonResponse({
            "status": "ok",
            "id": categoria.id,
            "nome": categoria.nome,
            "icone": categoria.icone,
            "cor": categoria.cor,
            "tipo": categoria.tipo,
        })

    except IntegrityError:
        return JsonResponse({
            "status": "erro",
            "errors": "Você já possui uma categoria com esse nome para esse tipo."
        }, status=409)


@login_required
def restaurar_categoria(request):
    if request.method != "POST" or request.headers.get("x-requested-with") != "XMLHttpRequest":
        return JsonResponse({"status": "erro", "errors": "Método inválido"}, status=405)

    categoria_id = request.POST.get("categoria_id")
    if not categoria_id:
        return JsonResponse({"status": "erro", "errors": "categoria_id é obrigatório"}, status=400)

    categoria = get_object_or_404(Categoria, pk=categoria_id, usuario=request.user)
    categoria.ativa = True
    categoria.save(update_fields=["ativa"])
    return JsonResponse({"status": "ok", "id": categoria.id, "tipo": categoria.tipo})


@login_required
def arquivar_categoria(request):
    if request.method != "POST" or request.headers.get("x-requested-with") != "XMLHttpRequest":
        return JsonResponse({"status": "erro", "errors": "Método inválido"}, status=405)

    categoria_id = request.POST.get("categoria_id")
    if not categoria_id:
        return JsonResponse({"status": "erro", "errors": "categoria_id é obrigatório"}, status=400)

    categoria = get_object_or_404(Categoria, pk=categoria_id, usuario=request.user)
    categoria.ativa = False
    categoria.save(update_fields=["ativa"])
    return JsonResponse({"status": "ok", "id": categoria.id})


@login_required
def excluir_categoria(request, id):
    if request.method != "POST" or request.headers.get("x-requested-with") != "XMLHttpRequest":
        return JsonResponse({"status": "error", "error": "Requisição inválida"}, status=400)

    categoria = get_object_or_404(Categoria, pk=id, usuario=request.user)

    if categoria.ativa:
        return JsonResponse({
            "status": "blocked",
            "reason": "not_archived",
            "message": "Arquive a categoria antes de excluir definitivamente."
        }, status=400)

    from transacoes.models import Transacao
    count = Transacao.objects.filter(usuario=request.user, categoria=categoria).count()
    if count > 0:
        return JsonResponse({
            "status": "blocked",
            "reason": "in_use",
            "count": count,
            "message": f"Categoria possui {count} transação(ões). Use migração para transferir e excluir."
        }, status=400)

    categoria.delete()
    return JsonResponse({"status": "ok"})


@login_required
def verificar_exclusao_categoria(request, id):
    if request.method != "GET" or request.headers.get("x-requested-with") != "XMLHttpRequest":
        return JsonResponse({"status": "erro", "errors": "Método inválido"}, status=405)

    categoria = get_object_or_404(Categoria, pk=id, usuario=request.user)
    if categoria.ativa:
        return JsonResponse({"status": "erro", "errors": "Categoria não está arquivada"}, status=400)

    from transacoes.models import Transacao
    count = Transacao.objects.filter(usuario=request.user, categoria=categoria).count()
    return JsonResponse({"status": "ok", "count": count})


@login_required
def listar_categorias_ativas(request):
    tipo = request.GET.get("tipo", "despesa")
    # Transação "ajuste" usa categorias de receita no cadastro (ex.: saldo inicial).
    if tipo == "ajuste":
        tipo_filtro = "receita"
    elif tipo not in ("despesa", "receita"):
        return JsonResponse({"status": "erro", "errors": "Tipo inválido"}, status=400)
    else:
        tipo_filtro = tipo

    categorias = (
        Categoria.objects.filter(
            Q(usuario=request.user) | Q(padrao=True),
            tipo=tipo_filtro,
            ativa=True,
        )
        .order_by("nome")
        .values("id", "nome", "icone", "cor")
    )
    return JsonResponse({"status": "ok", "categorias": list(categorias)})


@login_required
def excluir_categoria_com_migracao(request):
    if request.method != "POST" or request.headers.get("x-requested-with") != "XMLHttpRequest":
        return JsonResponse({"status": "erro", "errors": "Método inválido"}, status=405)

    categoria_id = request.POST.get("categoria_id")
    nova_categoria_id = request.POST.get("nova_categoria_id")

    if not categoria_id or not nova_categoria_id:
        return JsonResponse({"status": "erro", "errors": "categoria_id e nova_categoria_id são obrigatórios"}, status=400)

    categoria = get_object_or_404(Categoria, pk=categoria_id, usuario=request.user)
    nova_categoria = get_object_or_404(Categoria, pk=nova_categoria_id, usuario=request.user)

    if categoria.ativa:
        return JsonResponse({"status": "erro", "errors": "Categoria deve estar arquivada"}, status=400)
    if nova_categoria.tipo != categoria.tipo:
        return JsonResponse({"status": "erro", "errors": "Nova categoria deve ser do mesmo tipo"}, status=400)
    if nova_categoria.id == categoria.id:
        return JsonResponse({"status": "erro", "errors": "Escolha uma categoria diferente"}, status=400)
    if not nova_categoria.ativa:
        return JsonResponse({"status": "erro", "errors": "Nova categoria deve estar ativa"}, status=400)

    from transacoes.models import Transacao
    Transacao.objects.filter(usuario=request.user, categoria=categoria).update(categoria=nova_categoria)
    categoria.delete()
    return JsonResponse({"status": "ok"})