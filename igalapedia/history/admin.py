from django.contrib import admin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from .models import PendingHistory, HistoryArticle, ArticleView
from dictionary.models import ContributionStats


@admin.register(HistoryArticle)
class HistoryArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'contributor', 'published_at']
    list_filter = ['published_at']
    search_fields = ['title', 'excerpt']
    readonly_fields = ['slug', 'published_at', 'updated_at']


@admin.register(ArticleView)
class ArticleViewAdmin(admin.ModelAdmin):
    list_display = ('article', 'ip_hash', 'viewed_date')
    list_filter = ('viewed_date',)
    readonly_fields = ('article', 'ip_hash', 'viewed_date')


@admin.register(PendingHistory)
class PendingHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'submitted_by',
        'status',
        'submitted_at',
    ]
    list_filter = ['status', 'submitted_at']
    search_fields = ['title', 'excerpt', 'submitted_by__username']
    readonly_fields = ['submitted_by', 'submitted_at', 'reviewed_by', 'reviewed_at', 'approved_article']
    fieldsets = (
        ('Content', {
            'fields': ('title', 'excerpt', 'thumbnail', 'content_english', 'content_igala', 'audio_english', 'audio_igala')
        }),
        ('Submission', {
            'fields': ('submitted_by', 'submitted_at', 'status')
        }),
        ('Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'rejection_notes', 'approved_article')
        }),
    )
    actions = ['approve_submissions', 'reject_submissions']

    def approve_submissions(self, request, queryset):
        from django.utils import timezone

        pending = queryset.filter(status='PENDING')
        approved_count = 0
        for sub in pending:
            try:
                article = HistoryArticle.objects.create(
                    title=sub.title,
                    excerpt=sub.excerpt or '',
                    thumbnail=sub.thumbnail,
                    content_english=sub.content_english or '',
                    content_igala=sub.content_igala or '',
                    audio_english=sub.audio_english,
                    audio_igala=sub.audio_igala,
                    contributor=sub.submitted_by,
                )
                sub.status = 'APPROVED'
                sub.reviewed_by = request.user
                sub.reviewed_at = timezone.now()
                sub.approved_article = article
                sub.save()

                stats, _ = ContributionStats.objects.get_or_create(user=sub.submitted_by)
                stats.approved_histories_count = (stats.approved_histories_count or 0) + 1
                stats.save()

                approved_count += 1
            except Exception as e:
                self.message_user(request, f'Failed to approve "{sub.title}": {e}', messages.ERROR)

        if approved_count:
            self.message_user(request, f'{approved_count} history article(s) approved.', messages.SUCCESS)
        return redirect(reverse('admin:history_pendinghistory_changelist'))

    approve_submissions.short_description = 'Approve selected histories'

    def reject_submissions(self, request, queryset):
        from django.utils import timezone

        pending = queryset.filter(status='PENDING')
        for sub in pending:
            sub.status = 'REJECTED'
            sub.reviewed_by = request.user
            sub.reviewed_at = timezone.now()
            if not (sub.rejection_notes and sub.rejection_notes.strip()):
                sub.rejection_notes = 'Rejected by admin.'
            sub.save()
        count = pending.count()
        self.message_user(request, f'{count} submission(s) rejected.', messages.WARNING)
        return redirect(reverse('admin:history_pendinghistory_changelist'))

    reject_submissions.short_description = 'Reject selected histories'
