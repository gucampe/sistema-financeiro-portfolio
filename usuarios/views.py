from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods
from django.urls import reverse, reverse_lazy
from django.conf import settings

from usuarios.audit import registrar_audit
from usuarios.models import AuditLog, LeadPrimeirosDonos
from usuarios.services.onboarding import progresso_primeiros_passos
from relatorios.models import ExportJob

from .forms import (
    CapturaLeadForm,
    ConfiguracoesPasswordChangeForm,
    DadosPessoaisForm,
    PreferenciasFinanceirasForm,
)
from .models import Perfil, Usuario
from .utils import iniciais_avatar


WHATSAPP_SUPORTE = "11931496081"
WHATSAPP_SUPORTE_DISPLAY = "(11) 93149-6081"


def _legal_context(request=None):
    site_url = getattr(settings, "SITE_URL", "") or (
        request.build_absolute_uri("/") if request is not None else ""
    )
    return {
        "privacidade_email": getattr(settings, "PRIVACIDADE_EMAIL", "privacidade@granago.com.br"),
        "contato_email": getattr(settings, "CONTATO_EMAIL", "ola@granago.com.br"),
        "llm_ativo": getattr(settings, "ENABLE_CATEGORIZACAO_LLM", False),
        "checkout_url": getattr(settings, "LANDING_CHECKOUT_URL", "") or reverse("usuarios:landing") + "#garantir-vaga",
        "site_url": site_url.rstrip("/"),
        "app_login_url": getattr(settings, "APP_LOGIN_URL", "") or reverse("usuarios:login"),
        "whatsapp_suporte": WHATSAPP_SUPORTE,
        "whatsapp_suporte_display": WHATSAPP_SUPORTE_DISPLAY,
        "whatsapp_suporte_url": f"https://wa.me/55{WHATSAPP_SUPORTE}",
    }


def _landing_context(request):
    ctx = _legal_context(request)
    ctx["captura_form"] = CapturaLeadForm()
    return ctx


def _institucional_context(request, nav_current=""):
    ctx = _legal_context(request)
    ctx["nav_current"] = nav_current
    return ctx


def home_view(request):
    return render(request, "institucional/home.html", _institucional_context(request, "home"))


def nossa_historia_view(request):
    return render(
        request,
        "institucional/nossa_historia.html",
        _institucional_context(request, "historia"),
    )


def como_funciona_view(request):
    return render(
        request,
        "institucional/como_funciona.html",
        _institucional_context(request, "como_funciona"),
    )


def faq_view(request):
    return render(request, "institucional/faq.html", _institucional_context(request, "faq"))


