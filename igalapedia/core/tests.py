from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from .validators import validate_audio_upload, validate_image_upload, validate_pdf_upload


class UploadValidationTests(SimpleTestCase):
    def test_rejects_disguised_files(self):
        for validator, name in [(validate_audio_upload, 'speech.mp3'),
                                (validate_image_upload, 'photo.png'),
                                (validate_pdf_upload, 'book.pdf')]:
            with self.subTest(name=name), self.assertRaises(ValidationError):
                validator(SimpleUploadedFile(name, b'<html>bad</html>'))

    def test_rejects_oversized_files_and_svg(self):
        file = SimpleUploadedFile('book.pdf', b'%PDF-1.7')
        file.size = 26 * 1024 * 1024
        with self.assertRaises(ValidationError):
            validate_pdf_upload(file)
        with self.assertRaises(ValidationError):
            validate_image_upload(SimpleUploadedFile('photo.svg', b'<svg></svg>'))

    def test_accepts_supported_headers_and_preserves_stream_position(self):
        stream = BytesIO()
        Image.new('RGB', (2, 2)).save(stream, format='PNG')
        cases = [(validate_pdf_upload, 'book.pdf', b'%PDF-1.7 content'),
                 (validate_audio_upload, 'speech.wav', b'RIFF1234WAVEdata'),
                 (validate_image_upload, 'photo.png', stream.getvalue())]
        for validator, name, content in cases:
            file = SimpleUploadedFile(name, content)
            file.seek(2)
            validator(file)
            self.assertEqual(file.tell(), 2)


class StorageConfigurationTests(SimpleTestCase):
    def test_storage_uses_configured_bucket_and_encodes_names(self):
        from django.test import override_settings
        from .storage_backends import SupabaseMediaStorage
        with override_settings(AWS_STORAGE_BUCKET_NAME='custom-media',
                               SUPABASE_PUBLIC_MEDIA_URL='https://cdn.example.com/custom-media/'):
            storage = SupabaseMediaStorage()
            self.assertEqual(storage.bucket_name, 'custom-media')
            self.assertEqual(storage.url('images/hello world#.png'),
                             'https://cdn.example.com/custom-media/images/hello%20world%23.png')

    def test_storage_does_not_allow_traversal_paths(self):
        from django.test import override_settings
        from django.core.exceptions import SuspiciousFileOperation
        from .storage_backends import SupabaseMediaStorage
        with override_settings(SUPABASE_PUBLIC_MEDIA_URL='https://cdn.example.com/media/'):
            with self.assertRaises(SuspiciousFileOperation):
                SupabaseMediaStorage().url('../private.pdf')


class SharedRichTextTests(SimpleTestCase):
    def test_legacy_rendering_sanitizes_and_preserves_formatting(self):
        from django.template import Context, Template
        html = Template('{% load content_safety %}{{ body|sanitized_html }}').render(
            Context({'body': '<p>Hello</p><script>attack()</script>'}))
        self.assertEqual(html, '<p>Hello</p>')

    def test_history_and_profile_forms_sanitize_editor_input(self):
        from history.forms import HistorySubmissionForm
        from history.models import PendingHistory
        from library.forms import HallOfFameSubmissionForm
        from library.models import PendingHallOfFameProfile
        payload = '<p>Text</p><img src=x onerror=attack()>'
        cases = [(HistorySubmissionForm, PendingHistory(content_english=payload), 'content_english'),
                 (HallOfFameSubmissionForm, PendingHallOfFameProfile(bio=payload), 'bio')]
        for form_class, instance, name in cases:
            form = form_class(instance=instance)
            self.assertNotIn('onerror', form.initial[name])
            bound = form_class(data={name: payload})
            self.assertNotIn('onerror', bound[name].value())


class ProductionSettingsTests(SimpleTestCase):
    def test_transaction_pooler_disables_persistent_connections_and_cursors(self):
        import os
        import runpy
        from pathlib import Path
        from unittest.mock import patch
        path = Path(__file__).resolve().parents[1] / 'igalapedia' / 'settings.py'
        for port in (5432, 6543):
            with self.subTest(port=port), patch.dict(os.environ, {
                'RENDER': 'false',
                'DATABASE_URL': f'postgresql://postgres.example:placeholder@aws-1-eu-west-1.pooler.supabase.com:{port}/postgres',
            }):
                database = runpy.run_path(str(path))['DATABASES']['default']
                self.assertEqual(database['CONN_MAX_AGE'], 0 if port == 6543 else 600)
                self.assertEqual(database.get('DISABLE_SERVER_SIDE_CURSORS', False), port == 6543)

    def test_render_disables_debug_and_requires_a_strong_secret(self):
        import os
        import runpy
        from pathlib import Path
        from unittest.mock import patch
        from django.core.exceptions import ImproperlyConfigured
        path = Path(__file__).resolve().parents[1] / 'igalapedia' / 'settings.py'
        env = {'RENDER': 'true', 'DEBUG': 'True',
               'SECRET_KEY': 'test-only-strong-production-configuration-key-with-at-least-50-chars',
               'RENDER_EXTERNAL_HOSTNAME': 'example.onrender.com',
               'DATABASE_URL': 'postgresql://placeholder:placeholder@localhost/db'}
        with patch.dict(os.environ, env):
            config = runpy.run_path(str(path))
            self.assertFalse(config['DEBUG'])
            self.assertTrue(config['SECURE_SSL_REDIRECT'])
            self.assertTrue(config['SESSION_COOKIE_SECURE'])
            self.assertTrue(config['CSRF_COOKIE_SECURE'])
            self.assertIn('example.onrender.com', config['ALLOWED_HOSTS'])
            with patch.dict(os.environ, {'SECRET_KEY': 'weak'}):
                with self.assertRaises(ImproperlyConfigured):
                    runpy.run_path(str(path))
