"""Local SQLite and filesystem uploads; run with --settings=igalapedia.development_settings."""
from .settings import *

if ON_RENDER:
    raise ImproperlyConfigured('Development settings cannot be used on Render.')

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MUSIC_AUDIO_STORAGE = 'music.storage.LocalMusicStorage'
LOCAL_MUSIC_ROOT = MEDIA_ROOT / 'music'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
