from functools import lru_cache
import re
from urllib.parse import urlsplit
from botocore.config import Config
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage
from django.utils.module_loading import import_string
from storages.backends.s3 import S3Storage


class LocalMusicStorage(FileSystemStorage):
    """Filesystem audio for local development only."""
    def __init__(self):
        if not settings.DEBUG or getattr(settings, 'ON_RENDER', False):
            raise ImproperlyConfigured('Local music storage requires local development settings.')
        super().__init__(location=settings.LOCAL_MUSIC_ROOT, base_url='/media/music/')


class PrivateMusicStorage(S3Storage):
    """Use S3 presigned URLs and a separate private bucket, never public media URLs."""
    def get_default_settings(self):
        options = super().get_default_settings()
        options.update(bucket_name=settings.MUSIC_STORAGE_BUCKET, default_acl=None,
                       querystring_auth=True, custom_domain=None, file_overwrite=False)
        return options

    def configured(self):
        if not self.bucket_name or self.bucket_name == settings.AWS_STORAGE_BUCKET_NAME:
            raise ImproperlyConfigured('Set MUSIC_STORAGE_BUCKET to a separate private Supabase bucket.')

    def _save(self, name, content):
        self.configured()
        return super()._save(name, content)

    def url(self, name, parameters=None, expire=None, http_method=None):
        self.configured()
        return super().url(name, parameters=parameters,
                           expire=expire or settings.MUSIC_PLAYBACK_URL_SECONDS, http_method=http_method)


class R2MusicStorage(PrivateMusicStorage):
    """Private R2 audio, isolated from the public Supabase media configuration."""
    def get_default_settings(self):
        options = super().get_default_settings()
        client_options = {'signature_version': 's3v4', 's3': {'addressing_style': 'path'}}
        # Newer AWS SDKs add optional streaming checksums; keep R2 requests compatible.
        # The SDK pinned in requirements predates these configuration options.
        if hasattr(Config(), 'request_checksum_calculation'):
            client_options.update(request_checksum_calculation='when_required',
                                  response_checksum_validation='when_required')
        options.update(
            bucket_name=settings.R2_BUCKET_NAME,
            access_key=settings.R2_ACCESS_KEY_ID,
            secret_key=settings.R2_SECRET_ACCESS_KEY,
            endpoint_url=settings.R2_ENDPOINT_URL,
            region_name=settings.R2_REGION_NAME,
            security_token=None, session_profile=None, client_config=Config(**client_options),
            signature_version='s3v4', addressing_style='path',
            cloudfront_key=None, cloudfront_key_id=None, location='',
            object_parameters={'CacheControl': 'private, max-age=3600'},
            gzip=False, use_ssl=True, verify=True,
        )
        return options

    def configured(self):
        required = {
            'R2_BUCKET_NAME': self.bucket_name,
            'R2_ENDPOINT_URL': self.endpoint_url,
            'R2_ACCESS_KEY_ID': self.access_key,
            'R2_SECRET_ACCESS_KEY': self.secret_key,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ImproperlyConfigured('Set music storage variables: ' + ', '.join(missing) + '.')
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,61}[a-z0-9]', self.bucket_name):
            raise ImproperlyConfigured('R2_BUCKET_NAME must be a valid Cloudflare R2 bucket name.')
        try:
            endpoint = urlsplit(self.endpoint_url)
            valid = (endpoint.scheme == 'https'
                     and (endpoint.hostname or '').endswith('.r2.cloudflarestorage.com')
                     and endpoint.port in (None, 443)
                     and endpoint.path in ('', '/')
                     and not (endpoint.query or endpoint.fragment or endpoint.username or endpoint.password))
        except ValueError:
            valid = False
        if not valid:
            raise ImproperlyConfigured(
                'R2_ENDPOINT_URL must be the HTTPS S3 account endpoint from Cloudflare, '
                'without a bucket path, query string, or credentials.'
            )

    @property
    def connection(self):
        # Block reads, writes, and ambient AWS credential discovery until R2 is configured.
        self.configured()
        return super().connection


@lru_cache(maxsize=4)
def _backend(path):
    return import_string(path)()


def music_storage():
    return _backend(settings.MUSIC_AUDIO_STORAGE)
