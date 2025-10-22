from django import template
from django.utils.text import slugify
from django.urls import reverse
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def split_terms(value, delimiter=','):
    """Split a string by delimiter and return a list"""
    if value:
        return [term.strip() for term in value.split(delimiter) if term.strip()]
    return []


@register.filter
def create_word_link(word):
    """Create a clickable link for a word"""
    from dictionary.models import Words
    
    # Try to find the word in database
    try:
        word_obj = Words.objects.filter(word__iexact=word.strip()).first()
        if word_obj:
            url = reverse('single-word', kwargs={'slug': word_obj.slug})
            return mark_safe(f'<a href="{url}" class="related-term-link">{word}</a>')
    except:
        pass
    
    # If word not found, return as plain text
    return word


@register.simple_tag
def related_terms_html(related_terms_string):
    """Convert related terms string to HTML with links"""
    from dictionary.models import Words
    
    if not related_terms_string:
        return ""
    
    terms = [term.strip() for term in related_terms_string.split(',') if term.strip()]
    html_parts = []
    
    for term in terms:
        # Try to find the word in database
        word_obj = Words.objects.filter(word__iexact=term).first()
        if word_obj:
            url = reverse('single-word', kwargs={'slug': word_obj.slug})
            html_parts.append(f'<a href="{url}" class="related-term-link">{term}</a>')
        else:
            html_parts.append(f'<span class="related-term-plain">{term}</span>')
    
    return mark_safe(', '.join(html_parts))

