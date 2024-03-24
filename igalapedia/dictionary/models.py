from django.db import models

class Dialect(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name

class Words(models.Model):
    word = models.CharField(max_length=100)
    meaning = models.CharField(max_length=200, blank=True, null=True)
    example = models.CharField(max_length=200, null=True, default=None)
    pronunciation = models.FileField(upload_to='word_sounds/', blank=True, null=True)
    dialects = models.ManyToManyField(Dialect, related_name='words', default="none")

    class Meta:
        verbose_name = "Word"

    def __str__(self):
        return self.word
