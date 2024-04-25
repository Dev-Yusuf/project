from django.db import models
from django.utils.text import slugify
 
class Words(models.Model):
    word = models.CharField(max_length=100)
    meaning = models.CharField(max_length=200, blank=True, null=True)
    igala_meaning = models.CharField(max_length=200, blank=True, null=True)
    part_of_speech = models.CharField(max_length=200, blank=True, null=True)
    pronunciation = models.FileField(upload_to='word_sounds/', blank=True, null=True)
    dialects = models.CharField(max_length=200, blank=True, null=True)
    related_terms = models.CharField(max_length=200, null=True, default=None)
    slug = models.SlugField(unique=True, max_length=100, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.word)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.word

    class Meta:
        verbose_name = "Word"
