"""Isolated test configuration: no production database, uploads, or SMTP."""
import os

# Seed harmless configuration before base settings can load a local .env.
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('SECRET_KEY', 'test-only-secret-key-with-enough-entropy-for-local-regressions')
from .settings import *

SECRET_KEY = 'test-only-secret-key-with-enough-entropy-for-local-regressions'
DEBUG = False
DATABASES = {'default': dj_database_url.parse(os.environ['TEST_DATABASE_URL'], ssl_require=False)
             if os.environ.get('TEST_DATABASE_URL')
             else {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
DEFAULT_FILE_STORAGE = 'django.core.files.storage.InMemoryStorage'
MEDIA_ROOT = ''
MEDIA_URL = '/media/'
MUSIC_AUDIO_STORAGE = 'django.core.files.storage.InMemoryStorage'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
ALLOWED_HOSTS = ['testserver', 'localhost']

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
