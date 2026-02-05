from django.urls import path
from . import views

urlpatterns = [
    path('', views.all_words, name='words'),
    path('single-word/<slug:slug>/', views.singleword, name='single-word'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('submit/', views.submit_word, name='submit_word'),
    path('my-contributions/', views.my_contributions, name='my_contributions'),
    path('word-exists/', views.word_exists, name='word_exists'),
]
