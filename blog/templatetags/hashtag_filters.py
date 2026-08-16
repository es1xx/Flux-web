from django import template

from blog.hashtags import linkify_hashtags

register = template.Library()

CAPTION_PREVIEW_LENGTH = 38


@register.filter(name='linkify_hashtags')
def linkify_hashtags_filter(value):
    """Render #hashtags in full caption/detail text as clickable links."""
    return linkify_hashtags(value)


@register.filter(name='caption_preview')
def caption_preview_filter(value, length=CAPTION_PREVIEW_LENGTH):
    """Truncate caption for feed cards (35–40 chars) and linkify hashtags."""
    try:
        max_len = int(length)
    except (TypeError, ValueError):
        max_len = CAPTION_PREVIEW_LENGTH
    return linkify_hashtags(value, truncate_to=max_len)
