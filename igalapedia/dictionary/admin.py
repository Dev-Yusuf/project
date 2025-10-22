from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    PartOfSpeech, Example, Meaning, Words,
    PendingWord, PendingMeaning, PendingExample, ContributionStats
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
    list_display = ['igala_example', 'english_meaning']
    search_fields = ['igala_example', 'english_meaning']


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
                
                approved_count += 1
        
        self.message_user(request, f'{approved_count} submission(s) approved successfully.')
    approve_submissions.short_description = '✅ Approve selected submissions'
    
    def reject_submissions(self, request, queryset):
        """Bulk reject submissions"""
        rejected_count = 0
        for pending_word in queryset.filter(status='PENDING'):
            pending_word.reject(request.user, notes="Rejected via bulk action")
            
            # Update contributor stats
            stats, created = ContributionStats.objects.get_or_create(
                user=pending_word.submitted_by
            )
            stats.update_stats()
            
            rejected_count += 1
        
        self.message_user(request, f'{rejected_count} submission(s) rejected.')
    reject_submissions.short_description = '❌ Reject selected submissions'


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
