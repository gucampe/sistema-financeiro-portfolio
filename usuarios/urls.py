from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import login_view

app_name = 'usuarios'

urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

]
