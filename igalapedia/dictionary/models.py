from core.validators import validate_audio_upload
from django.db import models, transaction, IntegrityError, router
from django.utils.text import slugify
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q, Min, Max

class PartOfSpeech(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Example(models.Model):
    igala_example = models.CharField(max_length=200)
    english_meaning = models.CharField(max_length=200)
    audio = models.FileField(validators=[validate_audio_upload], upload_to='example_sounds/', blank=True, null=True)

    def __str__(self):
        return self.igala_example
    
class Words(models.Model):
    word = models.CharField(max_length=100, unique=True)
    pronunciation = models.FileField(validators=[validate_audio_upload], upload_to='word_sounds/', blank=True, null=True)
    dialects = models.CharField(max_length=200, blank=True, null=True)
    related_terms = models.CharField(max_length=200, null=True, blank=True)
    slug = models.SlugField(unique=True, max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    contributor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contributed_words'
    )

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if self.slug or (update_fields is not None and not update_fields):
            return super().save(*args, **kwargs)

        using = kwargs.get('using') or router.db_for_write(type(self), instance=self)
        words = type(self).objects.using(using).exclude(pk=self.pk)
        max_length = self._meta.get_field('slug').max_length
        base = slugify(self.word) or 'word'
        suffix_number = 1
        if kwargs.get('update_fields') is not None:
            kwargs['update_fields'] = set(kwargs['update_fields']) | {'slug'}

        # The database remains the authority if another writer takes a candidate
        # between the availability check and INSERT. Retry only slug conflicts.
        for attempt in range(5):
            while True:
                suffix = '' if suffix_number == 1 else f'-{suffix_number}'
                self.slug = base[:max_length - len(suffix)] + suffix
                if not words.filter(slug=self.slug).exists():
                    break
                suffix_number += 1
            try:
                with transaction.atomic(using=using):
                    return super().save(*args, **kwargs)
            except IntegrityError:
                if (attempt == 4 or words.filter(word=self.word).exists()
                        or not words.filter(slug=self.slug).exists()):
                    raise
                suffix_number += 1

    def __str__(self):
        return self.word

    class Meta:
        verbose_name = "Word"


class Meaning(models.Model):
    word = models.ForeignKey(Words, related_name='meanings', on_delete=models.CASCADE)
    meaning = models.CharField(max_length=200)
    part_of_speech = models.ForeignKey(PartOfSpeech, on_delete=models.CASCADE)
    examples = models.ManyToManyField(Example)

    def __str__(self):
        return self.meaning



# CONTRIBUTION/SUBMISSION MODELS

class PendingWord(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    # Word Information
    word = models.CharField(max_length=100)
    pronunciation_file = models.FileField(validators=[validate_audio_upload], upload_to='pending_sounds/', blank=True, null=True)
    dialects = models.CharField(max_length=200, blank=True, null=True)
    related_terms = models.CharField(max_length=200, blank=True, null=True)
    
    # Submission Metadata
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pending_word_submissions'
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    # Review Metadata
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_words'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, null=True, help_text="Admin notes about the review")
    
    # Link to approved word (if approved)
    approved_word = models.OneToOneField(
        Words,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_submission'
    )
    
    class Meta:
        verbose_name = "Pending Word Submission"
        verbose_name_plural = "Pending Word Submissions"
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.word} - {self.get_status_display()}"
    
    def approve(self, reviewer):
        """Publish the complete submission and its statistics atomically."""
        with transaction.atomic():
            # Serialize reviewers of the same submission, then reload its state.
            type(self).objects.select_for_update().get(pk=self.pk)
            self.refresh_from_db()
            if self.status != 'PENDING':
                return None

            try:
                # A savepoint lets us inspect duplicates after a uniqueness error.
                with transaction.atomic():
                    word = Words.objects.create(
                        word=self.word,
                        pronunciation=self.pronunciation_file,
                        dialects=self.dialects,
                        related_terms=self.related_terms,
                        contributor=self.submitted_by,
                    )
            except IntegrityError:
                existing = Words.objects.filter(word__iexact=self.word).first()
                if existing is None:
                    # Slug collisions and other integrity failures are not duplicates.
                    raise
                self.reject(
                    reviewer,
                    f'Duplicate: The word "{self.word}" already exists in the dictionary. '
                    f'See: /dictionary/single-word/{existing.slug}/',
                )
                stats, _ = ContributionStats.objects.get_or_create(user=self.submitted_by)
                stats.update_stats()
                return None

            for pending_meaning in self.pending_meanings.prefetch_related('pending_examples'):
                meaning = Meaning.objects.create(
                    word=word,
                    meaning=pending_meaning.meaning,
                    part_of_speech=pending_meaning.part_of_speech,
                )
                for pending_example in pending_meaning.pending_examples.all():
                    example = Example.objects.create(
                        igala_example=pending_example.igala_example,
                        english_meaning=pending_example.english_meaning,
                    )
                    meaning.examples.add(example)

            self.status = 'APPROVED'
            self.reviewed_by = reviewer
            self.reviewed_at = timezone.now()
            self.approved_word = word
            self.save()
            stats, _ = ContributionStats.objects.get_or_create(user=self.submitted_by)
            stats.update_stats()
            return word

    def reject(self, reviewer, notes=""):
        """
        Reject this submission
        """
        self.status = 'REJECTED'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()


class PendingMeaning(models.Model):
    """
    Model for meanings submitted with pending words
    """
    pending_word = models.ForeignKey(
        PendingWord,
        on_delete=models.CASCADE,
        related_name='pending_meanings'
    )
    meaning = models.CharField(max_length=200)
    part_of_speech = models.ForeignKey(PartOfSpeech, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = "Pending Meaning"
        verbose_name_plural = "Pending Meanings"
    
    def __str__(self):
        return f"{self.meaning} ({self.pending_word.word})"


class PendingExample(models.Model):
    """
    Model for examples submitted with pending meanings
    """
    pending_meaning = models.ForeignKey(
        PendingMeaning,
        on_delete=models.CASCADE,
        related_name='pending_examples'
    )
    igala_example = models.CharField(max_length=200)
    english_meaning = models.CharField(max_length=200)
    
    class Meta:
        verbose_name = "Pending Example"
        verbose_name_plural = "Pending Examples"
    
    def __str__(self):
        return self.igala_example


class ContributionStats(models.Model):
    """
    Track user contribution statistics for leaderboard
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='contribution_stats'
    )
    approved_words_count = models.IntegerField(default=0)
    pending_words_count = models.IntegerField(default=0)
    rejected_words_count = models.IntegerField(default=0)
    total_submissions = models.IntegerField(default=0)
    approved_histories_count = models.IntegerField(default=0)
    
    # Timestamps
    first_contribution = models.DateTimeField(null=True, blank=True)
    last_contribution = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Contribution Statistics"
        verbose_name_plural = "Contribution Statistics"
    
    def __str__(self):
        return f"{self.user.username} - {self.approved_words_count} approved"
    
    @transaction.atomic
    def update_stats(self):
        """Rebuild counters from authoritative submissions under a row lock."""
        from history.models import PendingHistory
        type(self).objects.select_for_update().get(pk=self.pk)
        counts = PendingWord.objects.filter(submitted_by=self.user).aggregate(
            approved=Count('pk', filter=Q(status='APPROVED')),
            pending=Count('pk', filter=Q(status='PENDING')),
            rejected=Count('pk', filter=Q(status='REJECTED')),
            total=Count('pk'), first=Min('submitted_at'), last=Max('submitted_at'),
        )
        self.approved_words_count = counts['approved']
        self.pending_words_count = counts['pending']
        self.rejected_words_count = counts['rejected']
        self.total_submissions = counts['total']
        self.first_contribution = counts['first']
        self.last_contribution = counts['last']
        self.approved_histories_count = PendingHistory.objects.filter(
            submitted_by=self.user, status='APPROVED',
        ).count()
        self.save()


class PendingExampleContribution(models.Model):
    """
    Model for usage examples submitted by users for already-approved words.
    This is separate from PendingExample which is tied to new pending word submissions.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    # Target meaning (the approved meaning this example is for)
    meaning = models.ForeignKey(
        Meaning,
        on_delete=models.CASCADE,
        related_name='pending_example_contributions'
    )
    
    # Example content
    igala_example = models.CharField(max_length=200)
    english_meaning = models.CharField(max_length=200)
    
    # Submission Metadata
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pending_example_contributions'
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    # Review Metadata
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_example_contributions'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, null=True, help_text="Admin notes about the review")
    
    # Link to approved example (if approved)
    approved_example = models.OneToOneField(
        Example,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_contribution'
    )
    
    class Meta:
        verbose_name = "Pending Example Contribution"
        verbose_name_plural = "Pending Example Contributions"
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f'"{self.igala_example}" for {self.meaning.word.word} - {self.get_status_display()}'
    
    @transaction.atomic
    def approve(self, reviewer):
        """Approve an example without publishing a partial contribution."""
        type(self).objects.select_for_update().get(pk=self.pk)
        self.refresh_from_db()
        if self.status != 'PENDING':
            return None
        
        # Create official example
        example = Example.objects.create(
            igala_example=self.igala_example,
            english_meaning=self.english_meaning
        )
        
        # Attach to meaning
        self.meaning.examples.add(example)
        
        # Update submission status
        self.status = 'APPROVED'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.approved_example = example
        self.save()
        
        return example
    
    def reject(self, reviewer, notes=""):
        """
        Reject this example submission.
        """
        self.status = 'REJECTED'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()

