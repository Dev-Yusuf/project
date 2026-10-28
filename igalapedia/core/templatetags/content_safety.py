from django import template
from django.utils.safestring import mark_safe

from core.sanitization import sanitize_rich_text

register = template.Library()


@register.filter
def sanitized_html(value):
    return mark_safe(sanitize_rich_text(value))
