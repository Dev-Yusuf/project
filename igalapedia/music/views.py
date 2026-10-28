import logging
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Max, Q
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache

from .forms import PlaylistForm, SubmissionForm
from .models import Artist, Genre, MusicSubmission, Playlist, PlaylistItem, Release, SavedTrack, Track

logger = logging.getLogger(__name__)


def available_tracks():
    return Track.objects.filter(is_published=True, artist__is_published=True, rights_confirmed=True).filter(
        Q(release__isnull=True) | Q(release__is_published=True, release__artist__is_published=True)
    ).exclude(audio='').exclude(rights_contact='').filter(duration__gt=0).select_related('artist', 'release', 'genre')


def track_data(track):
    return {'id': track.pk, 'title': track.title, 'artist': track.artist.name,
            'artist_url': reverse('music:artist', args=[track.artist.slug]),
            'url': reverse('music:track', args=[track.slug]), 'cover': track.cover_url,
            'duration': track.duration, 'playback': reverse('music:playback', args=[track.pk])}


def page(request, section, **context):
    tracks = list(context.get('tracks', []))
    payload_tracks = tracks[:]
    if context.get('featured') and context['featured'].pk not in {track.pk for track in tracks}:
        payload_tracks.append(context['featured'])
    context.update(section=section, tracks=tracks, track_payload=[track_data(track) for track in payload_tracks],
                   genres=Genre.objects.filter(track__in=available_tracks()).distinct())
    if request.user.is_authenticated:
        context['saved_ids'] = set(SavedTrack.objects.filter(user=request.user, track__in=tracks).values_list('track_id', flat=True))
        context['user_playlists'] = Playlist.objects.filter(user=request.user)
    response = render(request, 'music/_content.html' if request.GET.get('fragment') == '1' else 'music/shell.html', context)
    response['Cache-Control'] = 'no-store'
    return response


def home(request):
    tracks = available_tracks()
    return page(request, 'home', tracks=tracks[:10], featured=tracks.filter(is_featured=True).first(),
                artists=Artist.objects.filter(is_published=True, tracks__in=tracks).distinct()[:6],
                releases=Release.objects.filter(is_published=True, artist__is_published=True, tracks__in=tracks).distinct()[:6])


def search(request):
    query = (request.GET.get('q') or '').strip()[:150]
    genre = request.GET.get('genre', '')
    tracks = available_tracks()
    if query:
        tracks = tracks.filter(Q(title__icontains=query) | Q(artist__name__icontains=query) |
                               Q(featured_artists__name__icontains=query, featured_artists__is_published=True) |
                               Q(release__title__icontains=query)).distinct()
    if genre.isdecimal() and len(genre) <= 12:
        tracks = tracks.filter(genre_id=genre)
    else:
        genre = ''
    holder = Paginator(tracks, 30).get_page(request.GET.get('page'))
    from urllib.parse import urlencode
    def link(number):
        return '?' + urlencode({'q': query, 'genre': genre, 'page': number})
    return page(request, 'search', tracks=holder, query=query, selected_genre=genre, holder=holder,
                artists=Artist.objects.filter(is_published=True, name__icontains=query)[:6] if query else [],
                releases=Release.objects.filter(is_published=True, artist__is_published=True).filter(
                    Q(title__icontains=query) | Q(artist__name__icontains=query)).select_related('artist')[:6] if query else [],
                previous_url=link(holder.previous_page_number()) if holder.has_previous() else '',
                next_url=link(holder.next_page_number()) if holder.has_next() else '')


def artists(request):
    return page(request, 'artists', artists=Artist.objects.filter(is_published=True))


def artist(request, slug):
    item = get_object_or_404(Artist, slug=slug, is_published=True)
    return page(request, 'artist', artist=item, tracks=available_tracks().filter(artist=item),
                releases=item.releases.filter(is_published=True))


def releases(request):
    return page(request, 'releases', releases=Release.objects.filter(is_published=True, artist__is_published=True).select_related('artist'))


def release(request, slug):
    item = get_object_or_404(Release.objects.select_related('artist'), slug=slug, is_published=True, artist__is_published=True)
    return page(request, 'release', release=item, tracks=available_tracks().filter(release=item).order_by('track_number', 'pk'))


def track(request, slug):
    item = get_object_or_404(available_tracks().prefetch_related('featured_artists'), slug=slug)
    return page(request, 'track', current_track=item, tracks=[item])


