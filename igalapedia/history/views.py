from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.utils import timezone

from main.utils import get_client_ip_hash
from .models import HistoryArticle, PendingHistory, ArticleView
from .forms import HistorySubmissionForm


def history_list(request):
    """List all published history articles in a clean card grid."""
    articles = HistoryArticle.objects.all().order_by('-published_at').annotate(view_count=Count('view_records'))
    paginator = Paginator(articles, 12)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)

    context = {
        'articles': page_obj,
        'page_obj': page_obj,
        'page_title': 'Igala History - IgalaHeritage',
    }
    return render(request, 'history/history_list.html', context)


def history_detail(request, slug):
    """Detail page with English/Igala toggle and audio per version."""
    article = get_object_or_404(HistoryArticle.objects.annotate(view_count=Count('view_records')), slug=slug)
    ip_hash = get_client_ip_hash(request)
    if ip_hash:
        today = timezone.localdate()
        ArticleView.objects.get_or_create(article=article, ip_hash=ip_hash, viewed_date=today)

    context = {
        'article': article,
        'page_title': f'{article.title} - IgalaHeritage',
    }
    return render(request, 'history/history_detail.html', context)


@login_required
def submit_history(request):
    """User submission form for history articles."""
    if request.method == 'POST':
        form = HistorySubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.submitted_by = request.user
            submission.save()
            messages.success(
                request,
                'Your history submission has been received. It will be reviewed by our team.'
            )
            return redirect('history_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = HistorySubmissionForm()

    context = {
        'form': form,
        'page_title': 'Submit History - IgalaHeritage',
    }
    return render(request, 'history/submit_history.html', context)
