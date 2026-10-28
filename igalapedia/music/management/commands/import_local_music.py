from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from mutagen import File as ReadAudio
from mutagen.mp3 import MP3

from music.models import Artist, Track
from music.storage import LocalMusicStorage, music_storage


class Command(BaseCommand):
    help = 'Import a recording into the local SQLite catalogue and music folder only.'

    def add_arguments(self, parser):
        parser.add_argument('file')
        parser.add_argument('--title', required=True)
        parser.add_argument('--artist', required=True)
        parser.add_argument('--publish-for-local-testing', action='store_true')

    def handle(self, *args, **options):
        storage = music_storage()
        if (not settings.DEBUG or getattr(settings, 'ON_RENDER', False)
                or connection.vendor != 'sqlite' or not isinstance(storage, LocalMusicStorage)):
            raise CommandError('Use --settings=igalapedia.development_settings; this command is local-only.')
        source = Path(options['file']).resolve()
        if not source.is_file():
            raise CommandError('The source audio file does not exist.')
        if source.stat().st_size > settings.MUSIC_MAX_UPLOAD_BYTES:
            raise CommandError('Music files must be 25 MB or smaller.')
        title, artist_name = options['title'].strip(), options['artist'].strip()
        if not title or not artist_name:
            raise CommandError('Title and artist cannot be empty.')
        if Track.objects.filter(title=title, artist__name=artist_name).exists():
            raise CommandError('This title and artist already exist in the local catalogue.')
        filename = source.name
        if source.suffix.lower() == '.mpeg':
            if not isinstance(ReadAudio(source), MP3):
                raise CommandError('Only MPEG files containing MP3 audio can be imported as MP3.')
            filename = source.with_suffix('.mp3').name
        publish = options['publish_for_local_testing']
        track = None
        try:
            with transaction.atomic():
                artist = Artist.objects.filter(name=artist_name).first()
                if artist is None:
                    artist = Artist.objects.create(name=artist_name, is_published=publish)
                elif publish and not artist.is_published:
                    artist.is_published = True
                    artist.save(update_fields=['is_published'])
                track = Track(title=title, artist=artist, is_published=publish,
                              rights_confirmed=publish,
                              rights_contact='User-provided recording for local testing only',
                              rights_notes='Local playback testing only. Production streaming permission has not been reviewed.')
                with source.open('rb') as handle:
                    track.audio = File(handle, name=filename)
                    track.full_clean()
                    track.save()
        except Exception:
            if track and track.audio and track.audio._committed:
                storage.delete(track.audio.name)
            raise
        self.stdout.write(self.style.SUCCESS(
            f'Imported {track.title} by {artist.name} ({track.length_label}) into local SQLite.'))
        self.stdout.write(f'Audio: {track.audio.path}')
        self.stdout.write(f'Local page: /music/tracks/{track.slug}/')
