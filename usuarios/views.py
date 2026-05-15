from django.contrib import messages
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import (
    ConfiguracoesPasswordChangeForm,
    DadosPessoaisForm,
    PreferenciasFinanceirasForm,
)
from .models import Perfil
from .utils import iniciais_avatar


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        senha = request.POST.get("senha")

        usuario = authenticate(request, email=email, password=senha)

        if usuario is not None:
            login(request, usuario)
            return redirect("relatorios:home")
        messages.error(request, "E-mail ou senha inválidos.")
        return redirect("usuarios:login")

    return render(request, "usuarios/partials/login.html")


def _configuracoes_context(request, perfil=None, dados_form=None, pref_form=None, senha_form=None):
    perfil = perfil or Perfil.objects.get_or_create(usuario=request.user)[0]
    dados_form = dados_form or DadosPessoaisForm(instance=request.user, user=request.user)
    pref_form = pref_form or PreferenciasFinanceirasForm(instance=perfil, user=request.user)
    senha_form = senha_form or ConfiguracoesPasswordChangeForm(request.user)
    foto_url = perfil.foto.url if perfil.foto else None
    return {
        "dados_form": dados_form,
        "pref_form": pref_form,
        "senha_form": senha_form,
        "perfil": perfil,
        "foto_url": foto_url,
        "iniciais_avatar": iniciais_avatar(request.user.nome),
    }


@login_required
def configuracoes(request):
    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)

    if request.method == "POST":
        form_tipo = request.POST.get("form")
        if form_tipo == "dados_pessoais":
            fd = DadosPessoaisForm(
                request.POST,
                request.FILES,
                instance=request.user,
                user=request.user,
            )
            if fd.is_valid():
                fd.save()
                foto = fd.cleaned_data.get("foto")
                if foto:
                    perfil.foto = foto
                    perfil.save(update_fields=["foto"])
                messages.success(request, "Dados pessoais atualizados com sucesso.")
                return redirect(f"{reverse('usuarios:configuracoes')}#perfil")
            return render(
                request,
                "usuarios/configuracoes/configuracoes.html",
                _configuracoes_context(request, perfil=perfil, dados_form=fd),
            )
        if form_tipo == "preferencias":
            fp = PreferenciasFinanceirasForm(
                request.POST,
                instance=perfil,
                user=request.user,
            )
            if fp.is_valid():
                fp.save()
                messages.success(request, "Preferências salvas com sucesso.")
                return redirect(f"{reverse('usuarios:configuracoes')}#preferencias")
            return render(
                request,
                "usuarios/configuracoes/configuracoes.html",
                _configuracoes_context(request, perfil=perfil, pref_form=fp),
            )

    return render(
        request,
        "usuarios/configuracoes/configuracoes.html",
        _configuracoes_context(request, perfil=perfil),
    )


@login_required
def configuracoes_alterar_senha(request):
    if request.method != "POST":
        return redirect("usuarios:configuracoes")

    form = ConfiguracoesPasswordChangeForm(request.user, request.POST)
    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Senha alterada com sucesso.")
        return redirect(f"{reverse('usuarios:configuracoes')}#seguranca")

    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
    return render(
        request,
        "usuarios/configuracoes/configuracoes.html",
        _configuracoes_context(request, perfil=perfil, senha_form=form),
    )
