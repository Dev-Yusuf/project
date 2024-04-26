import django_filters
from .models import Words

class WordsFilters(django_filters.FilterSet):
    word = django_filters.CharFilter(field_name='word', lookup_expr='icontains')



    class Meta:
        model = Words
        fields = ['word']