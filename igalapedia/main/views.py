import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from django.http import JsonResponse
from .models import Community, Pioneer
from dictionary.models import Words, Example, ContributionStats
from .utils import get_aggregated_counts, get_first_instance
from .forms import CustomUserRegistrationForm, CustomLoginForm
from .feeds_utils import get_feed_items
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


def mainpage(request):
    fields_to_count = [
        ('word', ''),
        ('pronunciation', ''),
        ('igala_example', '')
    ]
    
    pioneers = Pioneer.objects.all()[:3]
    recent_words = Words.objects.select_related('contributor').order_by('-id')[:3]
    recent_examples = Example.objects.order_by('-id')[:2]
    word_count = Words.objects.count()
    audio_count = Words.objects.exclude(pronunciation__isnull=True).exclude(pronunciation='').count()
    contributor_count = ContributionStats.objects.filter(approved_words_count__gt=0).count()
    history_count = 0
    try:
        from history.models import HistoryArticle
        history_count = HistoryArticle.objects.count()
    except Exception:
        pass
    if contributor_count == 0:
        User = get_user_model()
        contributor_count = User.objects.count()

    context = {
        'word_count': word_count,
        'audio_count': audio_count,
        'contributor_count': contributor_count,
        'history_count': history_count,
        'community_stats': get_first_instance(Community),
        'pioneers': pioneers,
        'recent_words': recent_words,
        'recent_examples': recent_examples
    }
    
    return render(request, 'main/index.html', context)


def about(request):
    """About page view"""
    context = {
        'page_title': 'About Igalapedia'
    }
    return render(request, 'main/about.html', context)


def translator(request):
    """Translator page view (placeholder for future implementation)"""
    context = {
        'page_title': 'English - Igala Translator'
    }
    return render(request, 'main/translator.html', context)


def api_docs(request):
    """API documentation page view (placeholder for future implementation)"""
    context = {
        'page_title': 'API Documentation'
    }
    return render(request, 'main/api.html', context)


def register(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                ContributionStats.objects.create(user=user)
            except IntegrityError:
                messages.error(
                    request,
                    'An account with this username or email already exists.'
                )
                context = {'form': form, 'page_title': 'Register - Igalapedia'}
                return render(request, 'main/register.html', context)
            except Exception:
                logger.exception(
                    "Registration: failed after user save (e.g. ContributionStats or DB)",
                )
                messages.info(
                    request,
                    'Something went wrong during registration. If you already have an account, try signing in.',
                )
                return redirect('login')
            try:
                login(request, user)
                # Welcome email disabled; will use another email platform later.
                # try:
                #     from main.emails import send_welcome_email
                #     send_welcome_email(user, request)
                # except BaseException:
                #     pass
                messages.success(request, f'Welcome to Igalapedia, {user.username}! Your account has been created successfully.')
                return redirect('index')
            except Exception:
                logger.exception(
                    "Registration: failed during login/session/messages/redirect",
                )
                messages.success(
                    request,
                    'Your account was created successfully. Please sign in.',
                )
                return redirect('login')
        else:
            messages.error(request, 'Please check your credentials.')
    else:
        form = CustomUserRegistrationForm()
    
    context = {
        'form': form,
        'page_title': 'Register - Igalapedia'
    }
    return render(request, 'main/register.html', context)


def user_login(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                # Redirect to next page or index
                next_page = request.GET.get('next', 'index')
                return redirect(next_page)
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = CustomLoginForm()
    
    # Get dynamic statistics for the login page
    total_words = Words.objects.count()
    total_examples = Example.objects.count()
    # Count contributors with at least one approved word
    total_contributors = ContributionStats.objects.filter(approved_words_count__gt=0).count()
    
    context = {
        'form': form,
        'page_title': 'Login - Igalapedia',
        'total_words': total_words,
        'total_examples': total_examples,
        'total_contributors': total_contributors,
    }
    return render(request, 'main/login.html', context)


@login_required
def user_logout(request):
    """User logout view"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('index')


@login_required
def user_dashboard(request):
    """User dashboard showing contribution statistics"""
    from dictionary.models import PendingWord
    from history.models import PendingHistory
    
    # Get or create user stats
    stats, created = ContributionStats.objects.get_or_create(user=request.user)
    if created or stats.total_submissions == 0:
        stats.update_stats()
    
    # Fetch recent 4 approved and rejected words
    recent_approved = PendingWord.objects.filter(
        submitted_by=request.user,
        status='APPROVED'
    ).select_related('approved_word').order_by('-reviewed_at')[:4]
    
    recent_rejected = PendingWord.objects.filter(
        submitted_by=request.user,
        status='REJECTED'
    ).order_by('-reviewed_at')[:4]
    
    # Fetch recent approved and rejected histories
    recent_approved_histories = PendingHistory.objects.filter(
        submitted_by=request.user,
        status='APPROVED'
    ).select_related('approved_article').order_by('-reviewed_at')[:4]
    
    recent_rejected_histories = PendingHistory.objects.filter(
        submitted_by=request.user,
        status='REJECTED'
    ).order_by('-reviewed_at')[:4]
    
    context = {
        'stats': stats,
        'recent_approved': recent_approved,
        'recent_rejected': recent_rejected,
        'recent_approved_histories': recent_approved_histories,
        'recent_rejected_histories': recent_rejected_histories,
        'page_title': 'My Dashboard - IgalaHeritage'
    }
    return render(request, 'main/dashboard.html', context)


def pioneers_page(request):
    """Display all pioneers"""
    pioneers = Pioneer.objects.all()
    
    context = {
        'pioneers': pioneers,
        'page_title': 'Pioneers - Igalapedia'
    }
    return render(request, 'main/pioneers.html', context)


def feed_page(request):
    """Discovery feed: mixed content from dictionary and history."""
    page_size = 12
    items, has_more, total = get_feed_items(offset=0, limit=page_size)
    context = {
        'feed_items': items,
        'has_more': has_more,
        'total': total,
        'page_size': page_size,
        'page_title': 'Discover - IgalaHeritage',
    }
    return render(request, 'main/feed.html', context)


def feed_api(request):
    """JSON API for feed pagination (infinite scroll)."""
    try:
        offset = max(0, int(request.GET.get('offset', 0)))
        limit = min(24, max(1, int(request.GET.get('limit', 12))))
    except (TypeError, ValueError):
        offset, limit = 0, 12
    items, has_more, total = get_feed_items(offset=offset, limit=limit)
    # Serialize for JSON (date to ISO string)
    out = []
    for it in items:
        out.append({
            'title': it['title'],
            'excerpt': it['excerpt'],
            'thumbnail_url': it['thumbnail_url'],
            'url': it['url'],
            'type': it['type'],
            'date': it['date'].isoformat() if it.get('date') else None,
        })
    return JsonResponse({'items': out, 'has_more': has_more, 'total': total})