def robots_txt(request):
    site = _legal_context(request)["site_url"]
    body = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /obrigado/",
            "Disallow: /captura/",
            "Disallow: /admin/",
            "",
            f"Sitemap: {site}/sitemap.xml",
            "",
        ]
    )
    return HttpResponse(body, content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    site = _legal_context(request)["site_url"]
    paths = [
        "/",
        "/nossa-historia/",
        "/como-funciona/",
        "/faq/",
        "/politica-de-privacidade/",
        "/termos-de-uso/",
        "/comece/",
    ]
    urls = "\n".join(
        f"  <url><loc>{site}{path}</loc></url>" for path in paths
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n"
        "</urlset>\n"
    )
    return HttpResponse(xml, content_type="application/xml")


@never_cache
def landing_view(request):
    if request.user.is_authenticated:
        return redirect("relatorios:home")
    return render(request, "landing/landing.html", _landing_context(request))


@require_http_methods(["POST"])
def captura_lead_view(request):
    if request.user.is_authenticated:
        return redirect("relatorios:home")

    form = CapturaLeadForm(request.POST)
    if form.is_valid():
        email = form.cleaned_data["email"]
        LeadPrimeirosDonos.objects.update_or_create(
            email=email,
            defaults={
                "nome": form.cleaned_data["nome"],
                "whatsapp": form.cleaned_data["whatsapp"],
            },
        )
        request.session["captura_lead_nome"] = form.cleaned_data["nome"]
        request.session["captura_lead_email"] = email
        return redirect("usuarios:obrigado")

    ctx = _landing_context(request)
    ctx["captura_form"] = form
    ctx["abrir_modal_captura"] = True
    return render(request, "landing/landing.html", ctx, status=400)


@never_cache
@require_GET
def obrigado_view(request):
    if request.user.is_authenticated:
        return redirect("relatorios:home")

    ctx = _landing_context(request)
    ctx["lead_nome"] = request.session.get("captura_lead_nome", "")
    ctx["lead_email"] = request.session.get("captura_lead_email", "")
    return render(request, "landing/obrigado.html", ctx)


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

    return render(request, "usuarios/partials/login.html", _legal_context(request))


def privacidade_view(request):
    return render(request, "usuarios/legal/privacidade.html", _legal_context(request))


def termos_view(request):
    return render(request, "usuarios/legal/termos.html", _legal_context(request))


class GranaGoPasswordResetView(PasswordResetView):
    template_name = "usuarios/legal/password_reset_form.html"
    email_template_name = "usuarios/legal/password_reset_email.html"
    subject_template_name = "usuarios/legal/password_reset_subject.txt"
    success_url = reverse_lazy("usuarios:password_reset_done")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if "email" in form.fields:
            form.fields["email"].widget.attrs.update({"class": "input w-full"})
        return form


class GranaGoPasswordResetDoneView(PasswordResetDoneView):
    template_name = "usuarios/legal/password_reset_done.html"


class GranaGoPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "usuarios/legal/password_reset_confirm.html"
    success_url = reverse_lazy("usuarios:password_reset_complete")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs.update({"class": "input w-full pr-10", "autocomplete": "new-password"})
        return form


class GranaGoPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "usuarios/legal/password_reset_complete.html"


def _configuracoes_context(request, perfil=None, dados_form=None, pref_form=None, senha_form=None):
    usuario = Usuario.objects.get(pk=request.user.pk)
    perfil = perfil or Perfil.objects.get_or_create(usuario=usuario)[0]
    dados_form = dados_form or DadosPessoaisForm(instance=usuario, user=usuario)
    pref_form = pref_form or PreferenciasFinanceirasForm(instance=perfil, user=usuario)
    senha_form = senha_form or ConfiguracoesPasswordChangeForm(usuario)
    foto_url = perfil.foto.url if perfil.foto else None
    return {
        "usuario": usuario,
        "dados_form": dados_form,
        "pref_form": pref_form,
        "senha_form": senha_form,
        "perfil": perfil,
        "foto_url": foto_url,
        "iniciais_avatar": iniciais_avatar(usuario.nome),
    }


@login_required
@never_cache
def configuracoes(request):
    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)

    if request.method == "POST":
        form_tipo = request.POST.get("form")
        if form_tipo == "dados_pessoais":
            usuario = Usuario.objects.get(pk=request.user.pk)
            fd = DadosPessoaisForm(
                request.POST,
                request.FILES,
                instance=usuario,
                user=usuario,
            )
            if fd.is_valid():
                usuario = fd.save()
                usuario.refresh_from_db()
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
        registrar_audit(
            acao=AuditLog.ACAO_PASSWORD_CHANGE,
            usuario=user,
            request=request,
        )
        messages.success(request, "Senha alterada com sucesso.")
        return redirect(f"{reverse('usuarios:configuracoes')}#seguranca")

    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
    return render(
        request,
        "usuarios/configuracoes/configuracoes.html",
        _configuracoes_context(request, perfil=perfil, senha_form=form),
    )


@login_required
@never_cache
def primeiros_passos(request):
    """Central de configuração inicial — página dedicada."""
    return render(
        request,
        "usuarios/primeiros_passos/primeiros_passos.html",
        {"primeiros_passos": progresso_primeiros_passos(request.user)},
    )


@login_required
@require_GET
def primeiros_passos_status(request):
    """Status JSON do checklist — atualização client-side sem reload."""
    return JsonResponse(progresso_primeiros_passos(request.user))


def _limpar_arquivos_usuario(usuario):
    import shutil
    from pathlib import Path

    from relatorios.models import ExportJob

    for job in ExportJob.objects.filter(usuario=usuario):
        if job.arquivo:
            try:
                job.arquivo.delete(save=False)
            except Exception:
                pass
    perfil = getattr(usuario, "perfil", None)
    if perfil and perfil.foto:
        try:
            perfil.foto.delete(save=False)
        except Exception:
            pass
    media_root = Path(settings.MEDIA_ROOT)
    export_dir = media_root / "exports" / str(usuario.pk)
    if export_dir.exists():
        shutil.rmtree(export_dir, ignore_errors=True)
    foto_dir = media_root / "perfis" / "fotos"
    if perfil and perfil.foto and perfil.foto.name:
        try:
            (media_root / perfil.foto.name).unlink(missing_ok=True)
        except Exception:
            pass


@login_required
@never_cache
def excluir_conta(request):
    if request.method == "POST":
        senha = request.POST.get("senha") or ""
        confirmo = request.POST.get("confirmo")
        if not confirmo or not request.user.check_password(senha):
            messages.error(request, "Confirme sua senha e o entendimento sobre exclusão permanente.")
            return render(request, "usuarios/configuracoes/excluir_conta.html")

        user = request.user
        user_id = user.pk
        registrar_audit(
            acao=AuditLog.ACAO_DELETE_ACCOUNT,
            usuario=user,
            request=request,
        )
        _limpar_arquivos_usuario(user)
        ExportJob.objects.filter(usuario=user).update(status=ExportJob.STATUS_CANCELLED)
        try:
            cache.delete_many([f"export_rate:{user_id}", f"ia_batch_rl:{user_id}"])
        except Exception:
            pass
        with transaction.atomic():
            user.delete()
        logout(request)
        messages.success(request, "Sua conta foi excluída permanentemente.")
        return redirect("usuarios:login")

    return render(request, "usuarios/configuracoes/excluir_conta.html")
