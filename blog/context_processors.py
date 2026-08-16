from .models import Post
from .hashtags import HASHTAG_RE, normalize_hashtag

TRENDING_HASHTAG_LIMIT = 8


def flux_nav(request):
    """Provide feed filter state and curated trending hashtags for the drawer."""
    sort = (request.GET.get('sort') or 'latest').lower()
    timeframe = (request.GET.get('timeframe') or '').lower()
    if sort != 'top' or timeframe not in {'day', 'month', 'year'}:
        sort = 'latest'
        timeframe = ''
        feed_mode = 'latest'
    else:
        feed_mode = 'top'

    selected_tag = normalize_hashtag(request.GET.get('tag') or '')
    resolver_match = getattr(request, 'resolver_match', None)
    if resolver_match and resolver_match.url_name == 'tag_posts':
        selected_tag = normalize_hashtag(resolver_match.kwargs.get('tag_slug') or selected_tag)

    tag_counts = {}
    for content in Post.objects.filter(status='published').values_list('content', flat=True):
        seen_in_post = set()
        for match in HASHTAG_RE.findall(content or ''):
            key = match.lower()
            if key in seen_in_post:
                continue
            seen_in_post.add(key)
            tag_counts[key] = tag_counts.get(key, 0) + 1

    trending_hashtags = sorted(
        tag_counts.items(),
        key=lambda item: (-item[1], item[0]),
    )[:TRENDING_HASHTAG_LIMIT]

    return {
        'trending_hashtags': trending_hashtags,
        'nav_hashtags': trending_hashtags,  # backwards-compatible alias
        'selected_tag': selected_tag,
        'feed_sort': sort,
        'feed_timeframe': timeframe,
        'feed_mode': feed_mode,
        'search_query': (request.GET.get('q') or '').strip(),
    }
