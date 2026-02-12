from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from .models import Categoria
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

@login_required
def categorias_view(request):
    categorias = Categoria.objects.filter(usuario=request.user) | Categoria.objects.filter(padrao=True)
    return render(request, "categorias/home.html", {
        "categorias": categorias,
        "icones": Categoria.ICONES_CHOICES,
        "cores": Categoria.CORES_CHOICES,
    })


@login_required
def adicionar_categoria(request):
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":

        categoria_id = request.POST.get("categoria_id")
        nome = request.POST.get("nome")
        icone = request.POST.get("icone")
        cor = request.POST.get("cor")

        if categoria_id:
            # Edição
            categoria = Categoria.objects.get(id=categoria_id)
            categoria.nome = nome
            categoria.icone = icone
            categoria.cor = cor
            categoria.save()
            return JsonResponse({
                "status": "ok",
                "id": categoria.id,
                "nome": categoria.nome,
                "icone": categoria.icone,
                "cor": categoria.cor
            })
        else:
            # Criação
            categoria = Categoria.objects.create(
                nome=nome,
                icone=icone,
                cor=cor,
                usuario=request.user
            )
            return JsonResponse({
                "status": "ok",
                "id": categoria.id,
                "nome": categoria.nome,
                "icone": categoria.icone,
                "cor": categoria.cor
            })


    return JsonResponse({"status": "erro", "errors": "Método inválido"}, status=405)

@login_required
def excluir_categoria(request, id):
    # Aceita apenas requisições AJAX via POST
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        try:
            categoria = get_object_or_404(Categoria, pk=id, usuario=request.user)
            categoria.delete()
            return JsonResponse({"status": "ok"})
        except Exception as e:
            return JsonResponse({"status": "error", "error": str(e)})
    return JsonResponse({"status": "error", "error": "Requisição inválida"})
