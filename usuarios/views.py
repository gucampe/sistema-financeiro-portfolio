from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages

def login_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        senha = request.POST.get('senha')

        usuario = authenticate(request, email=email, password=senha)

        if usuario is not None:
            login(request, usuario)
            return redirect('dashboard:home')  # substitua 'home' pelo nome da sua URL da página principal
        else:
            messages.error(request, "E-mail ou senha inválidos.")
            return redirect('usuarios:login')  # substitua se necessário

    return render(request, 'usuarios/partials/login.html')
