from django.contrib import admin
from .models import PartOfSpeech, Example, Meaning, Words

# Register your models here.
admin.site.register( PartOfSpeech)
admin.site.register(Example)
admin.site.register(Meaning)
admin.site.register(Words)
