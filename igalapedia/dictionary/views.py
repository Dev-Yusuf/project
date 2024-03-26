from django.shortcuts import render
from django.http import HttpResponse
from .models import Words
# Create your views here.

def all_words(request):
    words = Words.objects.all().order_by('word')
    context = {"words":words}
    return render(request, "dictionary/dictionary.html", context)

def singleword(request, slug):
    single_words = Words.objects.get(slug=slug)
    context = {"single_words":single_words}
    return render(request, "dictionary/single_word.html", context)


    
