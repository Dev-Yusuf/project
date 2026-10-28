from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from blog.models import BlogGuidelinesAck


@override_settings(
    ALLOWED_HOSTS=['testserver'],
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
)
class SafeNextRedirectTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='redirect-tester', password='test-password',
        )

    def submit(self, endpoint, destination=None, secure=False):
        self.client.logout()
        if endpoint == 'login':
            data = {'username': self.user.username, 'password': 'test-password'}
        else:
            self.client.force_login(self.user)
            data = {}
        url = reverse(endpoint)
        if destination is not None:
            url += '?' + urlencode({'next': destination})
        response = self.client.post(url, data, secure=secure)
        if endpoint == 'login':
            self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)
        else:
            self.assertTrue(BlogGuidelinesAck.objects.filter(user=self.user).exists())
        return response

    def test_unsafe_destinations_fall_back_after_successful_submission(self):
        destinations = [
            'https://evil.example/phishing', '//evil.example/phishing',
            'https://testserver.evil.example/', 'https://testserver@evil.example/',
            r'/\evil.example/path', '///evil.example/path',
            'javascript:alert(1)', 'data:text/html,bad',
            'https:///evil.example/path', '\x01https://evil.example/',
        ]
        for endpoint, fallback in [('login', 'index'), ('blog:blog_guidelines', 'blog:blog_create')]:
            for destination in destinations:
                with self.subTest(endpoint=endpoint, destination=destination):
                    response = self.submit(endpoint, destination)
                    self.assertEqual(response.status_code, 302)
                    self.assertEqual(response['Location'], reverse(fallback))

    def test_missing_and_blank_destinations_use_defaults(self):
        for endpoint, fallback in [('login', 'index'), ('blog:blog_guidelines', 'blog:blog_create')]:
            for destination in (None, '', '   '):
                with self.subTest(endpoint=endpoint, destination=destination):
                    self.assertEqual(self.submit(endpoint, destination)['Location'], reverse(fallback))

    def test_safe_destinations_are_preserved(self):
        for endpoint in ('login', 'blog:blog_guidelines'):
            for destination in ('/dashboard/?tab=recent', 'https://testserver/dashboard/', '/dictionary/'):
                with self.subTest(endpoint=endpoint, destination=destination):
                    self.assertEqual(self.submit(endpoint, destination)['Location'], destination)

    def test_https_requests_cannot_redirect_to_http(self):
        for endpoint, fallback in [('login', 'index'), ('blog:blog_guidelines', 'blog:blog_create')]:
            with self.subTest(endpoint=endpoint):
                response = self.submit(endpoint, 'http://testserver/dashboard/', secure=True)
                self.assertEqual(response['Location'], reverse(fallback))
                response = self.submit(endpoint, 'https://testserver/dashboard/', secure=True)
                self.assertEqual(response['Location'], 'https://testserver/dashboard/')


class FeedPaginationTests(TestCase):
    def setUp(self):
        from blog.models import BlogPost
        from dictionary.models import Words
        from history.models import HistoryArticle
        self.user = get_user_model().objects.create_user(username='feed-writer')
        for i in range(30):
            Words.objects.create(word=f'Feedword{i}')
        HistoryArticle.objects.create(title='History')
        BlogPost.objects.create(author=self.user, title='Published', body='<p>Body</p>', status='published')
        BlogPost.objects.create(author=self.user, title='Draft', body='Private')
        BlogPost.objects.create(author=self.user, title='Hidden', body='Private', status='published', is_hidden=True)

    def test_pagination_is_complete_and_excludes_nonpublic_posts(self):
        from .feeds_utils import get_feed_items
        first, has_more, total = get_feed_items(0, 12)
        second, _, _ = get_feed_items(12, 12)
        last, has_more_last, _ = get_feed_items(24, 12)
        self.assertEqual(total, 32)
        self.assertTrue(has_more)
        self.assertFalse(has_more_last)
        self.assertEqual(len({item['url'] for item in first + second + last}), 32)
        self.assertNotIn('Draft', [item['title'] for item in first + second + last])

    def test_sql_pages_before_fetching_content(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        from .feeds_utils import get_feed_items
        with CaptureQueriesContext(connection) as queries:
            items, _, _ = get_feed_items(0, 5)
        self.assertEqual(len(items), 5)
        self.assertLessEqual(len(queries), 5)
        page_queries = [q['sql'] for q in queries if 'UNION ALL' in q['sql'] and 'LIMIT 5' in q['sql']]
        self.assertEqual(len(page_queries), 1)

    def test_tied_dates_and_legacy_words_have_stable_order(self):
        from django.utils import timezone
        from dictionary.models import Words
        from .feeds_utils import get_feed_items
        Words.objects.all().update(created_at=None)
        first = get_feed_items(0, 12)[0]
        self.assertEqual(first, get_feed_items(0, 12)[0])
        self.assertEqual(first[-1]['date'].year, 2000)


class RegistrationAndLogoutTests(TestCase):
    def test_registration_failure_does_not_leave_account(self):
        from unittest.mock import patch
        from dictionary.models import ContributionStats
        data = {'username': 'new-member', 'email': 'new@example.com',
                'password1': 'Long-complex-password42!', 'password2': 'Long-complex-password42!'}
        with patch('main.views.ContributionStats.objects.create', side_effect=RuntimeError('DB failure')):
            with self.assertLogs('main.views', level='ERROR'):
                response = self.client.post(reverse('register'), data)
        self.assertEqual(response.status_code, 503)
        self.assertFalse(get_user_model().objects.filter(username='new-member').exists())
        self.assertFalse(ContributionStats.objects.exists())

    def test_registration_creates_account_and_stats(self):
        from dictionary.models import ContributionStats
        response = self.client.post(reverse('register'), {
            'username': 'new-member', 'email': 'new@example.com',
            'password1': 'Long-complex-password42!', 'password2': 'Long-complex-password42!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContributionStats.objects.get().user.username, 'new-member')

    def test_logout_requires_post_and_csrf(self):
        from django.test import Client
        user = get_user_model().objects.create_user(username='logout-user')
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        self.assertEqual(client.get(reverse('logout')).status_code, 405)
        self.assertIn('_auth_user_id', client.session)
        self.assertEqual(client.post(reverse('logout')).status_code, 403)
        client.get(reverse('dashboard'))
        token = client.cookies['csrftoken'].value
        self.assertEqual(client.post(reverse('logout'), {'csrfmiddlewaretoken': token}).status_code, 302)
        self.assertNotIn('_auth_user_id', client.session)


class SanitizedFixtureTests(TestCase):
    def test_fixture_loads_without_real_accounts_or_sessions(self):
        from django.contrib.sessions.models import Session
        from django.core.management import call_command
        from django.contrib.admin.models import LogEntry
        call_command('loaddata', 'data.json', verbosity=0)
        self.assertTrue(get_user_model().objects.exists())
        for user in get_user_model().objects.all():
            self.assertFalse(user.has_usable_password())
            self.assertFalse(user.is_staff)
            self.assertFalse(user.is_superuser)
            self.assertFalse(user.is_active)
            self.assertEqual(user.email, '')
        self.assertFalse(Session.objects.exists())
        self.assertFalse(LogEntry.objects.exists())
        self.assertEqual(self.client.get(reverse('index')).status_code, 200)
