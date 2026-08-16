"""Shared hashtag parsing helpers for captions."""
import re

from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe

# Letters, digits, underscore — Unicode-aware for UK/EN tags
HASHTAG_RE = re.compile(r'(?<!\w)#([\w]+)', re.UNICODE)


def normalize_hashtag(raw):
    if not raw:
        return ''
    tag = raw.strip().lstrip('#')
    tag = re.sub(r'[^\w]', '', tag, flags=re.UNICODE)
    return tag.lower()


def extract_hashtags(text):
    if not text:
        return []
    seen = []
    for match in HASHTAG_RE.findall(text):
        key = match.lower()
        if key not in seen:
            seen.append(key)
    return seen


def linkify_hashtags(text, truncate_to=None):
    """Escape text, optionally truncate, and turn #tags into monochrome links."""
    if text is None:
        text = ''
    plain = str(text)
    ellipsis = ''
    if truncate_to is not None and len(plain) > truncate_to:
        plain = plain[:truncate_to].rstrip()
        ellipsis = '…'

    parts = []
    last = 0
    for match in HASHTAG_RE.finditer(plain):
        parts.append(escape(plain[last:match.start()]))
        tag = match.group(1)
        url = reverse('tag_posts', kwargs={'tag_slug': tag.lower()})
        parts.append(
            f'<a href="{escape(url)}" class="ig-hashtag">#{escape(tag)}</a>'
        )
        last = match.end()
    parts.append(escape(plain[last:]))
    parts.append(escape(ellipsis) if ellipsis else '')
    html = ''.join(parts).replace('\n', '<br>')
    return mark_safe(html)
