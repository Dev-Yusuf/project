from django.urls import path
from . import views

urlpatterns = [
    path('', views.all_words, name='words'),
    path('single-word/<slug:slug>/', views.singleword, name= 'single-word'),

]
