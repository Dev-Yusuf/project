from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify
from ckeditor.fields import RichTextField


class Book(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
    ]
    LANGUAGE_CHOICES = [
        ("ig", "Igala"),
        ("en", "English"),
        ("bi", "Bilingual"),
        ("ot", "Other"),
    ]
    ACCESS_CHOICES = [
        ("open", "Open Access"),
        ("request", "Request Access"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=220, blank=True)
    author = models.CharField(max_length=200, blank=True)
    author_email = models.EmailField(
        blank=True,
        help_text="Author's email for access requests. Required if access type is 'Request Access'.",
    )
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="library/book_covers/", blank=True, null=True)
    file = models.FileField(upload_to="library/books/", blank=True, null=True)
    external_url = models.URLField(blank=True, null=True)
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default="ig")
    publication_year = models.IntegerField(blank=True, null=True)
    access_type = models.CharField(
        max_length=10,
        choices=ACCESS_CHOICES,
        default="open",
        help_text="'Open Access' allows direct download. 'Request Access' notifies the author via email.",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="published")
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            i = 1
            while Book.objects.filter(slug=slug).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class BookAccessRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("fulfilled", "Fulfilled"),
        ("denied", "Denied"),
    ]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="access_requests")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="book_access_requests",
    )
    email = models.EmailField(help_text="Reader's email where the book should be sent.")
    message = models.TextField(blank=True, help_text="Optional message to the author.")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["book", "user"]  # One request per user per book

    def __str__(self):
        return f"{self.user} → {self.book.title} ({self.get_status_display()})"


class PendingBook(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending Review"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="library/book_covers/", blank=True, null=True)
    file = models.FileField(upload_to="library/books/", blank=True, null=True)
    external_url = models.URLField(blank=True, null=True)
    language = models.CharField(max_length=10, choices=Book.LANGUAGE_CHOICES, default="ig")
    publication_year = models.IntegerField(blank=True, null=True)

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pending_books",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_books",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, null=True)

    approved_book = models.OneToOneField(
        Book,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_submission",
    )

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = "Pending Book"
        verbose_name_plural = "Pending Books"

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"

    def approve(self, reviewer):
        if self.status != "PENDING":
            return None

        with transaction.atomic():
            book = Book.objects.create(
                title=self.title,
                author=self.author,
                description=self.description,
                cover_image=self.cover_image,
                file=self.file,
                external_url=self.external_url,
                language=self.language,
                publication_year=self.publication_year,
                status="published",
            )
            self.status = "APPROVED"
            self.reviewed_by = reviewer
            self.reviewed_at = timezone.now()
            self.approved_book = book
            self.save()
            return book

    def reject(self, reviewer, notes=""):
        self.status = "REJECTED"
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()


class HallOfFameProfile(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=220, blank=True)
    title_role = models.CharField(max_length=200, blank=True)
    era = models.CharField(max_length=200, blank=True)
    bio = RichTextField(blank=True)
    achievements = models.TextField(blank=True)
    profile_image = models.ImageField(upload_to="library/hall_of_fame/", blank=True, null=True)
    external_links = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_featured", "name"]
        verbose_name = "Hall of Fame Profile"
        verbose_name_plural = "Hall of Fame Profiles"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            i = 1
            while HallOfFameProfile.objects.filter(slug=slug).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class PendingHallOfFameProfile(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending Review"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    name = models.CharField(max_length=200)
    title_role = models.CharField(max_length=200, blank=True)
    era = models.CharField(max_length=200, blank=True)
    bio = RichTextField(blank=True)
    achievements = models.TextField(blank=True)
    profile_image = models.ImageField(upload_to="library/hall_of_fame/", blank=True, null=True)
    external_links = models.TextField(blank=True)

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pending_hall_of_fame",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_hall_of_fame",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, null=True)

    approved_profile = models.OneToOneField(
        HallOfFameProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_submission",
    )

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = "Pending Hall of Fame Profile"
        verbose_name_plural = "Pending Hall of Fame Profiles"

    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"

    def approve(self, reviewer):
        if self.status != "PENDING":
            return None

        with transaction.atomic():
            profile = HallOfFameProfile.objects.create(
                name=self.name,
                title_role=self.title_role,
                era=self.era,
                bio=self.bio,
                achievements=self.achievements,
                profile_image=self.profile_image,
                external_links=self.external_links,
            )
            self.status = "APPROVED"
            self.reviewed_by = reviewer
            self.reviewed_at = timezone.now()
            self.approved_profile = profile
            self.save()
            return profile

    def reject(self, reviewer, notes=""):
        self.status = "REJECTED"
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()


class Quiz(models.Model):
    CATEGORY_CHOICES = [
        ("language", "Language"),
        ("history", "History"),
        ("culture", "Culture"),
        ("general", "General"),
    ]
    DIFFICULTY_CHOICES = [
        ("easy", "Easy"),
        ("medium", "Medium"),
        ("hard", "Hard"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=220, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="general")
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default="easy")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_quizzes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            i = 1
            while Quiz.objects.filter(slug=slug).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    image = models.ImageField(upload_to="library/quiz_images/", blank=True, null=True)
    audio = models.FileField(upload_to="library/quiz_audio/", blank=True, null=True)
    explanation = models.TextField(blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.quiz.title} - Q{self.order or self.id}"


class QuizChoice(models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name="choices")
    choice_text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Choice for {self.question_id}"


class QuizAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    score = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title}"


class QuizAttemptAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name="attempt_answers")
    selected_choice = models.ForeignKey(QuizChoice, on_delete=models.SET_NULL, null=True, blank=True)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Answer for {self.attempt_id}"
