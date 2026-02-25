from django.db import models, transaction
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from ckeditor.fields import RichTextField


class PendingHistory(models.Model):
    """User-submitted history article awaiting admin approval."""

    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    title = models.CharField(max_length=200)
    excerpt = models.CharField(max_length=300, blank=True)
    thumbnail = models.ImageField(upload_to='history_thumbnails/', blank=True, null=True)
    content_english = RichTextField(blank=True)
    content_igala = RichTextField(blank=True)
    audio_english = models.FileField(upload_to='history_audio/', blank=True, null=True)
    audio_igala = models.FileField(upload_to='history_audio/', blank=True, null=True)

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pending_history_submissions'
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_histories'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_notes = models.TextField(blank=True, null=True)

    approved_article = models.OneToOneField(
        'HistoryArticle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_submission'
    )

    class Meta:
        verbose_name = 'Pending History'
        verbose_name_plural = 'Pending Histories'
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"


class HistoryArticle(models.Model):
    """Published history article (approved content)."""

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=220, blank=True)
    excerpt = models.CharField(max_length=300, blank=True)
    thumbnail = models.ImageField(upload_to='history_thumbnails/', blank=True, null=True)
    content_english = RichTextField(blank=True)
    content_igala = RichTextField(blank=True)
    audio_english = models.FileField(upload_to='history_audio/', blank=True, null=True)
    audio_igala = models.FileField(upload_to='history_audio/', blank=True, null=True)

    contributor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contributed_histories'
    )
    published_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'History Article'
        verbose_name_plural = 'History Articles'
        ordering = ['-published_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            i = 1
            while HistoryArticle.objects.filter(slug=slug).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ArticleView(models.Model):
    """Unique view per IP per day (one count per visitor per day)."""
    article = models.ForeignKey(
        HistoryArticle,
        on_delete=models.CASCADE,
        related_name='view_records'
    )
    ip_hash = models.CharField(max_length=64)
    viewed_date = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['article', 'ip_hash', 'viewed_date'],
                name='unique_article_view_per_day'
            )
        ]

    def __str__(self):
        return f"View on {self.article.title}"
