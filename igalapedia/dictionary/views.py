from django.shortcuts import render
from django.http import HttpResponse
from .models import Words
# Create your views here.

def all_words(request):
    words = Words.objects.all()
    context = {"words":"words"}
    return render(request, "dictionary/dictionary.html", context)

    
