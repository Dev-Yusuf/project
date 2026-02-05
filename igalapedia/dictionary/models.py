from django.db import models, transaction, IntegrityError
from django.utils.text import slugify
from django.conf import settings
from django.utils import timezone

class PartOfSpeech(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Example(models.Model):
    igala_example = models.CharField(max_length=200)
    english_meaning = models.CharField(max_length=200)
    audio = models.FileField(upload_to='example_sounds/', blank=True, null=True)

    def __str__(self):
        return self.igala_example
    
class Words(models.Model):
    word = models.CharField(max_length=100, unique=True)
    pronunciation = models.FileField(upload_to='word_sounds/', blank=True, null=True)
    dialects = models.CharField(max_length=200, blank=True, null=True)
    related_terms = models.CharField(max_length=200, null=True, blank=True)
    slug = models.SlugField(unique=True, max_length=100, blank=True)
    contributor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contributed_words'
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.word)
        super().save(*args, **kwargs)

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
    pronunciation_file = models.FileField(upload_to='pending_sounds/', blank=True, null=True)
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
        """
        Approve this submission and create official Word entry.
        Returns the created Words instance on success, or None if:
        - Already processed (not PENDING)
        - Duplicate word exists (race condition or concurrent approval)
        
        If duplicate detected, auto-rejects with appropriate notes.
        """
        if self.status != 'PENDING':
            return None
        
        try:
            with transaction.atomic():
                # Create official word (unique constraint will raise IntegrityError if duplicate)
                word = Words.objects.create(
                    word=self.word,
                    pronunciation=self.pronunciation_file,
                    dialects=self.dialects,
                    related_terms=self.related_terms,
                    contributor=self.submitted_by
                )
                
                # Update submission status
                self.status = 'APPROVED'
                self.reviewed_by = reviewer
                self.reviewed_at = timezone.now()
                self.approved_word = word
                self.save()
                
                return word
        except IntegrityError:
            # Duplicate word already exists - auto-reject this submission
            existing = Words.objects.filter(word__iexact=self.word).first()
            self.status = 'REJECTED'
            self.reviewed_by = reviewer
            self.reviewed_at = timezone.now()
            self.review_notes = f'Duplicate: The word "{self.word}" already exists in the dictionary.'
            if existing:
                self.review_notes += f' See: /dictionary/single-word/{existing.slug}/'
            self.save()
            return None
    
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
    
    # Timestamps
    first_contribution = models.DateTimeField(null=True, blank=True)
    last_contribution = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Contribution Statistics"
        verbose_name_plural = "Contribution Statistics"
    
    def __str__(self):
        return f"{self.user.username} - {self.approved_words_count} approved"
    
    def update_stats(self):
        """
        Recalculate contribution statistics
        """
        user_submissions = PendingWord.objects.filter(submitted_by=self.user)
        
        self.approved_words_count = user_submissions.filter(status='APPROVED').count()
        self.pending_words_count = user_submissions.filter(status='PENDING').count()
        self.rejected_words_count = user_submissions.filter(status='REJECTED').count()
        self.total_submissions = user_submissions.count()
        
        first_submission = user_submissions.order_by('submitted_at').first()
        last_submission = user_submissions.order_by('-submitted_at').first()
        
        if first_submission:
            self.first_contribution = first_submission.submitted_at
        if last_submission:
            self.last_contribution = last_submission.submitted_at
        
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
    
    def approve(self, reviewer):
        """
        Approve this example and add it to the meaning.
        """
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

