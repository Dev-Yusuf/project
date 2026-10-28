import logging
from urllib.parse import urlencode
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from .models import Words, Meaning, PendingWord, PendingMeaning, PendingExample, PendingExampleContribution, ContributionStats
from .forms import WordSubmissionForm, MeaningFormSet, ExampleInlineFormSet, ExampleContributionForm
from main.utils import paginate_queryset, get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Prefetch
from django.db.models.functions import Lower


logger = logging.getLogger(__name__)


def all_words(request):
    query = (request.GET.get('word') or '').strip()[:100]
    meanings = Prefetch('meanings', queryset=Meaning.objects.select_related('part_of_speech').order_by('pk'))
    archive = Words.objects.all()
    words = archive.order_by(Lower('word'), 'pk').prefetch_related(meanings)
    if query:
        words = words.filter(word__istartswith=query)
    page = paginate_queryset(words, 20, request.GET.get('page'))
    params = {'word': query} if query else {}
    page_link = lambda number: '?' + urlencode({**params, 'page': number})
    context = {
        'words': page, 'current_page_holder': page,
        'query': query,
        'page_links': [{'number': number, 'url': page_link(number) if isinstance(number, int) else ''}
                       for number in page.paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1)],
        'previous_url': page_link(page.previous_page_number()) if page.has_previous() else '',
        'next_url': page_link(page.next_page_number()) if page.has_next() else '',
    }
    if request.GET.get('fragment') == '1':
        return render(request, 'dictionary/_browse_results.html', context)
    context['featured_word'] = archive.prefetch_related(meanings).order_by('-created_at', '-pk').first()
    return render(request, "dictionary/dictionary.html", context)


def dictionary_search_api(request):
    """Prefix search, or an exact lookup with meanings for the homepage word lab."""
    q = (request.GET.get('q') or '').strip()
    if not q or len(q) > Words._meta.get_field('word').max_length:
        return JsonResponse({'words': []})
    if request.GET.get('exact') == '1':
        words = Words.objects.filter(word__iexact=q).order_by('pk').prefetch_related(
            Prefetch('meanings', queryset=Meaning.objects.select_related('part_of_speech').order_by('pk')),
        )[:10]
        return JsonResponse({'words': [
            {'word': word.word, 'slug': word.slug,
             'url': reverse('single-word', kwargs={'slug': word.slug}),
             'meanings': [{'meaning': meaning.meaning, 'part_of_speech': meaning.part_of_speech.name}
                          for meaning in word.meanings.all()]}
            for word in words
        ]})
    words = Words.objects.filter(word__istartswith=q).order_by('word')[:50]
    return JsonResponse({
        'words': [{'word': w.word, 'slug': w.slug} for w in words]
    })


def singleword(request, slug):
    word = get_object_or_404(Words, slug=slug)
    example_form = None
    
    # Only show example contribution form to logged-in users
    if request.user.is_authenticated:
        if request.method == 'POST' and 'submit_example' in request.POST:
            example_form = ExampleContributionForm(request.POST, word=word)
            if example_form.is_valid():
                # Validate that the meaning belongs to this word
                meaning = example_form.cleaned_data['meaning']
                if meaning.word_id != word.id:
                    messages.error(request, 'Invalid meaning selected.')
                else:
                    # Create pending example contribution
                    pending_example = example_form.save(commit=False)
                    pending_example.submitted_by = request.user
                    pending_example.save()
                    messages.success(
                        request,
                        f'Thank you! Your usage example has been submitted for review.'
                    )
                    return redirect('single-word', slug=slug)
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            example_form = ExampleContributionForm(word=word)
    
    context = {
        'single_words': word,
        'example_form': example_form,
    }
    return render(request, "dictionary/single_word.html", context)


def leaderboard(request):
    User = get_user_model()
    contributors = User.objects.annotate(
        approved_count=Count('pending_word_submissions', filter=Q(pending_word_submissions__status='APPROVED')),
        pending_count=Count('pending_word_submissions', filter=Q(pending_word_submissions__status='PENDING')),
        submission_count=Count('pending_word_submissions'),
    ).filter(approved_count__gt=0).order_by('-approved_count', 'username')
    contributors_data = [
        {'user': user, 'word_count': user.approved_count,
         'pending_count': user.pending_count, 'total_submissions': user.submission_count}
        for user in contributors
    ]
    context = {'contributors': contributors_data}
    return render(request, 'dictionary/leaderboard.html', context)


