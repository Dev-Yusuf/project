from django.shortcuts import render
from django.shortcuts import render, get_object_or_404
from .models import Words
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.text import slugify
from .filters import WordsFilters
# Create your views here.

def all_words(request):
    words = Words.objects.all().order_by('word')
    word_filter = WordsFilters(request.GET, queryset=words)
    filtered_words = word_filter.qs
    results = 50
    word_paginator = Paginator(filtered_words, results)
    page_number = request.GET.get('page')
    try:
        current_page_holder = word_paginator.get_page(page_number)
    except PageNotAnInteger:
        current_page_holder = word_paginator.page(1) 
    except EmptyPage:
        current_page_holder = word_paginator.page(word_paginator.num_pages)
    context = {"words": current_page_holder, "word_filter": word_filter, "current_page_holder": current_page_holder}
    return render(request, "dictionary/dictionary.html", context)

def singleword(request, slug):
    single_words = get_object_or_404(Words, slug=slug)
    context = {"single_words":single_words}
    return render(request, "dictionary/single_word.html", context)
    
