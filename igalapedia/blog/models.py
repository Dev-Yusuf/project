from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from ckeditor.fields import RichTextField


class BlogPost(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blog_posts'
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=220, blank=True)
    body = RichTextField()
    cover_image = models.ImageField(upload_to='blog_covers/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            i = 1
            while BlogPost.objects.filter(slug=slug).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        if self.status == 'published' and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class BlogPostLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blog_likes'
    )
    post = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'post'], name='unique_blog_like')
        ]

    def __str__(self):
        return f"{self.user.username} likes {self.post.title}"


class BlogPostComment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blog_comments'
    )
    post = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.post.title}"


class BlogGuidelinesAck(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blog_guidelines_ack'
    )
    acknowledged_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} acknowledged at {self.acknowledged_at}"


class BlogPostView(models.Model):
    """Unique view per IP per day (one count per visitor per day)."""
    post = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name='view_records'
    )
    ip_hash = models.CharField(max_length=64)
    viewed_date = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['post', 'ip_hash', 'viewed_date'],
                name='unique_blog_view_per_day'
            )
        ]

    def __str__(self):
        return f"View on {self.post.title}"


class BlogPostReport(models.Model):
    post = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blog_reports'
    )
    reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Report on {self.post.title} by {self.reported_by.username}"
