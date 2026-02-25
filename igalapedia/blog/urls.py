from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.blog_list, name='blog_list'),
    path('guidelines/', views.blog_guidelines, name='blog_guidelines'),
    path('create/', views.blog_create, name='blog_create'),
    path('<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('<slug:slug>/edit/', views.blog_edit, name='blog_edit'),
    path('<slug:slug>/delete/', views.blog_delete, name='blog_delete'),
    path('<slug:slug>/like/', views.blog_like_toggle, name='blog_like_toggle'),
    path('<slug:slug>/comment/', views.blog_comment_add, name='blog_comment_add'),
    path('<slug:slug>/report/', views.blog_report, name='blog_report'),
]
