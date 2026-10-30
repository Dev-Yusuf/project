from botocore.exceptions import BotoCoreError, ClientError
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError

from music.storage import music_storage


class Command(BaseCommand):
    help = 'Validate cloud music configuration; optionally check bucket access without uploading files.'
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument('--remote', action='store_true', help='Make a read-only HeadBucket request.')

    def handle(self, *args, **options):
        storage = music_storage()
        if not hasattr(storage, 'configured'):
            raise CommandError('This command requires the cloud music backend, not local/test storage.')
        try:
            storage.configured()
        except ImproperlyConfigured as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f'Music storage configuration is complete ({type(storage).__name__}).')
        if options['remote']:
            try:
                storage.connection.meta.client.head_bucket(Bucket=storage.bucket_name)
            except (BotoCoreError, ClientError) as exc:
                raise CommandError(
                    'Cannot access the music bucket. Check its name, endpoint, credentials, '
                    'bucket-scoped token permissions, and network access.'
                ) from exc
            self.stdout.write(self.style.SUCCESS('Music bucket is reachable. No files were uploaded or changed.'))
        else:
            self.stdout.write('No network requests made. Use --remote to check bucket access.')
