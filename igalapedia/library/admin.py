from django.contrib import admin, messages
from .models import (
    Book,
    BookAccessRequest,
    PendingBook,
    HallOfFameProfile,
    PendingHallOfFameProfile,
    Quiz,
    QuizQuestion,
    QuizChoice,
    QuizAttempt,
    QuizAttemptAnswer,
)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "language", "access_type", "publication_year", "status", "is_featured", "created_at")
    list_filter = ("status", "language", "access_type", "is_featured")
    search_fields = ("title", "author")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(BookAccessRequest)
class BookAccessRequestAdmin(admin.ModelAdmin):
    list_display = ("book", "user", "email", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("book__title", "user__username", "email")
    readonly_fields = ("book", "user", "email", "message", "created_at")

@admin.register(PendingBook)
class PendingBookAdmin(admin.ModelAdmin):
    list_display = ("title", "submitted_by", "status", "submitted_at", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("title", "author", "submitted_by__username")
    actions = ("approve_selected", "reject_selected")

    @admin.action(description="Approve selected book submissions")
    def approve_selected(self, request, queryset):
        approved = 0
        for submission in queryset:
            if submission.status == "PENDING":
                submission.approve(request.user)
                approved += 1
        self.message_user(request, f"Approved {approved} book submission(s).", messages.SUCCESS)

    @admin.action(description="Reject selected book submissions")
    def reject_selected(self, request, queryset):
        rejected = 0
        for submission in queryset:
            if submission.status == "PENDING":
                submission.reject(request.user, notes="Rejected in admin.")
                rejected += 1
        self.message_user(request, f"Rejected {rejected} book submission(s).", messages.WARNING)


@admin.register(HallOfFameProfile)
class HallOfFameProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "title_role", "era", "is_featured", "created_at")
    list_filter = ("is_featured",)
    search_fields = ("name", "title_role", "era")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(PendingHallOfFameProfile)
class PendingHallOfFameProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "submitted_by", "status", "submitted_at", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("name", "submitted_by__username")
    actions = ("approve_selected", "reject_selected")

    @admin.action(description="Approve selected Hall of Fame submissions")
    def approve_selected(self, request, queryset):
        approved = 0
        for submission in queryset:
            if submission.status == "PENDING":
                submission.approve(request.user)
                approved += 1
        self.message_user(request, f"Approved {approved} Hall of Fame submission(s).", messages.SUCCESS)

    @admin.action(description="Reject selected Hall of Fame submissions")
    def reject_selected(self, request, queryset):
        rejected = 0
        for submission in queryset:
            if submission.status == "PENDING":
                submission.reject(request.user, notes="Rejected in admin.")
                rejected += 1
        self.message_user(request, f"Rejected {rejected} Hall of Fame submission(s).", messages.WARNING)


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 1


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "difficulty", "is_active", "created_at")
    list_filter = ("category", "difficulty", "is_active")
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}
    inlines = [QuizQuestionInline]


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("quiz", "order", "question_text")
    search_fields = ("question_text",)
    list_filter = ("quiz",)


@admin.register(QuizChoice)
class QuizChoiceAdmin(admin.ModelAdmin):
    list_display = ("question", "choice_text", "is_correct")
    list_filter = ("is_correct",)
    search_fields = ("choice_text",)


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "quiz", "score", "total_questions", "started_at", "completed_at")
    list_filter = ("quiz",)
    search_fields = ("user__username", "quiz__title")


@admin.register(QuizAttemptAnswer)
class QuizAttemptAnswerAdmin(admin.ModelAdmin):
    list_display = ("attempt", "question", "selected_choice", "is_correct")
    list_filter = ("is_correct",)
