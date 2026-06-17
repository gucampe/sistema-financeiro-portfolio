from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('usuarios.urls')),
    path(
        'dashboard/',
        RedirectView.as_view(pattern_name='relatorios:home', permanent=False),
        name='legacy_dashboard_redirect',
    ),
    path('', include('relatorios.urls')),
    path('transacoes/', include(('transacoes.urls', 'transacoes'), namespace='transacoes')),
    path('', include(('categorias.urls', 'categorias'))),
    path('contas/', include(('contas.urls', 'contas'), namespace='contas')),
    path('cartoes/', include(('cartoes.urls', 'cartoes'), namespace='cartoes')),
]

if getattr(settings, "SILKY_PYTHON_PROFILER", False):
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]

if "debug_toolbar" in settings.INSTALLED_APPS:
    urlpatterns = [
        path("__debug__/", include("debug_toolbar.urls")),
        *urlpatterns,
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
