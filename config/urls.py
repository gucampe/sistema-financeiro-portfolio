from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from config.health_views import health

handler404 = "config.error_handlers.handler404"
handler403 = "config.error_handlers.handler403"
handler500 = "config.error_handlers.handler500"

urlpatterns = [
    path("health/", health, name="health"),
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
    path('categorizacao/', include(('categorizacao.urls', 'categorizacao'), namespace='categorizacao')),
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
elif getattr(settings, "PROTECT_MEDIA", False):
    from config.media_views import protected_media

    urlpatterns += [
        path("media/<path:path>", protected_media, name="protected_media"),
    ]

if settings.DEBUG and getattr(settings, "ENABLE_BENCHMARK_ROUTES", False):
    from config import benchmark_views

    urlpatterns += [
        path("__benchmark/ping/", benchmark_views.ping, name="benchmark_ping"),
        path("__benchmark/ping-auth/", benchmark_views.ping_auth, name="benchmark_ping_auth"),
        path("__benchmark/ping-template/", benchmark_views.ping_template, name="benchmark_ping_template"),
        path("__benchmark/ping-db/", benchmark_views.ping_db, name="benchmark_ping_db"),
    ]
