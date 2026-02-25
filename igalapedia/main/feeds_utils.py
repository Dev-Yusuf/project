"""
Feed aggregation: unified items from Words, HistoryArticle, and BlogPost for the discovery feed.
"""
import re
from django.utils import timezone
from django.urls import reverse


def get_feed_items(offset=0, limit=12):
    """
    Return a list of feed items (dicts) from Words, HistoryArticle, and BlogPost,
    merged and sorted by date descending, then sliced by offset/limit.
    Each item: title, excerpt, thumbnail_url, url, type, date (for sorting).
    """
    from dictionary.models import Words
    from history.models import HistoryArticle
    from blog.models import BlogPost

    items = []

    # Blog posts (published only)
    for post in BlogPost.objects.filter(status='published', is_hidden=False).select_related('author').order_by('-published_at', '-created_at'):
        date_val = post.published_at or post.created_at
        excerpt = (post.body[:300] if post.body else '') or 'Read more...'
        excerpt = re.sub(r'<[^>]+>', '', excerpt)[:300]
        items.append({
            'title': post.title,
            'excerpt': excerpt or 'Read more...',
            'thumbnail_url': post.cover_image.url if post.cover_image else None,
            'url': reverse('blog:blog_detail', kwargs={'slug': post.slug}),
            'type': 'blog',
            'date': date_val,
        })

    # History articles
    for art in HistoryArticle.objects.all().order_by('-published_at').select_related('contributor'):
        items.append({
            'title': art.title,
            'excerpt': (art.excerpt or '').strip() or 'Read more...',
            'thumbnail_url': art.thumbnail.url if art.thumbnail else None,
            'url': reverse('history_detail', kwargs={'slug': art.slug}),
            'type': 'history',
            'date': art.published_at,
        })

    # Dictionary words (use created_at if set, else id as proxy)
    words_qs = Words.objects.prefetch_related('meanings').order_by('-created_at', '-id')
    for w in words_qs:
        first_meaning = w.meanings.first()
        excerpt = (first_meaning.meaning if first_meaning else None) or f'Igala word: {w.word}'
        # Use created_at for sorting; if null, use a date far in past so they sort after dated items
        sort_date = w.created_at if w.created_at else timezone.datetime(2000, 1, 1, tzinfo=timezone.get_current_timezone())
        items.append({
            'title': w.word,
            'excerpt': excerpt[:300] if excerpt else 'Igala word',
            'thumbnail_url': None,
            'url': reverse('single-word', kwargs={'slug': w.slug}),
            'type': 'word',
            'date': sort_date,
        })

    # Sort by date descending
    items.sort(key=lambda x: x['date'], reverse=True)

    # Apply offset and limit
    total = len(items)
    page = items[offset:offset + limit]
    has_more = (offset + limit) < total

    return page, has_more, total
