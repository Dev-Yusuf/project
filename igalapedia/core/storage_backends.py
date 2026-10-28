"""Public media storage using the configured Supabase bucket and CDN URL."""
from urllib.parse import quote

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, SuspiciousFileOperation
from storages.backends.s3boto3 import S3Boto3Storage


class SupabaseMediaStorage(S3Boto3Storage):
    default_acl = 'public-read'
    file_overwrite = False

    def url(self, name, parameters=None, expire=None, http_method=None):
        base = settings.SUPABASE_PUBLIC_MEDIA_URL
        if not base:
            raise ImproperlyConfigured('Configure SUPABASE_URL or SUPABASE_PUBLIC_MEDIA_URL for media URLs.')
        if any(part in ('.', '..') for part in name.replace('\\', '/').split('/')):
            raise SuspiciousFileOperation('Invalid media path.')
        return base.rstrip('/') + '/' + quote(name.lstrip('/'), safe='/')
