from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import redirect, render
from django.utils import timezone
from .models import (
    PartOfSpeech, Example, Meaning, Words,
    PendingWord, PendingMeaning, PendingExample, PendingExampleContribution, ContributionStats
)


# ========================================
# ORIGINAL MODELS ADMIN
# ========================================

@admin.register(PartOfSpeech)
class PartOfSpeechAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Example)
class ExampleAdmin(admin.ModelAdmin):
    list_display = ['igala_example', 'english_meaning', 'has_audio']
    search_fields = ['igala_example', 'english_meaning']
    
    def has_audio(self, obj):
        return bool(obj.audio)
    has_audio.boolean = True
    has_audio.short_description = 'Audio'


class MeaningInline(admin.TabularInline):
    model = Meaning
    extra = 1
    filter_horizontal = ['examples']


@admin.register(Words)
class WordsAdmin(admin.ModelAdmin):
    list_display = ['word', 'contributor', 'dialects']
    list_filter = ['contributor']
    search_fields = ['word', 'dialects']
    prepopulated_fields = {'slug': ('word',)}
    inlines = [MeaningInline]


@admin.register(Meaning)
class MeaningAdmin(admin.ModelAdmin):
    list_display = ['meaning', 'word', 'part_of_speech']
    list_filter = ['part_of_speech']
    search_fields = ['meaning', 'word__word']
    filter_horizontal = ['examples']


# ========================================
# PENDING SUBMISSIONS ADMIN
# ========================================

class PendingMeaningInline(admin.TabularInline):
    model = PendingMeaning
    extra = 0
    fields = ['meaning', 'part_of_speech']
    readonly_fields = []


class PendingExampleInline(admin.TabularInline):
    model = PendingExample
    extra = 0
    fields = ['igala_example', 'english_meaning']


