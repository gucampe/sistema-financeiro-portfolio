from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('usuarios.urls')),
    path('', include('dashboard.urls')),
    path('transacoes/', include(('transacoes.urls', 'transacoes'), namespace='transacoes')),
    path('', include(('categorias.urls', 'categorias'))),
    path('contas/', include(('contas.urls', 'contas'), namespace='contas')),
    path(
        'configuracoes/',
        TemplateView.as_view(template_name='configuracoes/em_breve.html'),
        name='configuracoes',
    ),
]
