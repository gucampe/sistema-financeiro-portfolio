from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('usuarios.urls')),
    path('', include('dashboard.urls')),
    path('transacoes/', include(('transacoes.urls', 'transacoes'), namespace='transacoes')),
    path('', include(('categorias.urls', 'categorias'))),
    path('contas/', include(('contas.urls', 'contas'), namespace='contas')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
