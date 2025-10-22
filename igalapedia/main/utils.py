from django.db.models import Count, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import get_object_or_404

def get_aggregated_counts(model, fields):
    """
    Get aggregated counts for specified fields in a model.
    
    Args:
        model: Django model class
        fields: List of tuples containing (field_name, filter_value)
        
    Returns:
        Dictionary of aggregated counts
    """
    counts = {}
    try:
        for field, value in fields:
            count_key = f"{field}_count"
            counts[count_key] = model.objects.aggregate(
                count=Count(field, filter=~Q(**{field: value}))
            )['count']
    except Exception:
        for field, _ in fields:
            count_key = f"{field}_count"
            counts[count_key] = None
    return counts

def get_first_instance(model):
    """
    Safely get the first instance of a model.
    
    Args:
        model: Django model class
        
    Returns:
        First instance of the model or None if not found
    """
    try:
        return model.objects.first()
    except Exception:
        return None

def paginate_queryset(queryset, results_per_page, page_number):
    """
    Paginate a queryset.
    
    Args:
        queryset: QuerySet to paginate
        results_per_page: Number of results per page
        page_number: Current page number
        
    Returns:
        Page object with paginated results
    """
    paginator = Paginator(queryset, results_per_page)
    try:
        return paginator.get_page(page_number)
    except PageNotAnInteger:
        return paginator.page(1)
    except EmptyPage:
        return paginator.page(paginator.num_pages)

def get_filtered_queryset(queryset, filter_class, request):
    """
    Apply filters to a queryset using a filter class.
    
    Args:
        queryset: QuerySet to filter
        filter_class: Filter class to use
        request: Django request object
        
    Returns:
        Tuple of (filtered_queryset, filter_instance)
    """
    filter_instance = filter_class(request.GET, queryset=queryset)
    return filter_instance.qs, filter_instance