@login_required
def submit_word(request):
    if request.method == 'POST':
        word_form = WordSubmissionForm(request.POST, request.FILES)
        meaning_formset = MeaningFormSet(request.POST, prefix='meanings')
        example_formset = ExampleInlineFormSet(request.POST, prefix='examples')
        
        if word_form.is_valid() and meaning_formset.is_valid() and example_formset.is_valid():
            try:
                with transaction.atomic():
                    # Create pending word
                    pending_word = word_form.save(commit=False)
                    pending_word.submitted_by = request.user
                    pending_word.save()
                    
                    # Create pending meanings (keep order for example indexing)
                    pending_meanings_list = []
                    for meaning_form in meaning_formset:
                        if meaning_form.cleaned_data and not meaning_form.cleaned_data.get('DELETE', False):
                            meaning_data = meaning_form.cleaned_data
                            pm = PendingMeaning.objects.create(
                                pending_word=pending_word,
                                meaning=meaning_data['meaning'],
                                part_of_speech=meaning_data['part_of_speech']
                            )
                            pending_meanings_list.append(pm)
                    
                    # Create pending examples (linked to meaning by index)
                    for ex_form in example_formset:
                        if not ex_form.cleaned_data or ex_form.cleaned_data.get('DELETE'):
                            continue
                        data = ex_form.cleaned_data
                        igala = (data.get('igala_example') or '').strip()
                        english = (data.get('english_meaning') or '').strip()
                        if not igala and not english:
                            continue
                        idx = data.get('meaning_index', 0)
                        if idx < 0 or idx >= len(pending_meanings_list):
                            continue
                        PendingExample.objects.create(
                            pending_meaning=pending_meanings_list[idx],
                            igala_example=igala or '(no Igala)',
                            english_meaning=english or '(no English)',
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
                    
            except Exception:
                logger.exception('Word submission failed for user %s', request.user.pk)
                messages.error(request, 'Your submission could not be saved. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        word_form = WordSubmissionForm()
        meaning_formset = MeaningFormSet(prefix='meanings')
        example_formset = ExampleInlineFormSet(prefix='examples')
    
    context = {
        'word_form': word_form,
        'meaning_formset': meaning_formset,
        'example_formset': example_formset,
    }
    return render(request, 'dictionary/submit_word.html', context)


@login_required
def my_contributions(request):
    # Word submissions split by status
    base_words_qs = PendingWord.objects.filter(
        submitted_by=request.user
    ).prefetch_related('pending_meanings')
    
    pending_words = base_words_qs.filter(status='PENDING').order_by('-submitted_at')
    approved_words = base_words_qs.filter(status='APPROVED').order_by('-reviewed_at', '-submitted_at')
    rejected_words = base_words_qs.filter(status='REJECTED').order_by('-reviewed_at', '-submitted_at')
    
    # Example contributions split by status
    base_examples_qs = PendingExampleContribution.objects.filter(
        submitted_by=request.user
    ).select_related('meaning__word', 'meaning__part_of_speech')
    
    pending_examples = base_examples_qs.filter(status='PENDING').order_by('-submitted_at')
    approved_examples = base_examples_qs.filter(status='APPROVED').order_by('-reviewed_at', '-submitted_at')
    rejected_examples = base_examples_qs.filter(status='REJECTED').order_by('-reviewed_at', '-submitted_at')
    
    # History submissions (from history app)
    pending_histories = []
    approved_histories = []
    rejected_histories = []
    from history.models import PendingHistory
    base_histories_qs = PendingHistory.objects.filter(submitted_by=request.user).select_related('approved_article')
    pending_histories = list(base_histories_qs.filter(status='PENDING').order_by('-submitted_at'))
    approved_histories = list(base_histories_qs.filter(status='APPROVED').order_by('-reviewed_at', '-submitted_at'))
    rejected_histories = list(base_histories_qs.filter(status='REJECTED').order_by('-reviewed_at', '-submitted_at'))

    # Get stats
    stats, created = ContributionStats.objects.get_or_create(user=request.user)
    stats.update_stats()
    
    context = {
        # Word submissions by status
        'pending_words': pending_words,
        'approved_words': approved_words,
        'rejected_words': rejected_words,
        'approved_words_count': approved_words.count(),
        'rejected_words_count': rejected_words.count(),
        
        # Example contributions by status
        'pending_examples': pending_examples,
        'approved_examples': approved_examples,
        'rejected_examples': rejected_examples,
        'approved_examples_count': approved_examples.count(),
        'rejected_examples_count': rejected_examples.count(),
        
        # History submissions by status
        'pending_histories': pending_histories,
        'approved_histories': approved_histories,
        'rejected_histories': rejected_histories,
        'approved_histories_count': len(approved_histories),
        'rejected_histories_count': len(rejected_histories),
        
        # Overall stats
        'stats': stats,
    }
    return render(request, 'dictionary/my_contributions.html', context)


def word_exists(request):
    """
    JSON endpoint to check if a word already exists in the approved dictionary.
    Returns: { "exists": true/false, "word_url": string|null }
    """
    word = request.GET.get('word', '').strip()
    
    if not word:
        return JsonResponse({'exists': False, 'word_url': None})
    
    existing = Words.objects.filter(word__iexact=word).first()
    
    if existing:
        word_url = reverse('single-word', kwargs={'slug': existing.slug})
        return JsonResponse({
            'exists': True,
            'word_url': word_url,
            'word': existing.word,
        })
    
    return JsonResponse({'exists': False, 'word_url': None})
