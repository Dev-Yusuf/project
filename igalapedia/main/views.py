from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Community, Pioneer
from dictionary.models import Words, Example, ContributionStats
from .utils import get_aggregated_counts, get_first_instance
from .forms import CustomUserRegistrationForm, CustomLoginForm


def mainpage(request):
    """
    Main page view that displays statistics and community information.
    
    Returns:
        Rendered template with statistics context
    """
    # Get aggregated counts for various fields
    fields_to_count = [
        ('word', ''),
        ('pronunciation', ''),
        ('igala_example', '')
    ]
    
    # Get pioneers from database (limit to 3 for homepage)
    pioneers = Pioneer.objects.all()[:3]
    
    # Get recent contributions (last 3 words added)
    recent_words = Words.objects.select_related('contributor').order_by('-id')[:3]
    
    # Get recent examples added
    recent_examples = Example.objects.order_by('-id')[:2]
    
    context = {
        **get_aggregated_counts(Words, fields_to_count[:2]),  # Get word and pronunciation counts
        **get_aggregated_counts(Example, fields_to_count[2:]),  # Get example counts
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
            user = form.save()
            # Create contribution stats for new user
            ContributionStats.objects.create(user=user)
            # Log the user in
            login(request, user)
            messages.success(request, f'Welcome to Igalapedia, {user.username}! Your account has been created successfully.')
            return redirect('index')
        else:
            messages.error(request, 'Please correct the errors below.')
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
    # Get or create user stats
    stats, created = ContributionStats.objects.get_or_create(user=request.user)
    if created or stats.total_submissions == 0:
        stats.update_stats()
    
    context = {
        'stats': stats,
        'page_title': 'My Dashboard - Igalapedia'
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