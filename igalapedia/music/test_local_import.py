import io
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from .models import Track
from .storage import LocalMusicStorage, _backend
from .tests import test_audio


class LocalImportTests(TestCase):
    def test_import_copies_audio_and_creates_playable_record_without_duplicates(self):
        with TemporaryDirectory() as folder:
            source = Path(folder) / 'source.wav'
            original = test_audio().read()
            source.write_bytes(original)
            with override_settings(DEBUG=True, ON_RENDER=False, LOCAL_MUSIC_ROOT=Path(folder) / 'music',
                                   MUSIC_AUDIO_STORAGE='music.storage.LocalMusicStorage'):
                _backend.cache_clear()
                with patch.object(Track._meta.get_field('audio'), 'storage', LocalMusicStorage()):
                    options = dict(title='Local song', artist='Local artist', publish_for_local_testing=True,
                                   stdout=io.StringIO())
                    call_command('import_local_music', str(source), **options)
                    track = Track.objects.get()
                    self.assertEqual(source.read_bytes(), original)
                    self.assertEqual(Path(track.audio.path).read_bytes(), original)
                    self.assertTrue(track.artist.is_published)
                    self.assertEqual(track.duration, 2)
                    self.assertEqual(self.client.get(f'/music/api/tracks/{track.pk}/play/').status_code, 200)
                    with self.assertRaises(CommandError):
                        call_command('import_local_music', str(source), **options)
                    self.assertEqual(Track.objects.count(), 1)
                _backend.cache_clear()

    def test_import_rejects_nonlocal_storage(self):
        with self.assertRaisesMessage(CommandError, 'local-only'):
            call_command('import_local_music', 'missing.mp3', title='Song', artist='Artist')

    def test_local_storage_cannot_be_used_on_render(self):
        with override_settings(DEBUG=True, ON_RENDER=True):
            with self.assertRaises(ImproperlyConfigured):
                LocalMusicStorage()
