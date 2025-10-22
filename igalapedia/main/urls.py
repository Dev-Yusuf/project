from django.urls import path
from . import views

urlpatterns = [
    path('', views.mainpage, name='index'),
    path('about/', views.about, name='about'),
    path('translator/', views.translator, name='translator'),
    path('api/', views.api_docs, name='api'),
    path('pioneers/', views.pioneers_page, name='pioneers'),
    
    # Authentication URLs
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.user_dashboard, name='dashboard'),
]
