from django.db import models
from django.utils.text import slugify
from django.db import models

class PartOfSpeech(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Example(models.Model):
    igala_example = models.CharField(max_length=200)
    english_meaning = models.CharField(max_length=200)

    def __str__(self):
        return self.igala_example
    
class Words(models.Model):
    word = models.CharField(max_length=100)
    pronunciation = models.FileField(upload_to='word_sounds/', blank=True, null=True)
    dialects = models.CharField(max_length=200, blank=True, null=True)
    related_terms = models.CharField(max_length=200, null=True, blank=True)
    slug = models.SlugField(unique=True, max_length=100, blank=True)

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

