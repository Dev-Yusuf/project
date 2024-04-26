from django.shortcuts import render
from django.shortcuts import render, get_object_or_404
from .models import Words
from django.utils.text import slugify
from .filters import WordsFilters
# Create your views here.

def all_words(request):
    words = Words.objects.all().order_by('word')[0:50]
    word_filter = WordsFilters(request.GET, queryset=words)
    words = word_filter.qs
    context = {"words":words, "word_filter":word_filter}
    return render(request, "dictionary/dictionary.html", context)

def singleword(request, slug):
    single_words = get_object_or_404(Words, slug=slug)
    context = {"single_words":single_words}
    return render(request, "dictionary/single_word.html", context)
    