@admin.register(PendingWord)
class PendingWordAdmin(admin.ModelAdmin):
    list_display = [
        'word',
        'submitted_by_link',
        'status_badge',
        'submitted_at',
        'reviewed_by',
        'meanings_count'
    ]
    list_filter = ['status', 'submitted_at', 'reviewed_at']
    search_fields = ['word', 'submitted_by__username', 'dialects']
    readonly_fields = [
        'submitted_by',
        'submitted_at',
        'reviewed_by',
        'reviewed_at',
        'approved_word_link',
        'status'
    ]
    fieldsets = (
        ('Word Information', {
            'fields': ('word', 'pronunciation_file', 'dialects', 'related_terms')
        }),
        ('Submission Details', {
            'fields': ('submitted_by', 'submitted_at', 'status')
        }),
        ('Review Details', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_notes', 'approved_word_link'),
            'classes': ('collapse',)
        }),
    )
    inlines = [PendingMeaningInline]
    actions = ['approve_submissions', 'reject_submissions']

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'reject-with-notes/',
                self.admin_site.admin_view(self.reject_with_notes_view),
                name='dictionary_pendingword_reject_with_notes',
            ),
        ]
        return custom + urls

    def reject_with_notes_view(self, request):
        """Intermediate page for rejecting submissions with custom notes."""
        from django.http import HttpResponseRedirect

        ids_param = request.GET.get('ids') or request.POST.get('ids') or ''
        ids = [pk.strip() for pk in ids_param.split(',') if pk.strip()]
        ids = [pk for pk in ids if pk.isdigit()]

        pending_words = PendingWord.objects.filter(
            pk__in=ids, status='PENDING'
        ).select_related('submitted_by').order_by('word')

        if not pending_words:
            self.message_user(
                request,
                'No pending submissions selected or they were already processed.',
                messages.WARNING,
            )
            return HttpResponseRedirect(reverse('admin:dictionary_pendingword_changelist'))

        if request.method == 'POST':
            review_notes = (request.POST.get('review_notes') or '').strip()
            rejected_count = 0
            for pending_word in pending_words:
                pending_word.reject(request.user, notes=review_notes or 'No reason provided.')

                stats, created = ContributionStats.objects.get_or_create(
                    user=pending_word.submitted_by
                )
                stats.update_stats()

                try:
                    from dictionary.emails import send_word_rejected_email
                    send_word_rejected_email(
                        pending_word.submitted_by, pending_word, request
                    )
                except Exception:
                    pass
                rejected_count += 1

            self.message_user(
                request,
                f'{rejected_count} submission(s) rejected. Contributors have been notified.',
                messages.SUCCESS,
            )
            return HttpResponseRedirect(reverse('admin:dictionary_pendingword_changelist'))

        # GET: show form
        context = {
            **self.admin_site.each_context(request),
            'title': 'Reject submissions with notes',
            'pending_words': pending_words,
            'ids_param': ','.join(str(p.pk) for p in pending_words),
            'opts': self.model._meta,
        }
        return render(request, 'admin/dictionary/pendingword/reject_with_notes.html', context)

    def reject_submissions(self, request, queryset):
        """Redirect to reject-with-notes page so admin can add rejection reason."""
        from django.http import HttpResponseRedirect

        pending = queryset.filter(status='PENDING')
        if not pending:
            self.message_user(request, 'No pending submissions selected.', messages.WARNING)
            return None
        ids = ','.join(str(p.pk) for p in pending)
        url = reverse('admin:dictionary_pendingword_reject_with_notes') + '?ids=' + ids
        return HttpResponseRedirect(url)
    reject_submissions.short_description = '❌ Reject selected submissions (add notes)'

    def submitted_by_link(self, obj):
        """Link to user's profile"""
        if obj.submitted_by:
            url = reverse('admin:auth_user_change', args=[obj.submitted_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.submitted_by.username)
        return '-'
    submitted_by_link.short_description = 'Submitted By'
    
    def status_badge(self, obj):
        """Colored status badge"""
        colors = {
            'PENDING': 'orange',
            'APPROVED': 'green',
            'REJECTED': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def approved_word_link(self, obj):
        """Link to approved word if exists"""
        if obj.approved_word:
            url = reverse('admin:dictionary_words_change', args=[obj.approved_word.id])
            return format_html('<a href="{}">View Approved Word</a>', url)
        return 'Not yet approved'
    approved_word_link.short_description = 'Approved Word'
    
    def meanings_count(self, obj):
        """Count of meanings submitted"""
        return obj.pending_meanings.count()
    meanings_count.short_description = 'Meanings'
    
    def approve_submissions(self, request, queryset):
        """Bulk approve submissions"""
        approved_count = 0
        duplicate_count = 0
        
        for pending_word in queryset.filter(status='PENDING'):
            word = pending_word.approve(request.user)
            if word:
                # Create meanings and examples
                for pending_meaning in pending_word.pending_meanings.all():
                    # Create official meaning
                    meaning = Meaning.objects.create(
                        word=word,
                        meaning=pending_meaning.meaning,
                        part_of_speech=pending_meaning.part_of_speech
                    )
                    
                    # Create examples if any
                    for pending_example in pending_meaning.pending_examples.all():
                        example = Example.objects.create(
                            igala_example=pending_example.igala_example,
                            english_meaning=pending_example.english_meaning
                        )
                        meaning.examples.add(example)
                
                # Update contributor stats
                stats, created = ContributionStats.objects.get_or_create(
                    user=pending_word.submitted_by
                )
                stats.update_stats()
                
                # Send approval email to the contributor
                try:
                    from dictionary.emails import send_word_approved_email
                    send_word_approved_email(
                        pending_word.submitted_by, word, pending_word, request
                    )
                except Exception:
                    pass
                
                approved_count += 1
            else:
                # Check if it was auto-rejected as duplicate (status changed to REJECTED)
                pending_word.refresh_from_db()
                if pending_word.status == 'REJECTED' and 'Duplicate' in (pending_word.review_notes or ''):
                    duplicate_count += 1
                    # Update contributor stats
                    stats, created = ContributionStats.objects.get_or_create(
                        user=pending_word.submitted_by
                    )
                    stats.update_stats()
                    # Send rejection email for duplicate
                    try:
                        from dictionary.emails import send_word_rejected_email
                        send_word_rejected_email(
                            pending_word.submitted_by, pending_word, request
                        )
                    except Exception:
                        pass
        
        # Build result message
        msg_parts = []
        if approved_count:
            msg_parts.append(f'{approved_count} submission(s) approved')
        if duplicate_count:
            msg_parts.append(f'{duplicate_count} skipped as duplicate(s)')
        
        if msg_parts:
            self.message_user(request, '. '.join(msg_parts) + '.')
        else:
            self.message_user(request, 'No pending submissions were processed.', messages.WARNING)
    approve_submissions.short_description = '✅ Approve selected submissions'
    


@admin.register(PendingMeaning)
class PendingMeaningAdmin(admin.ModelAdmin):
    list_display = ['meaning', 'pending_word', 'part_of_speech', 'examples_count']
    list_filter = ['part_of_speech']
    search_fields = ['meaning', 'pending_word__word']
    inlines = [PendingExampleInline]
    
    def examples_count(self, obj):
        return obj.pending_examples.count()
    examples_count.short_description = 'Examples'


@admin.register(PendingExample)
class PendingExampleAdmin(admin.ModelAdmin):
    list_display = ['igala_example', 'english_meaning', 'pending_meaning']
    search_fields = ['igala_example', 'english_meaning']


@admin.register(ContributionStats)
class ContributionStatsAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'approved_words_count',
        'pending_words_count',
        'rejected_words_count',
        'total_submissions',
        'first_contribution',
        'last_contribution'
    ]
    list_filter = ['first_contribution', 'last_contribution']
    search_fields = ['user__username']
    readonly_fields = [
        'user',
        'approved_words_count',
        'pending_words_count',
        'rejected_words_count',
        'total_submissions',
        'first_contribution',
        'last_contribution'
    ]
    actions = ['recalculate_stats']
    
    def recalculate_stats(self, request, queryset):
        """Recalculate statistics for selected users"""
        for stats in queryset:
            stats.update_stats()
        self.message_user(request, f'Statistics updated for {queryset.count()} user(s).')
    recalculate_stats.short_description = '🔄 Recalculate statistics'


# ========================================
# PENDING EXAMPLE CONTRIBUTIONS ADMIN
# ========================================

@admin.register(PendingExampleContribution)
class PendingExampleContributionAdmin(admin.ModelAdmin):
    list_display = [
        'igala_example_truncated',
        'word_link',
        'meaning_display',
        'submitted_by_link',
        'status_badge',
        'submitted_at',
    ]
    list_filter = ['status', 'submitted_at', 'reviewed_at']
    search_fields = [
        'igala_example',
        'english_meaning',
        'meaning__word__word',
        'submitted_by__username'
    ]
    readonly_fields = [
        'submitted_by',
        'submitted_at',
        'reviewed_by',
        'reviewed_at',
        'approved_example',
        'status'
    ]
    fieldsets = (
        ('Example Content', {
            'fields': ('meaning', 'igala_example', 'english_meaning')
        }),
        ('Submission Details', {
            'fields': ('submitted_by', 'submitted_at', 'status')
        }),
        ('Review Details', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_notes', 'approved_example'),
            'classes': ('collapse',)
        }),
    )
    actions = ['approve_examples', 'reject_examples']

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'reject-with-notes/',
                self.admin_site.admin_view(self.reject_with_notes_view),
                name='dictionary_pendingexamplecontribution_reject_with_notes',
            ),
        ]
        return custom + urls

    def reject_with_notes_view(self, request):
        """Intermediate page for rejecting example contributions with custom notes."""
        from django.http import HttpResponseRedirect

        ids_param = request.GET.get('ids') or request.POST.get('ids') or ''
        ids = [pk.strip() for pk in ids_param.split(',') if pk.strip()]
        ids = [pk for pk in ids if pk.isdigit()]

        pending_examples = PendingExampleContribution.objects.filter(
            pk__in=ids, status='PENDING'
        ).select_related('submitted_by', 'meaning__word').order_by('igala_example')

        if not pending_examples:
            self.message_user(
                request,
                'No pending example contributions selected or they were already processed.',
                messages.WARNING,
            )
            return HttpResponseRedirect(reverse('admin:dictionary_pendingexamplecontribution_changelist'))

        if request.method == 'POST':
            review_notes = (request.POST.get('review_notes') or '').strip()
            rejected_count = 0
            for pending_example in pending_examples:
                pending_example.reject(request.user, notes=review_notes or 'No reason provided.')

                # Send rejection email
                try:
                    from dictionary.emails import send_example_rejected_email
                    send_example_rejected_email(
                        pending_example.submitted_by, pending_example, request
                    )
                except Exception:
                    pass
                rejected_count += 1

            self.message_user(
                request,
                f'{rejected_count} example contribution(s) rejected. Contributors have been notified.',
                messages.SUCCESS,
            )
            return HttpResponseRedirect(reverse('admin:dictionary_pendingexamplecontribution_changelist'))

        # GET: show form
        context = {
            **self.admin_site.each_context(request),
            'title': 'Reject example contributions with notes',
            'pending_examples': pending_examples,
            'ids_param': ','.join(str(p.pk) for p in pending_examples),
            'opts': self.model._meta,
        }
        return render(request, 'admin/dictionary/pendingexamplecontribution/reject_with_notes.html', context)

    def igala_example_truncated(self, obj):
        """Truncate long examples for display"""
        text = obj.igala_example
        if len(text) > 50:
            return text[:50] + '...'
        return text
    igala_example_truncated.short_description = 'Igala Example'

    def word_link(self, obj):
        """Link to the word this example is for"""
        word = obj.meaning.word
        url = reverse('admin:dictionary_words_change', args=[word.id])
        return format_html('<a href="{}">{}</a>', url, word.word)
    word_link.short_description = 'Word'

    def meaning_display(self, obj):
        """Show the meaning (truncated)"""
        text = f"({obj.meaning.part_of_speech.name}) {obj.meaning.meaning}"
        if len(text) > 40:
            return text[:40] + '...'
        return text
    meaning_display.short_description = 'Meaning'

    def submitted_by_link(self, obj):
        """Link to user's profile"""
        if obj.submitted_by:
            url = reverse('admin:auth_user_change', args=[obj.submitted_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.submitted_by.username)
        return '-'
    submitted_by_link.short_description = 'Submitted By'

    def status_badge(self, obj):
        """Colored status badge"""
        colors = {
            'PENDING': 'orange',
            'APPROVED': 'green',
            'REJECTED': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def approve_examples(self, request, queryset):
        """Bulk approve example contributions"""
        approved_count = 0
        for pending_example in queryset.filter(status='PENDING'):
            example = pending_example.approve(request.user)
            if example:
                # Send approval email
                try:
                    from dictionary.emails import send_example_approved_email
                    send_example_approved_email(
                        pending_example.submitted_by,
                        pending_example.meaning,
                        pending_example.meaning.word,
                        request
                    )
                except Exception:
                    pass
                approved_count += 1

        self.message_user(request, f'{approved_count} example contribution(s) approved successfully.')
    approve_examples.short_description = '✅ Approve selected examples'

    def reject_examples(self, request, queryset):
        """Redirect to reject-with-notes page so admin can add rejection reason."""
        from django.http import HttpResponseRedirect

        pending = queryset.filter(status='PENDING')
        if not pending:
            self.message_user(request, 'No pending example contributions selected.', messages.WARNING)
            return None
        ids = ','.join(str(p.pk) for p in pending)
        url = reverse('admin:dictionary_pendingexamplecontribution_reject_with_notes') + '?ids=' + ids
        return HttpResponseRedirect(url)
    reject_examples.short_description = '❌ Reject selected examples (add notes)'
