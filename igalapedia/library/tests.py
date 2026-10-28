from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .forms import BookSubmissionForm
from .models import Book, BookAccessRequest


class BookAccessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='reader')
        self.client.force_login(self.user)
        self.book = Book.objects.create(title='Private book', access_type='request', author_email='author@example.com')
        self.url = reverse('library:request_book_access', kwargs={'slug': self.book.slug})

    def test_request_only_books_cannot_reference_public_downloads(self):
        for field, value in [('file', 'library/books/exposed.pdf'), ('external_url', 'https://example.com/book.pdf')]:
            book = Book(title='Unsafe', access_type='request', author_email='author@example.com')
            setattr(book, field, value)
            with self.subTest(field=field), self.assertRaises(ValidationError):
                book.save()

    def test_invalid_email_is_not_saved(self):
        response = self.client.post(self.url, {'email': 'not-an-email'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(BookAccessRequest.objects.exists())

    def test_email_failure_keeps_request_and_reports_failure_honestly(self):
        with patch('library.views.send_mail', side_effect=RuntimeError('SMTP unavailable')):
            with self.assertLogs('library.views', level='ERROR'):
                response = self.client.post(self.url, {'email': 'reader@example.com'})
        self.assertTrue(BookAccessRequest.objects.filter(user=self.user, book=self.book).exists())
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertTrue(any('could not email' in message for message in messages))

    def test_email_success_and_duplicate_request(self):
        with patch('library.views.send_mail', return_value=1) as send:
            response = self.client.post(self.url, {'email': 'reader@example.com'})
            self.client.post(self.url, {'email': 'reader@example.com'})
        self.assertEqual(BookAccessRequest.objects.count(), 1)
        send.assert_called_once()
        self.assertTrue(any('notification was sent' in str(m) for m in get_messages(response.wsgi_request)))

    def test_upload_form_rejects_disguised_pdf(self):
        form = BookSubmissionForm(data={'title': 'Book', 'language': 'ig'},
                                  files={'file': SimpleUploadedFile('book.pdf', b'<html>Bad</html>')})
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)
