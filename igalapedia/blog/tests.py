from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase

from .forms import BlogPostForm, BlogPostAdminForm
from .models import BlogPost
from .sanitization import sanitize_blog_html


class BlogHtmlTests(SimpleTestCase):
    def test_removes_active_content_and_dangerous_urls(self):
        payloads = [
            '<script>alert(1)</script><p>Text</p>',
            '<img src="/image.png" onerror="alert(1)">',
            '<a href="jav&#x61;script:alert(1)">Link</a>',
            '<a href="data:text/html,bad">Link</a>',
            '<svg onload="alert(1)"><script>alert(1)</script></svg>',
            '<iframe srcdoc="bad"></iframe><object data="bad"></object>',
            '<p style="background:url(javascript:alert(1))" onclick="alert(1)">Text</p>',
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                cleaned = sanitize_blog_html(payload)
                for forbidden in ('<script', 'onerror', 'onclick', 'onload',
                                  'javascript:', 'data:', '<svg', '<iframe',
                                  '<object', 'style='):
                    self.assertNotIn(forbidden, cleaned)

    def test_preserves_normal_rich_text(self):
        html = ('<h2>Igala</h2><p><strong>Language</strong> <em>and culture</em></p>'
                '<ul><li>History</li></ul><a href="https://example.com">Source</a>'
                '<img src="/media/image.png" alt="Portrait">'
                '<table><tbody><tr><td colspan="2">Word</td></tr></tbody></table>')
        cleaned = sanitize_blog_html(html)
        for fragment in ('<h2>Igala</h2>', '<strong>Language</strong>',
                         '<ul><li>History</li></ul>', 'href="https://example.com"',
                         'src="/media/image.png"', '<td colspan="2">Word</td>'):
            self.assertIn(fragment, cleaned)
        self.assertIn('rel="noopener noreferrer"', cleaned)
        self.assertEqual(sanitize_blog_html(cleaned), cleaned)

    def test_forms_sanitize_submitted_html_and_legacy_editor_content(self):
        payload = '<p>Hello</p><script>alert(1)</script>'
        form = BlogPostForm(data={'title': 'Hello', 'body': payload, 'status': 'draft'})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['body'], '<p>Hello</p>')
        post = BlogPost(title='Legacy', body=payload)
        for form_class in (BlogPostForm, BlogPostAdminForm):
            self.assertEqual(form_class(instance=post).initial['body'], '<p>Hello</p>')
        self.assertIn('author', BlogPostAdminForm().fields)
        self.assertIn('is_hidden', BlogPostAdminForm().fields)


class BlogHtmlPersistenceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='writer')

    def test_model_save_sanitizes_content(self):
        post = BlogPost.objects.create(
            author=self.user, title='Safe post',
            body='<p>Hello</p><script>alert(1)</script>',
        )
        post.refresh_from_db()
        self.assertEqual(post.body, '<p>Hello</p>')

    def test_detail_template_sanitizes_legacy_content_without_rewriting_it(self):
        post = BlogPost.objects.create(author=self.user, title='Legacy post', body='Text')
        payload = '<p>Legacy text</p><img src="/photo.png" onerror="legacyAttack()">'
        BlogPost.objects.filter(pk=post.pk).update(body=payload)
        post.refresh_from_db()
        html = render_to_string('blog/blog_detail.html', {'post': post})
        self.assertIn('<p>Legacy text</p>', html)
        self.assertNotIn('legacyAttack', html)
        post.refresh_from_db()
        self.assertEqual(post.body, payload)


class BlogVisibilityTests(TestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(username='author')
        self.reader = get_user_model().objects.create_user(username='reader')
        self.post = BlogPost.objects.create(author=self.author, title='Visibility', body='Text')
        self.client.force_login(self.reader)

    def interact(self, endpoint):
        from django.urls import reverse
        return self.client.post(reverse('blog:' + endpoint, kwargs={'slug': self.post.slug}),
                                {'body': 'Comment', 'reason': 'Report'})

    def test_non_author_cannot_interact_with_draft_or_hidden_post(self):
        from .models import BlogPostLike, BlogPostComment, BlogPostReport
        for status, hidden in [('draft', False), ('published', True)]:
            self.post.status, self.post.is_hidden = status, hidden
            self.post.save()
            for endpoint in ('blog_like_toggle', 'blog_comment_add', 'blog_report'):
                with self.subTest(status=status, endpoint=endpoint):
                    self.assertEqual(self.interact(endpoint).status_code, 404)
        self.assertFalse(BlogPostLike.objects.exists())
        self.assertFalse(BlogPostComment.objects.exists())
        self.assertFalse(BlogPostReport.objects.exists())

    def test_public_post_remains_interactive(self):
        self.post.status = 'published'
        self.post.save()
        self.assertEqual(self.interact('blog_like_toggle').status_code, 200)
        self.assertEqual(self.interact('blog_comment_add').status_code, 302)
        self.assertEqual(self.interact('blog_report').status_code, 302)

    def test_author_can_access_draft_but_not_hidden_post(self):
        self.client.force_login(self.author)
        self.assertEqual(self.interact('blog_like_toggle').status_code, 200)
        self.post.is_hidden = True
        self.post.save()
        self.assertEqual(self.interact('blog_like_toggle').status_code, 404)
