from django.urls import path
from . import views

app_name = 'music'
urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search, name='search'),
    path('artists/', views.artists, name='artists'),
    path('artists/<slug:slug>/', views.artist, name='artist'),
    path('releases/', views.releases, name='releases'),
    path('releases/<slug:slug>/', views.release, name='release'),
    path('tracks/<slug:slug>/', views.track, name='track'),
    path('api/tracks/<int:pk>/play/', views.playback, name='playback'),
    path('api/tracks/<int:pk>/save/', views.save_track, name='save_track'),
    path('submit/', views.submit, name='submit'),
    path('submissions/', views.submissions, name='submissions'),
    path('submissions/<int:pk>/preview/', views.submission_preview, name='submission_preview'),
    path('library/', views.library, name='library'),
    path('playlists/<int:pk>/', views.playlist, name='playlist'),
    path('playlists/<int:pk>/edit/', views.playlist_action, name='playlist_action'),
]
