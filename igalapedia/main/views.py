from django.shortcuts import render
from django.db.models import Count
from .models import Community, Pioneer
from dictionary.models import Words, Example
from django.db.models import Q


# here make a content 
# Create your views here. 
# def mainpage(request):
#     word_count = Words.objects.aaggregate(word_count=Count('word', filter=~Q(word="")))['word_count']
#     context = {"word_count":word_count}
#     return render(request, 'main/index.html', context)

def mainpage(request):
    try:
        word_count = Words.objects.aggregate(count=Count('word', filter=~Q(word="")))['count']
        pronunciation_count = Words.objects.aggregate(count=Count('pronunciation', filter=~Q(pronunciation="")))['count']
        igala_example_count = Example.objects.aggregate(count=Count('igala_example', filter=~Q(igala_example="")))['count']
        community_stats = Community.objects.first()
    except Exception as e:
        word_count = None
        pronunciation_count = None
        igala_example_count = None
        community_stats
    context = {"word_count": word_count, "pronunciation_count": pronunciation_count, "igala_example_count": igala_example_count, "community_stats":community_stats}
    return render(request, 'main/index.html', context)