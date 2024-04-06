from django.contrib import admin
from .models import Words, Dialect, PartOfSpeech

# Register your models here.
admin.site.register(Words)
admin.site.register(Dialect)
admin.site.register(PartOfSpeech)

