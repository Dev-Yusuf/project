from django.urls import path
from . import views

urlpatterns = [
    path('', views.history_list, name='history_list'),
    path('submit/', views.submit_history, name='submit_history'),
    path('<slug:slug>/', views.history_detail, name='history_detail'),
]
