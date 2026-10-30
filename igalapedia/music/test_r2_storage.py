from io import StringIO
import os
import runpy
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from botocore.stub import ANY, Stubber
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command, CommandError
from django.test import SimpleTestCase, override_settings
from django.conf import settings

from .models import validate_storage
from .storage import PrivateMusicStorage, R2MusicStorage


@override_settings(
    R2_BUCKET_NAME='music-test',
    R2_ENDPOINT_URL='https://' + 'a' * 32 + '.r2.cloudflarestorage.com',
    R2_ACCESS_KEY_ID='r2-test-access-key',
    R2_SECRET_ACCESS_KEY='r2-test-secret-key',
    R2_REGION_NAME='auto',
    MUSIC_PLAYBACK_URL_SECONDS=3600,
    AWS_STORAGE_BUCKET_NAME='public-media',
    AWS_ACCESS_KEY_ID='supabase-test-key',
    AWS_SECRET_ACCESS_KEY='supabase-test-secret',
    AWS_S3_ENDPOINT_URL='https://example.supabase.co/storage/v1/s3',
    AWS_S3_REGION_NAME='eu-west-1',
    AWS_S3_CUSTOM_DOMAIN='images.example.com',
    AWS_DEFAULT_ACL='public-read',
    AWS_QUERYSTRING_AUTH=False,
    AWS_LOCATION='public',
    AWS_S3_OBJECT_PARAMETERS={'ACL': 'public-read'},
)
class R2StorageTests(SimpleTestCase):
    def test_signed_url_uses_only_private_r2_settings(self):
        storage = R2MusicStorage()
        parsed = urlsplit(storage.url('audio/a song.mp3'))
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.hostname, 'a' * 32 + '.r2.cloudflarestorage.com')
        self.assertEqual(parsed.path, '/music-test/audio/a%20song.mp3')
        self.assertEqual(query['X-Amz-Algorithm'], ['AWS4-HMAC-SHA256'])
        self.assertEqual(query['X-Amz-Expires'], ['3600'])
        self.assertTrue(query['X-Amz-Credential'][0].startswith('r2-test-access-key/'))
        self.assertIn('/auto/s3/aws4_request', query['X-Amz-Credential'][0])
        self.assertIn('X-Amz-Signature', query)
        self.assertNotIn('X-Amz-Security-Token', query)
        self.assertIsNone(storage.default_acl)
        self.assertIsNone(storage.custom_domain)
        self.assertFalse(storage.file_overwrite)
        self.assertEqual(storage.secret_key, 'r2-test-secret-key')
        self.assertEqual(storage.client_config.s3['addressing_style'], 'path')
        self.assertTrue(storage.verify)
        self.assertNotIn('supabase', storage.url('audio/test.mp3', expire=120))
        self.assertEqual(parse_qs(urlsplit(storage.url('audio/test.mp3', expire=120)).query)
                         ['X-Amz-Expires'], ['120'])

    def test_missing_r2_configuration_never_uses_supabase_or_ambient_credentials(self):
        for setting in ('R2_BUCKET_NAME', 'R2_ENDPOINT_URL', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY'):
            with self.subTest(setting=setting), self.settings(**{setting: ''}), patch('boto3.Session') as session:
                storage = R2MusicStorage()
                for operation in (
                    lambda: storage.url('audio/test.mp3'),
                    lambda: storage.exists('audio/test.mp3'),
                    lambda: storage.open('audio/test.mp3'),
                    lambda: storage.size('audio/test.mp3'),
                    lambda: storage.delete('audio/test.mp3'),
                    lambda: storage.save('audio/test.mp3', SimpleUploadedFile('test.mp3', b'test')),
                ):
                    with self.assertRaisesMessage(ImproperlyConfigured, setting):
                        operation()
                session.assert_not_called()

    def test_invalid_endpoints_are_rejected_before_creating_client(self):
        for endpoint in ('http://account.r2.cloudflarestorage.com', 'https://example.com',
                         'https://account.r2.cloudflarestorage.com/music-test',
                         'https://account.r2.cloudflarestorage.com?token=test',
                         'https://user:password@account.r2.cloudflarestorage.com',
                         'https://account.r2.cloudflarestorage.com:8080', 'https://['):
            with self.subTest(endpoint=endpoint), self.settings(R2_ENDPOINT_URL=endpoint), patch('boto3.Session') as session:
                with self.assertRaisesMessage(ImproperlyConfigured, 'R2_ENDPOINT_URL'):
                    R2MusicStorage().url('audio/test.mp3')
                session.assert_not_called()

    def test_jurisdiction_endpoint_is_supported(self):
        endpoint = 'https://' + 'a' * 32 + '.eu.r2.cloudflarestorage.com'
        with self.settings(R2_ENDPOINT_URL=endpoint):
            self.assertEqual(urlsplit(R2MusicStorage().url('audio/test.mp3')).netloc,
                             urlsplit(endpoint).netloc)

    def test_upload_routes_to_r2_with_no_public_acl(self):
        storage = R2MusicStorage()
        client = storage.connection.meta.client
        with Stubber(client) as stub:
            stub.add_client_error('head_object', service_error_code='404', http_status_code=404,
                                  expected_params={'Bucket': 'music-test', 'Key': 'audio/test.mp3'})
            stub.add_response('put_object', {'ETag': 'test-etag'}, {
                'Bucket': 'music-test', 'Key': 'audio/test.mp3', 'Body': ANY,
                'ContentType': 'audio/mpeg', 'CacheControl': 'private, max-age=3600',
            })
            saved = storage.save('audio/test.mp3', SimpleUploadedFile('test.mp3', b'test', content_type='audio/mpeg'))
            self.assertEqual(saved, 'audio/test.mp3')
            stub.assert_no_pending_responses()
    def test_unconfigured_r2_becomes_existing_friendly_validation_error(self):
        with self.settings(R2_SECRET_ACCESS_KEY=''):
            upload = SimpleUploadedFile('test.mp3', b'test')
            upload.storage = R2MusicStorage()
            with self.assertRaisesMessage(ValidationError, 'Music uploads are not available yet'):
                validate_storage(upload)

    def test_supabase_music_backend_remains_available(self):
        with self.settings(MUSIC_STORAGE_BUCKET='music-private'):
            storage = PrivateMusicStorage()
            storage.configured()
            self.assertEqual(storage.endpoint_url, 'https://example.supabase.co/storage/v1/s3')
            self.assertEqual(storage.bucket_name, 'music-private')
            self.assertEqual(storage.access_key, 'supabase-test-key')

    def test_check_command_is_offline_unless_remote_requested(self):
        storage = R2MusicStorage()
        with patch('music.management.commands.check_music_storage.music_storage', return_value=storage), patch('boto3.Session') as session:
            output = StringIO()
            call_command('check_music_storage', stdout=output)
            self.assertIn('No network requests', output.getvalue())
            session.assert_not_called()

    def test_check_command_remote_uses_read_only_head_bucket(self):
        storage = R2MusicStorage()
        with Stubber(storage.connection.meta.client) as stub:
            stub.add_response('head_bucket', {}, {'Bucket': 'music-test'})
            with patch('music.management.commands.check_music_storage.music_storage', return_value=storage):
                call_command('check_music_storage', remote=True, stdout=StringIO())
            stub.assert_no_pending_responses()

    def test_check_command_hides_remote_error_details(self):
        storage = R2MusicStorage()
        with Stubber(storage.connection.meta.client) as stub:
            stub.add_client_error('head_bucket', service_error_code='AccessDenied',
                                  service_message='sensitive-service-detail', http_status_code=403,
                                  expected_params={'Bucket': 'music-test'})
            with patch('music.management.commands.check_music_storage.music_storage', return_value=storage):
                with self.assertRaises(CommandError) as caught:
                    call_command('check_music_storage', remote=True, stdout=StringIO())
                self.assertNotIn('sensitive-service-detail', str(caught.exception))
            stub.assert_no_pending_responses()


class MusicProviderSettingsTests(SimpleTestCase):
    def load_settings(self, **variables):
        environment = {'DATABASE_URL': 'sqlite:///:memory:', 'SECRET_KEY': 'test-only-settings-key', **variables}
        with patch.dict(os.environ, environment, clear=True), patch('dotenv.load_dotenv'):
            return runpy.run_path(str(settings.BASE_DIR / 'igalapedia' / 'settings.py'))

    def test_existing_supabase_configuration_remains_default(self):
        config = self.load_settings()
        self.assertEqual(config['MUSIC_AUDIO_STORAGE'], 'music.storage.PrivateMusicStorage')

    def test_r2_selection_does_not_change_database_or_public_storage(self):
        config = self.load_settings(MUSIC_STORAGE_PROVIDER='r2')
        self.assertEqual(config['MUSIC_AUDIO_STORAGE'], 'music.storage.R2MusicStorage')
        self.assertEqual(config['DEFAULT_FILE_STORAGE'], 'core.storage_backends.SupabaseMediaStorage')
        self.assertEqual(config['DATABASES']['default']['ENGINE'], 'django.db.backends.sqlite3')

    def test_unknown_provider_is_rejected(self):
        with self.assertRaisesMessage(ImproperlyConfigured, 'MUSIC_STORAGE_PROVIDER'):
            self.load_settings(MUSIC_STORAGE_PROVIDER='unknown')
