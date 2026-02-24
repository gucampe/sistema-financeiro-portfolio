# categorias/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError

from .models import Categoria
from .defaults import ICONES_DISPONIVEIS


@login_required
def categorias_view(request):
    categorias_despesa = Categoria.objects.filter(usuario=request.user, tipo="despesa").order_by("nome")
    categorias_receita = Categoria.objects.filter(usuario=request.user, tipo="receita").order_by("nome")

    return render(request, "categorias/home.html", {
        "categorias_despesa": categorias_despesa,
        "categorias_receita": categorias_receita,
        "icones": ICONES_DISPONIVEIS,        # lista de strings: "fa-home", "fa-car", ...
        "cores": Categoria.CORES_CHOICES,
        "tipos": Categoria.TIPO_CHOICES,
    })


@login_required
def adicionar_categoria(request):
    if request.method != "POST" or request.headers.get("x-requested-with") != "XMLHttpRequest":
        return JsonResponse({"status": "erro", "errors": "Método inválido"}, status=405)

    categoria_id = request.POST.get("categoria_id")
    nome = (request.POST.get("nome") or "").strip()
    icone = request.POST.get("icone") or "fa-ellipsis-h"
    cor = request.POST.get("cor") or "#4F46E5"
    tipo = request.POST.get("tipo") or "despesa"

    if not nome:
        return JsonResponse({"status": "erro", "errors": "Nome é obrigatório"}, status=400)

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
def excluir_categoria(request, id):
    if request.method != "POST" or request.headers.get("x-requested-with") != "XMLHttpRequest":
        return JsonResponse({"status": "error", "error": "Requisição inválida"}, status=400)

    categoria = get_object_or_404(Categoria, pk=id, usuario=request.user)
    categoria.delete()
    return JsonResponse({"status": "ok"})