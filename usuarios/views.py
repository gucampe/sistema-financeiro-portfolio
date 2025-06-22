from django.shortcuts import render, redirect
from .models import Usuario
from django import forms

# Create your views here.

class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nome', 'email', 'data_nascimento']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'email': forms.EmailInput(attrs={'class': 'input input-bordered w-full'}),
            'data_nascimento': forms.DateInput(attrs={'type': 'date', 'class': 'input input-bordered w-full'}),
        }

def cadastro_usuario(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('cadastro_usuario')
    else:
        form = UsuarioForm()
    return render(request, 'usuarios/partials/cadastro.html', {'form': form})

def login(request):
    return render(request, 'usuarios/partials/login.html')
