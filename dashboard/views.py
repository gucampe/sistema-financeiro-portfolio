from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required(login_url='usuarios:login')  
def dashboard_view(request):
    return render(request, 'dashboard/partials/index.html')
