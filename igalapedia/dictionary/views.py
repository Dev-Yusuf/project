from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import Words, PendingWord, PendingMeaning, PendingExample, ContributionStats
from .filters import WordsFilters
from .forms import WordSubmissionForm, MeaningFormSet, ExampleFormSet
from main.utils import paginate_queryset, get_filtered_queryset, get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Count


def all_words(request):
    """
    View for displaying all words with pagination and filtering.
    
    Args:
        request: Django request object
        
    Returns:
        Rendered template with paginated and filtered words
    """
    # Get all words ordered by word
    words = Words.objects.all().order_by('word')
    
    # Apply filters
    filtered_words, word_filter = get_filtered_queryset(words, WordsFilters, request)
    
    # Paginate results
    page_number = request.GET.get('page')
    current_page_holder = paginate_queryset(filtered_words, 50, page_number)
    
    context = {
        'words': current_page_holder,
        'word_filter': word_filter,
        'current_page_holder': current_page_holder
    }
    
    return render(request, "dictionary/dictionary.html", context)


def singleword(request, slug):
    """
    View for displaying a single word's details.
    
    Args:
        request: Django request object
        slug: Slug of the word to display
        
    Returns:
        Rendered template with single word details
    """
    word = get_object_or_404(Words, slug=slug)
    context = {'single_words': word}
    return render(request, "dictionary/single_word.html", context)


def leaderboard(request):
    """
    Display leaderboard based on approved contributions
    """
    # Get or create contribution stats for all users with contributions
    User = get_user_model()
    
    # Get all users who have made contributions
    contributors_data = []
    pending_words = PendingWord.objects.select_related('submitted_by').all()
    
    user_ids = set(pending_words.values_list('submitted_by_id', flat=True))
    
    for user_id in user_ids:
        user = User.objects.get(id=user_id)
        stats, created = ContributionStats.objects.get_or_create(user=user)
        if created or stats.total_submissions == 0:
            stats.update_stats()
        
        if stats.approved_words_count > 0:  # Only show users with approved contributions
            contributors_data.append({
                'user': user,
                'word_count': stats.approved_words_count,
                'pending_count': stats.pending_words_count,
                'total_submissions': stats.total_submissions
            })
    
    # Sort by approved word count
    contributors_data.sort(key=lambda x: x['word_count'], reverse=True)
    
    context = {'contributors': contributors_data}
    return render(request, 'dictionary/leaderboard.html', context)


@login_required
def submit_word(request):
    """
    View for users to submit new words
    """
    if request.method == 'POST':
        word_form = WordSubmissionForm(request.POST, request.FILES)
        meaning_formset = MeaningFormSet(request.POST, prefix='meanings')
        
        if word_form.is_valid() and meaning_formset.is_valid():
            try:
                with transaction.atomic():
                    # Create pending word
                    pending_word = word_form.save(commit=False)
                    pending_word.submitted_by = request.user
                    pending_word.save()
                    
                    # Create pending meanings
                    for meaning_form in meaning_formset:
                        if meaning_form.cleaned_data and not meaning_form.cleaned_data.get('DELETE', False):
                            meaning_data = meaning_form.cleaned_data
                            PendingMeaning.objects.create(
                                pending_word=pending_word,
                                meaning=meaning_data['meaning'],
                                part_of_speech=meaning_data['part_of_speech']
                            )
                    
                    # Update user stats
                    stats, created = ContributionStats.objects.get_or_create(user=request.user)
                    stats.update_stats()
                    
                    messages.success(
                        request,
                        f'Thank you! Your submission "{pending_word.word}" has been sent for review. '
                        f'You will be notified once it\'s approved.'
                    )
                    return redirect('submit_word')
                    
            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        word_form = WordSubmissionForm()
        meaning_formset = MeaningFormSet(prefix='meanings')
    
    context = {
        'word_form': word_form,
        'meaning_formset': meaning_formset,
    }
    return render(request, 'dictionary/submit_word.html', context)


@login_required
def my_contributions(request):
    """
    View for users to see their own contributions
    """
    pending_words = PendingWord.objects.filter(
        submitted_by=request.user
    ).prefetch_related('pending_meanings').order_by('-submitted_at')
    
    # Get stats
    stats, created = ContributionStats.objects.get_or_create(user=request.user)
    if created:
        stats.update_stats()
    
    context = {
        'pending_words': pending_words,
        'stats': stats,
    }
    return render(request, 'dictionary/my_contributions.html', context)
    
