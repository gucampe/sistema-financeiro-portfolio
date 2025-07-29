from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import Categoria

@login_required
def categorias_view(request):
    categorias = Categoria.objects.filter(usuario=request.user)
    return render(request, "categorias/home.html", {
        "categorias": categorias
    })

@login_required
def adicionar_categoria(request):
    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()

        if not nome:
            return JsonResponse(
                {"status": "erro", "errors": {"nome": "O nome é obrigatório"}},
                status=400
            )

        # Cria a categoria associada ao usuário
        Categoria.objects.create(usuario=request.user, nome=nome)

        return JsonResponse({"status": "ok"})

    return JsonResponse(
        {"status": "erro", "errors": "Método inválido"},
        status=405
    )
