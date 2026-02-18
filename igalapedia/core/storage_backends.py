"""
Custom storage backend so FileField/ImageField .url returns Supabase public CDN URL.
"""
from storages.backends.s3boto3 import S3Boto3Storage


class SupabaseMediaStorage(S3Boto3Storage):
    bucket_name = "media"
    default_acl = "public-read"
    file_overwrite = False

    def url(self, name):
        return f"https://sbuhryoosnqycbaybjjx.supabase.co/storage/v1/object/public/media/{name}"
