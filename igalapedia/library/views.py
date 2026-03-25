from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.db import transaction, IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from main.utils import paginate_queryset
from .forms import BookSubmissionForm, HallOfFameSubmissionForm
from .models import (
    Book,
    BookAccessRequest,
    PendingBook,
    HallOfFameProfile,
    PendingHallOfFameProfile,
    Quiz,
    QuizAttempt,
    QuizAttemptAnswer,
    QuizChoice,
)


def library_home(request):
    return render(request, "library/library_home.html", {"page_title": "Library - IgalaHeritage"})


def books_list(request):
    books = Book.objects.filter(status="published")

    author = (request.GET.get("author") or "").strip()
    language = (request.GET.get("language") or "").strip()
    year = (request.GET.get("year") or "").strip()

    if author:
        books = books.filter(author__icontains=author)
    if language:
        books = books.filter(language=language)
    if year.isdigit():
        books = books.filter(publication_year=int(year))

    books = books.order_by("-created_at")
    page = paginate_queryset(books, 12, request.GET.get("page"))

    years = (
        Book.objects.exclude(publication_year__isnull=True)
        .values_list("publication_year", flat=True)
        .distinct()
        .order_by("-publication_year")
    )

    context = {
        "books": page,
        "filters": {
            "author": author,
            "language": language,
            "year": year,
        },
        "years": years,
        "page_title": "Books - Library",
    }
    return render(request, "library/books_list.html", context)


def book_detail(request, slug):
    book = get_object_or_404(Book, slug=slug, status="published")

    can_download = book.access_type == "open" and book.file
    has_requested = False
    if request.user.is_authenticated and book.access_type == "request":
        has_requested = BookAccessRequest.objects.filter(
            book=book, user=request.user
        ).exists()

    return render(
        request,
        "library/book_detail.html",
        {
            "book": book,
            "can_download": can_download,
            "has_requested": has_requested,
            "page_title": f"{book.title} - Library",
        },
    )


@login_required
@require_POST
def request_book_access(request, slug):
    book = get_object_or_404(Book, slug=slug, status="published", access_type="request")

    email = (request.POST.get("email") or "").strip()
    message_text = (request.POST.get("message") or "").strip()

    if not email:
        messages.error(request, "Please provide your email address.")
        return redirect("library:book_detail", slug=slug)

    try:
        access_request = BookAccessRequest.objects.create(
            book=book,
            user=request.user,
            email=email,
            message=message_text,
        )
    except IntegrityError:
        messages.info(request, "You have already requested access to this book.")
        return redirect("library:book_detail", slug=slug)

    # Send email notification to the author
    if book.author_email:
        subject = f"Book Access Request: {book.title}"
        body = (
            f"Hello {book.author},\n\n"
            f"A reader on IgalaHeritage has requested access to your book:\n\n"
            f"Book: {book.title}\n"
            f"Reader: {request.user.get_full_name() or request.user.username}\n"
            f"Email: {email}\n"
        )
        if message_text:
            body += f"Message: {message_text}\n"
        body += (
            f"\nPlease reply directly to the reader at {email} to share the book.\n\n"
            f"Thank you for contributing to IgalaHeritage."
        )
        try:
            send_mail(
                subject,
                body,
                django_settings.DEFAULT_FROM_EMAIL,
                [book.author_email],
                fail_silently=True,
            )
        except Exception:
            pass  # Don't block the user if email fails

    messages.success(
        request,
        "Your request has been sent to the author. They will contact you at the email you provided.",
    )
    return redirect("library:book_detail", slug=slug)


def hall_of_fame_list(request):
    profiles = HallOfFameProfile.objects.all().order_by("-is_featured", "name")
    page = paginate_queryset(profiles, 12, request.GET.get("page"))
    return render(
        request,
        "library/hall_of_fame_list.html",
        {"profiles": page, "page_title": "Hall of Fame - Library"},
    )


def hall_of_fame_detail(request, slug):
    profile = get_object_or_404(HallOfFameProfile, slug=slug)
    return render(
        request,
        "library/hall_of_fame_detail.html",
        {"profile": profile, "page_title": f"{profile.name} - Hall of Fame"},
    )


@login_required
def submit_book(request):
    if request.method == "POST":
        form = BookSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.submitted_by = request.user
            submission.save()
            messages.success(request, "Thanks! Your book submission is pending review.")
            return redirect("library:submit_book")
        messages.error(request, "Please correct the errors below.")
    else:
        form = BookSubmissionForm()

    return render(
        request,
        "library/submit_book.html",
        {"form": form, "page_title": "Submit Book - Library"},
    )