@never_cache
def playback(request, pk):
    item = get_object_or_404(available_tracks(), pk=pk)
    try:
        url = item.audio.url
    except Exception:
        logger.exception('Music storage unavailable for track %s', pk)
        return JsonResponse({'error': 'Playback is unavailable. Please try again.'}, status=503)
    return JsonResponse({**track_data(item), 'stream': url, 'expires_in': settings.MUSIC_PLAYBACK_URL_SECONDS})


@never_cache
@login_required
def submission_preview(request, pk):
    item = get_object_or_404(MusicSubmission, pk=pk)
    if item.user_id != request.user.pk and not request.user.has_perm('music.change_musicsubmission'):
        raise Http404
    try:
        return redirect(item.audio.url)
    except Exception:
        return JsonResponse({'error': 'Audio storage is not configured.'}, status=503)


@login_required
def submit(request):
    form = SubmissionForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        pending = MusicSubmission.objects.filter(user=request.user, status='pending').count()
        daily = MusicSubmission.objects.filter(user=request.user, created_at__date=timezone.localdate()).count()
        if pending >= 10 or daily >= 10:
            form.add_error(None, 'You have reached the submission limit. Please wait for review before uploading more.')
        elif form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            try:
                item.save()
            except Exception:
                logger.exception('Music upload failed for user %s', request.user.pk)
                form.add_error(None, 'Upload unavailable. Please try again later.')
            else:
                messages.success(request, 'Your track was submitted for review.')
                return redirect('music:submissions')
    return page(request, 'submit', form=form)


@login_required
def submissions(request):
    return page(request, 'submissions', submissions=MusicSubmission.objects.filter(user=request.user))


@login_required
def library(request):
    form = PlaylistForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if Playlist.objects.filter(user=request.user).count() >= 100:
            form.add_error(None, 'You can create up to 100 playlists.')
        else:
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            return redirect('music:playlist', pk=item.pk)
    return page(request, 'library', tracks=available_tracks().filter(saves__user=request.user).order_by('-saves__created_at'),
                playlists=Playlist.objects.filter(user=request.user), playlist_form=form)


@login_required
def playlist(request, pk):
    item = get_object_or_404(Playlist, pk=pk, user=request.user)
    return page(request, 'playlist', playlist=item,
                tracks=available_tracks().filter(playlistitem__playlist=item).order_by('playlistitem__position', 'playlistitem__pk'))


@login_required
@require_POST
def save_track(request, pk):
    item = get_object_or_404(available_tracks(), pk=pk)
    if request.POST.get('saved') == '1':
        SavedTrack.objects.get_or_create(user=request.user, track=item)
        saved = True
    else:
        SavedTrack.objects.filter(user=request.user, track=item).delete()
        saved = False
    return JsonResponse({'saved': saved})


@login_required
@require_POST
@transaction.atomic
def playlist_action(request, pk):
    item = get_object_or_404(Playlist.objects.select_for_update(), pk=pk, user=request.user)
    action = request.POST.get('action')
    if action == 'delete':
        item.delete()
        return redirect('music:library')
    if action == 'rename':
        form = PlaylistForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
        else:
            return JsonResponse({'error': 'Enter a playlist name of up to 120 characters.'}, status=400)
    else:
        track_id = request.POST.get('track', '')
        if not track_id.isdecimal():
            return JsonResponse({'error': 'Choose a track.'}, status=400)
        if action == 'add':
            song = get_object_or_404(available_tracks(), pk=track_id)
            position = (item.items.aggregate(last=Max('position'))['last'] or 0) + 1
            item.items.get_or_create(track=song, defaults={'position': position})
        elif action == 'remove':
            item.items.filter(track_id=track_id).delete()
        elif action in ('up', 'down'):
            entries = list(item.items.select_for_update())
            index = next((i for i, entry in enumerate(entries) if entry.track_id == int(track_id)), -1)
            other = index + (-1 if action == 'up' else 1)
            if index >= 0 and 0 <= other < len(entries):
                entries[index], entries[other] = entries[other], entries[index]
                for position, entry in enumerate(entries):
                    entry.position = position
                PlaylistItem.objects.bulk_update(entries, ['position'])
        else:
            return JsonResponse({'error': 'Unknown playlist action.'}, status=400)
    return redirect('music:playlist', pk=item.pk)
