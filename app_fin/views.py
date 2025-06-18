from django.shortcuts import render

# Create your views here.

def login(request):
    return render(request, 'app_fin/partials/login.html')

def cadastro(request):
    return render(request, 'app_fin/base/base.html')