@login_required
def submit_hall_of_fame(request):
    if request.method == "POST":
        form = HallOfFameSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.submitted_by = request.user
            submission.save()
            messages.success(request, "Thanks! Your Hall of Fame submission is pending review.")
            return redirect("library:submit_hall_of_fame")
        messages.error(request, "Please correct the errors below.")
    else:
        form = HallOfFameSubmissionForm()

    return render(
        request,
        "library/submit_hall_of_fame.html",
        {"form": form, "page_title": "Submit Hall of Fame - Library"},
    )


@login_required
def my_library_submissions(request):
    pending_books = PendingBook.objects.filter(submitted_by=request.user, status="PENDING").order_by("-submitted_at")
    approved_books = PendingBook.objects.filter(submitted_by=request.user, status="APPROVED").order_by("-reviewed_at")
    rejected_books = PendingBook.objects.filter(submitted_by=request.user, status="REJECTED").order_by("-reviewed_at")

    pending_profiles = PendingHallOfFameProfile.objects.filter(
        submitted_by=request.user, status="PENDING"
    ).order_by("-submitted_at")
    approved_profiles = PendingHallOfFameProfile.objects.filter(
        submitted_by=request.user, status="APPROVED"
    ).order_by("-reviewed_at")
    rejected_profiles = PendingHallOfFameProfile.objects.filter(
        submitted_by=request.user, status="REJECTED"
    ).order_by("-reviewed_at")

    context = {
        "pending_books": pending_books,
        "approved_books": approved_books,
        "rejected_books": rejected_books,
        "pending_profiles": pending_profiles,
        "approved_profiles": approved_profiles,
        "rejected_profiles": rejected_profiles,
        "page_title": "My Library Submissions",
    }
    return render(request, "library/my_submissions.html", context)


def games_home(request):
    quizzes = Quiz.objects.filter(is_active=True).order_by("-created_at")
    return render(
        request,
        "library/games_home.html",
        {"quizzes": quizzes, "page_title": "Games - Library"},
    )


def quiz_detail(request, slug):
    quiz = get_object_or_404(Quiz, slug=slug, is_active=True)
    question_count = quiz.questions.count()
    return render(
        request,
        "library/quiz_detail.html",
        {
            "quiz": quiz,
            "question_count": question_count,
            "page_title": f"{quiz.title} - Quiz",
        },
    )


@login_required
def quiz_play(request, slug):
    quiz = get_object_or_404(Quiz, slug=slug, is_active=True)
    questions = list(quiz.questions.prefetch_related("choices"))

    if request.method == "POST":
        with transaction.atomic():
            attempt = QuizAttempt.objects.create(
                user=request.user,
                quiz=quiz,
                score=0,
                total_questions=len(questions),
                completed_at=timezone.now(),
            )

            score = 0
            for question in questions:
                selected_choice_id = request.POST.get(f"q_{question.id}")
                selected_choice = None
                is_correct = False
                if selected_choice_id:
                    selected_choice = QuizChoice.objects.filter(id=selected_choice_id, question=question).first()
                    if selected_choice and selected_choice.is_correct:
                        is_correct = True
                        score += 1

                QuizAttemptAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    selected_choice=selected_choice,
                    is_correct=is_correct,
                )

            attempt.score = score
            attempt.completed_at = timezone.now()
            attempt.save()

        request.session[f"quiz_attempt_{quiz.id}"] = attempt.id
        return redirect("library:quiz_result", slug=quiz.slug)

    return render(
        request,
        "library/quiz_play.html",
        {
            "quiz": quiz,
            "questions": questions,
            "page_title": f"{quiz.title} - Play",
        },
    )


@login_required
def quiz_result(request, slug):
    quiz = get_object_or_404(Quiz, slug=slug, is_active=True)
    attempt_id = request.session.get(f"quiz_attempt_{quiz.id}")
    attempt = None
    if attempt_id:
        attempt = (
            QuizAttempt.objects.filter(id=attempt_id, user=request.user, quiz=quiz)
            .prefetch_related("answers__question", "answers__selected_choice")
            .first()
        )

    if not attempt:
        messages.info(request, "Please complete the quiz first.")
        return redirect("library:quiz_detail", slug=quiz.slug)

    answer_map = {answer.question_id: answer for answer in attempt.answers.all()}
    questions = list(quiz.questions.prefetch_related("choices"))

    return render(
        request,
        "library/quiz_result.html",
        {
            "quiz": quiz,
            "attempt": attempt,
            "questions": questions,
            "answer_map": answer_map,
            "page_title": f"{quiz.title} - Results",
        },
    )

