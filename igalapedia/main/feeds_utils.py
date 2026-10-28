"""Database-paginated discovery feed; hydrate only the requested page."""
from datetime import datetime, timezone

from django.db.models import CharField, DateTimeField, F, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.html import strip_tags


def get_feed_items(offset=0, limit=12):
    from dictionary.models import Meaning, Words
    from history.models import HistoryArticle
    from blog.models import BlogPost

    offset, limit = max(0, offset), min(24, max(1, limit))
    fallback = datetime(2000, 1, 1, tzinfo=timezone.utc)
    blogs = BlogPost.objects.filter(status='published', is_hidden=False)
    sources = [
        blogs.order_by().annotate(
            feed_kind=Value('blog', output_field=CharField()),
            feed_date=Coalesce('published_at', 'created_at'),
        ).values('pk', 'feed_kind', 'feed_date'),
        HistoryArticle.objects.order_by().annotate(
            feed_kind=Value('history', output_field=CharField()),
            feed_date=F('published_at'),
        ).values('pk', 'feed_kind', 'feed_date'),
        Words.objects.order_by().annotate(
            feed_kind=Value('word', output_field=CharField()),
            feed_date=Coalesce('created_at', Value(fallback, output_field=DateTimeField())),
        ).values('pk', 'feed_kind', 'feed_date'),
    ]
    feed = sources[0].union(*sources[1:], all=True)
    total = feed.count()
    rows = list(feed.order_by('-feed_date', 'feed_kind', '-pk')[offset:offset + limit])
    ids = {kind: [r['pk'] for r in rows if r['feed_kind'] == kind]
           for kind in ('blog', 'history', 'word')}
    posts = blogs.filter(pk__in=ids['blog']).only('title', 'body', 'slug', 'cover_image').in_bulk()
    articles = HistoryArticle.objects.filter(pk__in=ids['history']).only(
        'title', 'excerpt', 'slug', 'thumbnail',
    ).in_bulk()
    words = Words.objects.filter(pk__in=ids['word']).only('word', 'slug').annotate(
        first_meaning=Subquery(Meaning.objects.filter(word_id=OuterRef('pk'))
                              .order_by('pk').values('meaning')[:1]),
    ).in_bulk()

    items = []
    for row in rows:
        kind, pk = row['feed_kind'], row['pk']
        if kind == 'blog':
            obj = posts.get(pk)
            if obj is None:
                continue
            title = obj.title
            excerpt = strip_tags(obj.body)[:300] or 'Read more...'
            thumbnail = obj.cover_image.url if obj.cover_image else None
            url = reverse('blog:blog_detail', kwargs={'slug': obj.slug})
        elif kind == 'history':
            obj = articles.get(pk)
            if obj is None:
                continue
            title, excerpt = obj.title, obj.excerpt.strip() or 'Read more...'
            thumbnail = obj.thumbnail.url if obj.thumbnail else None
            url = reverse('history_detail', kwargs={'slug': obj.slug})
        else:
            obj = words.get(pk)
            if obj is None:
                continue
            title, excerpt = obj.word, (obj.first_meaning or f'Igala word: {obj.word}')[:300]
            thumbnail = None
            url = reverse('single-word', kwargs={'slug': obj.slug})
        items.append({'title': title, 'excerpt': excerpt, 'thumbnail_url': thumbnail,
                      'url': url, 'type': kind, 'date': row['feed_date']})
    return items, offset + limit < total, total
