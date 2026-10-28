from functools import lru_cache
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


@lru_cache(maxsize=4)
def _backend(path):
    return import_string(path)()


def music_storage():
    return _backend(settings.MUSIC_AUDIO_STORAGE)
