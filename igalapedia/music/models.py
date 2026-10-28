from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify

from core.validators import validate_image_upload
from .storage import music_storage
from .validators import audio_metadata, validate_music_audio


def audio_path(instance, filename):
    return f'audio/{uuid4().hex}{Path(filename).suffix.lower()}'


def artwork_path(instance, filename):
    return f'artwork/{uuid4().hex}{Path(filename).suffix.lower()}'


def validate_storage(audio):
    if hasattr(audio.storage, 'configured'):
        try:
            audio.storage.configured()
        except ImproperlyConfigured as exc:
            raise ValidationError('Music uploads are not available yet. Please try again later.') from exc


def unique_slug(instance, value):
    base = (slugify(value) or 'music')[:180]
    candidate = base
    while type(instance).objects.exclude(pk=instance.pk).filter(slug=candidate).exists():
        candidate = f'{base}-{uuid4().hex[:8]}'
    return candidate


class Artist(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    bio = models.TextField(blank=True)
    image = models.ImageField(upload_to='music/artists/', validators=[validate_image_upload], blank=True)
    is_published = models.BooleanField(default=False)
    class Meta:
        ordering = ['name', 'pk']
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)
    def __str__(self):
        return self.name


class Genre(models.Model):
    name = models.CharField(max_length=80, unique=True)
    class Meta:
        ordering = ['name']
    def __str__(self):
        return self.name


class Release(models.Model):
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    artist = models.ForeignKey(Artist, on_delete=models.PROTECT, related_name='releases')
    kind = models.CharField(max_length=10, choices=[('album', 'Album'), ('ep', 'EP'), ('single', 'Single')], default='album')
    artwork = models.ImageField(upload_to='music/releases/', validators=[validate_image_upload], blank=True)
    release_date = models.DateField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    class Meta:
        ordering = ['-release_date', '-pk']
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.title)
        super().save(*args, **kwargs)
    def __str__(self):
        return self.title


class Track(models.Model):
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    artist = models.ForeignKey(Artist, on_delete=models.PROTECT, related_name='tracks')
    featured_artists = models.ManyToManyField(Artist, related_name='featured_tracks', blank=True)
    release = models.ForeignKey(Release, on_delete=models.SET_NULL, related_name='tracks', blank=True, null=True)
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, blank=True, null=True)
    track_number = models.PositiveSmallIntegerField(default=1)
    audio = models.FileField(storage=music_storage, upload_to=audio_path, validators=[validate_music_audio])
    artwork = models.ImageField(storage=music_storage, upload_to=artwork_path, validators=[validate_image_upload], blank=True)
    duration = models.PositiveIntegerField(default=0, editable=False)
    rights_confirmed = models.BooleanField(default=False, help_text='Streaming permission has been reviewed.')
    rights_contact = models.CharField(max_length=250, help_text='Private rights-holder contact or permission reference.')
    rights_notes = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at', '-pk']
    def clean(self):
        if self.audio and not self.audio._committed:
            validate_storage(self.audio)
            self.duration = audio_metadata(self.audio)
        if self.is_published and (not self.audio or not self.duration or not self.rights_confirmed or not self.rights_contact):
            raise ValidationError('Publishing requires validated audio, streaming permission, and a rights contact.')
        if self.is_published and self.artist_id and not self.artist.is_published:
            raise ValidationError('Publish the artist before publishing this track.')
        if self.is_published and self.release_id and (not self.release.is_published or not self.release.artist.is_published):
            raise ValidationError('Publish the release and its artist before publishing this track.')
    def save(self, *args, **kwargs):
        self.clean()
        if not self.slug:
            self.slug = unique_slug(self, self.title)
        super().save(*args, **kwargs)
    @property
    def cover_url(self):
        cover = self.artwork or (self.release.artwork if self.release_id else None)
        return cover.url if cover else ''
    @property
    def length_label(self):
        return f'{self.duration // 60}:{self.duration % 60:02d}'
    def __str__(self):
        return f'{self.title} — {self.artist}'


class MusicSubmission(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='music_submissions')
    artist_name = models.CharField(max_length=160)
    title = models.CharField(max_length=180)
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, blank=True, null=True)
    audio = models.FileField(storage=music_storage, upload_to=audio_path, validators=[validate_music_audio])
    artwork = models.ImageField(storage=music_storage, upload_to=artwork_path, validators=[validate_image_upload], blank=True)
    duration = models.PositiveIntegerField(default=0, editable=False)
    rights_confirmed = models.BooleanField(default=False)
    rights_contact = models.CharField(max_length=250)
    rights_notes = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')
    review_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_track = models.OneToOneField(Track, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at', '-pk']
    def clean(self):
        if self.audio and not self.audio._committed:
            validate_storage(self.audio)
            self.duration = audio_metadata(self.audio)
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    @transaction.atomic
    def approve(self, reviewer, artist):
        if not reviewer.has_perm('music.change_musicsubmission') or not reviewer.has_perm('music.add_track'):
            raise ValidationError('Music review permission is required.')
        submission = type(self).objects.select_for_update().get(pk=self.pk)
        if submission.status != 'pending':
            raise ValidationError('This submission has already been reviewed.')
        if not submission.rights_confirmed or not artist.is_published:
            raise ValidationError('Verify streaming permission and select a published artist.')
        track = Track.objects.create(title=submission.title, artist=artist, audio=submission.audio.name,
            artwork=submission.artwork.name, duration=submission.duration, genre=submission.genre,
            rights_confirmed=True, rights_contact=submission.rights_contact, rights_notes=submission.rights_notes,
            is_published=True)
        submission.status = 'approved'
        submission.approved_track = track
        submission.reviewed_by = reviewer
        submission.reviewed_at = timezone.now()
        submission.save()
        return track
    def __str__(self):
        return f'{self.artist_name} / {self.title}'


class SavedTrack(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='saves')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'track'], name='music_unique_saved_track')]


class Playlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='music_playlists')
    title = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return self.title


class PlaylistItem(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='items')
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    position = models.PositiveIntegerField(default=0)
    class Meta:
        ordering = ['position', 'pk']
        constraints = [models.UniqueConstraint(fields=['playlist', 'track'], name='music_unique_playlist_track')]
