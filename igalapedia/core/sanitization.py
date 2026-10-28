"""Allow only passive rich-text HTML in community content."""
import nh3


def sanitize_rich_text(value):
    return nh3.clean(
        value or '',
        tags={
            'p', 'br', 'div', 'span', 'strong', 'b', 'em', 'i', 'u', 's',
            'blockquote', 'pre', 'code', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'a', 'img', 'hr', 'sub', 'sup',
            'table', 'caption', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
            'figure', 'figcaption',
        },
        attributes={
            'a': {'href', 'title'},
            'img': {'src', 'alt', 'title', 'width', 'height'},
            'th': {'colspan', 'rowspan', 'scope'},
            'td': {'colspan', 'rowspan'},
        },
        clean_content_tags={'script', 'style', 'iframe', 'object', 'embed', 'svg', 'math'},
        url_schemes={'http', 'https', 'mailto'},
        link_rel='noopener noreferrer',
    )
