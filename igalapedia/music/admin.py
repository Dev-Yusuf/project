from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from .forms import ReviewForm
from .models import Artist, Genre, MusicSubmission, Playlist, Release, Track


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_published']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    search_fields = ['name']


@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    list_display = ['title', 'artist', 'kind', 'is_published']
    list_filter = ['kind', 'is_published']
    search_fields = ['title', 'artist__name']
    autocomplete_fields = ['artist']


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ['title', 'artist', 'duration', 'is_published', 'rights_confirmed']
    list_filter = ['is_published', 'genre', 'rights_confirmed']
    search_fields = ['title', 'artist__name']
    autocomplete_fields = ['artist', 'featured_artists', 'release', 'genre']
    readonly_fields = ['duration', 'created_at']


@admin.register(MusicSubmission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['title', 'artist_name', 'user', 'status', 'created_at', 'review_link']
    list_filter = ['status']
    search_fields = ['title', 'artist_name', 'user__username']
    readonly_fields = ['user', 'artist_name', 'title', 'genre', 'duration', 'rights_confirmed',
                       'rights_contact', 'rights_notes', 'status', 'review_notes', 'reviewed_by',
                       'reviewed_at', 'approved_track', 'created_at', 'review_link']
    exclude = ['audio', 'artwork']
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False  # Audio may be shared with an approved track; retain audit history.
    def review_link(self, obj):
        return format_html('<a href="{}">Review submission</a>', reverse('admin:music_review', args=[obj.pk]))
    def get_urls(self):
        return [path('<int:pk>/review/', self.admin_site.admin_view(self.review), name='music_review')] + super().get_urls()
    @transaction.atomic
    def review(self, request, pk):
        if not self.has_change_permission(request):
            raise PermissionDenied
        item = get_object_or_404(MusicSubmission.objects.select_for_update(), pk=pk)
        form = ReviewForm(request.POST or None)
        if request.method == 'POST' and form.is_valid():
            if item.status != 'pending':
                form.add_error(None, 'This submission has already been reviewed.')
            elif request.POST.get('decision') == 'approve':
                if not form.cleaned_data['artist']:
                    form.add_error('artist', 'Select a published artist. Create a new artist profile if needed.')
                else:
                    try:
                        track = item.approve(request.user, form.cleaned_data['artist'])
                        MusicSubmission.objects.filter(pk=item.pk).update(review_notes=form.cleaned_data['review_notes'])
                    except ValidationError as exc:
                        form.add_error(None, exc)
                    else:
                        self.log_change(request, item, f'Approved as track {track.pk}')
                        self.message_user(request, 'Track approved and published.', messages.SUCCESS)
                        return redirect('admin:music_musicsubmission_changelist')
            elif request.POST.get('decision') == 'reject':
                if not form.cleaned_data['review_notes'].strip():
                    form.add_error('review_notes', 'Give the artist a reason for rejection.')
                else:
                    item.status = 'rejected'
                    item.review_notes = form.cleaned_data['review_notes']
                    item.reviewed_by = request.user
                    item.reviewed_at = timezone.now()
                    item.save()
                    self.log_change(request, item, 'Rejected submission')
                    return redirect('admin:music_musicsubmission_changelist')
        return render(request, 'admin/music/review.html', {**self.admin_site.each_context(request), 'item': item,
            'form': form, 'title': 'Review music submission', 'opts': self.model._meta})


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'created_at']
    readonly_fields = ['user', 'title', 'created_at']
    def has_add_permission(self, request):
        return False
