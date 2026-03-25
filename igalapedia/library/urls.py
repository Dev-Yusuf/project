from django.urls import path
from . import views

app_name = "library"

urlpatterns = [
    path("", views.library_home, name="library_home"),
    path("books/", views.books_list, name="books_list"),
    path("books/submit/", views.submit_book, name="submit_book"),
    path("books/<slug:slug>/", views.book_detail, name="book_detail"),
    path("books/<slug:slug>/request/", views.request_book_access, name="request_book_access"),
    path("hall-of-fame/", views.hall_of_fame_list, name="hall_of_fame_list"),
    path("hall-of-fame/submit/", views.submit_hall_of_fame, name="submit_hall_of_fame"),
    path("hall-of-fame/<slug:slug>/", views.hall_of_fame_detail, name="hall_of_fame_detail"),
    path("games/", views.games_home, name="games_home"),
    path("games/quizzes/<slug:slug>/", views.quiz_detail, name="quiz_detail"),
    path("games/quizzes/<slug:slug>/play/", views.quiz_play, name="quiz_play"),
    path("games/quizzes/<slug:slug>/result/", views.quiz_result, name="quiz_result"),
    path("my-submissions/", views.my_library_submissions, name="my_library_submissions"),
]
