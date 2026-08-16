from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import (
    Post,
    Comment,
    Like,
    UserProfile,
    Announcement,
    Rating,
    Subscription,
)
from .forms import (
    UserRegisterForm,
    UserLoginForm,
    PostForm,
    CommentForm,
    RatingForm,
    ProfileEditForm,
)
from .hashtags import normalize_hashtag

FEED_TIMEFRAMES = {
    'day': timedelta(days=1),
    'month': timedelta(days=30),
    'year': timedelta(days=365),
}


def _feed_timeframe_cutoff(timeframe):
    delta = FEED_TIMEFRAMES.get(timeframe)
    if not delta:
        return None
    return timezone.now() - delta


def _build_feed_queryset(request, base_qs=None):
    """Build feed queryset: chronological by default, or top-rated by timeframe."""
    qs = base_qs if base_qs is not None else Post.objects.filter(status='published')
    sort = (request.GET.get('sort') or 'latest').lower()
    timeframe = (request.GET.get('timeframe') or '').lower()
    tag = normalize_hashtag(request.GET.get('tag') or '')
    query = (request.GET.get('q') or '').strip()

    if tag:
        qs = qs.filter(content__icontains=f'#{tag}')
    elif query:
        if query.startswith('#'):
            qs = qs.filter(content__icontains=query)
            tag = normalize_hashtag(query)
        else:
            qs = qs.filter(Q(title__icontains=query) | Q(content__icontains=query))

    if sort == 'top' and timeframe in FEED_TIMEFRAMES:
        cutoff = _feed_timeframe_cutoff(timeframe)
        qs = qs.filter(created_at__gte=cutoff).order_by('-average_rating', '-created_at', '-pk')
        feed_mode = 'top'
    else:
        qs = qs.order_by('-created_at', '-pk')
        sort = 'latest'
        timeframe = ''
        feed_mode = 'latest'

    return qs, sort, timeframe, feed_mode, tag, query


def _annotate_feed_posts(queryset, user):
    posts = list(
        queryset.annotate(
            likes=Count('post_likes', distinct=True),
            comments_count=Count('comments', distinct=True),
        ).select_related('author', 'author__profile').prefetch_related('comments__author')
    )
    liked_ids = set()
    if user.is_authenticated and posts:
        liked_ids = set(
            Like.objects.filter(
                user=user,
                post_id__in=[p.pk for p in posts],
            ).values_list('post_id', flat=True)
        )
    for post in posts:
        post.user_liked = post.pk in liked_ids
    return posts


def _feed_heading(sort, timeframe, selected_tag=None, query=None):
    if selected_tag:
        return _('Posts tagged #%(tag)s') % {'tag': selected_tag}
    if query:
        return _('Search: "%(query)s"') % {'query': query}
    if sort == 'top' and timeframe:
        labels = {
            'day': _('Top Day'),
            'month': _('Top Month'),
            'year': _('Top Year'),
        }
        return labels.get(timeframe, _('Top Rated'))
    return _('Latest Posts')


def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Account created successfully! You can now login.'))
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'blog/register.html', {'form': form})


def _get_user_role(user):
    if not user.is_authenticated:
        return 'user'
    try:
        return user.profile.role
    except UserProfile.DoesNotExist:
        return 'user'


def _is_admin(user):
    return _get_user_role(user) == 'admin'


def _is_author(user):
    return _get_user_role(user) == 'author'


def _can_modify_post(user, post):
    return user.is_authenticated and (
        user == post.author
        or _is_admin(user)
        or user.is_staff
        or user.is_superuser
    )


def _can_delete_comment(user, comment):
    return user.is_authenticated and (
        _is_admin(user)
        or user == comment.author
        or (user == comment.post.author and _is_author(user))
    )


def login_view(request):
    """User login view"""
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, _('Welcome back, %(username)s!') % {'username': username})
                return redirect('home')
            messages.error(request, _('Invalid username or password.'))
    else:
        form = UserLoginForm()
    return render(request, 'blog/login.html', {'form': form})


def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, _('You have been logged out.'))
    return redirect('home')


def home(request):
    """Home/blog feed view — chronological newest-first by default."""
    qs, sort, timeframe, feed_mode, tag, query = _build_feed_queryset(request)
    posts = _annotate_feed_posts(qs, request.user)
    announcements = Announcement.objects.filter(is_active=True, created_by__profile__role='admin')

    context = {
        'posts': posts,
        'announcements': announcements,
        'feed_sort': sort,
        'feed_timeframe': timeframe,
        'feed_mode': feed_mode,
        'selected_tag': tag,
        'search_query': query,
        'feed_heading': _feed_heading(sort, timeframe, selected_tag=tag or None, query=query or None),
    }
    return render(request, 'blog/index.html', context)


@login_required(login_url='login')
def create_tag(request):
    """Legacy/create entry — hashtags are inline in captions, so send users to compose."""
    messages.info(request, _('Add #hashtags directly in your post caption.'))
    return redirect('create_post')


def tag_posts(request, tag_slug):
    """Filter the main feed by an inline caption hashtag."""
    tag = normalize_hashtag(tag_slug)
    if not tag:
        return redirect('home')

    base = Post.objects.filter(status='published', content__icontains=f'#{tag}')
    qs, sort, timeframe, feed_mode, _tag, _query = _build_feed_queryset(request, base)
    posts = _annotate_feed_posts(qs, request.user)
    announcements = Announcement.objects.filter(is_active=True, created_by__profile__role='admin')

    context = {
        'posts': posts,
        'announcements': announcements,
        'feed_sort': sort,
        'feed_timeframe': timeframe,
        'feed_mode': feed_mode,
        'selected_tag': tag,
        'search_query': '',
        'feed_heading': _feed_heading(sort, timeframe, selected_tag=tag),
    }
    return render(request, 'blog/index.html', context)


def post_detail(request, pk):
    """Individual post detail view with comments"""
    post = get_object_or_404(Post, pk=pk)
    post.likes_count = post.post_likes.count()
    comments = post.comments.all()
    is_author = request.user == post.author
    user_liked = False

    if request.user.is_authenticated:
        user_liked = post.post_likes.filter(user=request.user).exists()

    if request.method == 'POST' and request.user.is_authenticated:
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            messages.success(request, _('Comment added successfully!'))
            return redirect('post_detail', pk=post.pk)
    else:
        form = CommentForm()

    user_rating = None
    if request.user.is_authenticated:
        user_rating = Rating.objects.filter(post=post, user=request.user).first()

    comment_delete_ids = set()
    for comment in comments:
        if _can_delete_comment(request.user, comment):
            comment_delete_ids.add(comment.pk)

    context = {
        'post': post,
        'comments': comments,
        'form': form,
        'is_author': is_author,
        'user_liked': user_liked,
        'rating_form': RatingForm(),
        'user_rating': user_rating,
        'comment_delete_ids': comment_delete_ids,
    }
    return render(request, 'blog/post_detail.html', context)


def _resolve_post_status(request, default='draft'):
    """Read status from the Draft/Publish submit buttons."""
    status = (request.POST.get('status') or default).strip().lower()
    if status not in {'draft', 'published'}:
        return default
    return status


@login_required(login_url='login')
def create_post(request):
    """Create new blog post view"""
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.status = _resolve_post_status(request, default='draft')
            post.save()
            if post.status == 'published':
                messages.success(request, _('Post published successfully!'))
            else:
                messages.success(request, _('Draft saved successfully!'))
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm()

    context = {'form': form, 'action': _('Create'), 'current_status': 'draft'}
    return render(request, 'blog/post_form.html', context)


@login_required(login_url='login')
def edit_post(request, pk):
    """Edit blog post view"""
    post = get_object_or_404(Post, pk=pk)

    if request.user != post.author:
        messages.error(request, _('You can only edit your own posts.'))
        return redirect('post_detail', pk=post.pk)

    if not _can_modify_post(request.user, post):
        messages.error(request, _('You do not have permission to edit this post.'))
        return redirect('post_detail', pk=post.pk)

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            post.status = _resolve_post_status(request, default=post.status or 'draft')
            post.save()
            if post.status == 'published':
                messages.success(request, _('Post published successfully!'))
            else:
                messages.success(request, _('Draft saved successfully!'))
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm(instance=post)

    context = {
        'form': form,
        'post': post,
        'action': _('Edit'),
        'current_status': post.status,
    }
    return render(request, 'blog/post_form.html', context)


@login_required(login_url='login')
def delete_post(request, pk):
    """Delete blog post view."""
    post = get_object_or_404(Post, pk=pk)

    if not _can_modify_post(request.user, post):
        messages.error(request, _('You do not have permission to delete this post.'))
        return redirect('post_detail', pk=post.pk)

    if request.method == 'POST':
        post.delete()
        messages.success(request, _('Post deleted successfully!'))
        return redirect('home')

    context = {'post': post}
    return render(request, 'blog/post_confirm_delete.html', context)


@login_required(login_url='login')
def delete_comment(request, pk):
    """Delete a comment."""
    comment = get_object_or_404(Comment, pk=pk)
    post_id = comment.post.pk

    if not _can_delete_comment(request.user, comment):
        messages.error(request, _('You do not have permission to delete this comment.'))
        return redirect('post_detail', pk=post_id)

    if request.method == 'POST':
        comment.delete()
        messages.success(request, _('Comment deleted successfully!'))

    return redirect('post_detail', pk=post_id)


@login_required(login_url='login')
@require_POST
def toggle_like(request, pk):
    """Toggle like on a post (AJAX support)."""
    post = get_object_or_404(Post, pk=pk)

    like, created = Like.objects.get_or_create(post=post, user=request.user)

    if not created:
        like.delete()
        liked = False
    else:
        liked = True

    likes_count = post.post_likes.count()
    post.likes_count = likes_count
    post.save(update_fields=['likes_count'])

    accepts_json = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('Accept', '')
    )
    if accepts_json:
        return JsonResponse({
            'liked': liked,
            'likes_count': likes_count,
        })

    return redirect('post_detail', pk=post.pk)


@login_required(login_url='login')
@require_POST
def rate_post(request, pk):
    """Submit or update a rating for a post."""
    post = get_object_or_404(Post, pk=pk, status='published')
    form = RatingForm(request.POST)
    if form.is_valid():
        rating_value = int(form.cleaned_data['value'])
        Rating.objects.update_or_create(
            post=post,
            user=request.user,
            defaults={'value': rating_value}
        )
        post.update_average_rating()
        messages.success(request, _('Your rating has been saved.'))
    else:
        messages.error(request, _('Please select a valid rating.'))
    return redirect('post_detail', pk=post.pk)


@login_required(login_url='login')
def toggle_subscription(request):
    """Toggle email subscription for current user."""
    if request.method == 'POST':
        subscription, _created = Subscription.objects.get_or_create(user=request.user)
        subscription.subscribed = not subscription.subscribed
        subscription.save()
        if hasattr(request.user, 'profile'):
            request.user.profile.subscribe_to_new_posts = subscription.subscribed
            request.user.profile.save(update_fields=['subscribe_to_new_posts'])
        messages.success(request, _('Subscription preference updated.'))
    return redirect('profile')


def author_posts(request, username):
    """View all posts by a specific author."""
    author = get_object_or_404(User, username=username)
    if request.user == author or _is_admin(request.user) or request.user.is_staff or request.user.is_superuser:
        posts_qs = Post.objects.filter(author=author)
    else:
        posts_qs = Post.objects.filter(author=author, status='published')

    posts_qs = posts_qs.order_by('-created_at', '-pk')
    posts = _annotate_feed_posts(posts_qs, request.user)

    context = {
        'author': author,
        'posts': posts,
    }
    return render(request, 'blog/author_posts.html', context)


@login_required(login_url='login')
def profile(request):
    """User profile view with edit settings."""
    profile, _profile_created = UserProfile.objects.get_or_create(user=request.user)
    posts = request.user.posts.all().order_by('-created_at', '-pk')
    subscription, _subscription_created = Subscription.objects.get_or_create(user=request.user)
    total_likes = Like.objects.filter(post__author=request.user).count()

    if request.method == 'POST' and request.POST.get('form_type') == 'edit_profile':
        edit_form = ProfileEditForm(request.user, profile, request.POST, request.FILES)
        if edit_form.is_valid():
            edit_form.save()
            messages.success(request, _('Profile updated successfully.'))
            return redirect('profile')
        messages.error(request, _('Could not update profile. Please check the form.'))
    else:
        edit_form = ProfileEditForm(request.user, profile)

    nickname_remaining = profile.nickname_cooldown_remaining()
    avatar_remaining = profile.avatar_cooldown_remaining()

    context = {
        'profile': profile,
        'posts': posts,
        'subscription': subscription,
        'total_likes': total_likes,
        'edit_form': edit_form,
        'can_change_nickname': profile.can_change_nickname(),
        'can_change_avatar': profile.can_change_avatar(),
        'nickname_remaining_text': UserProfile.format_remaining(nickname_remaining),
        'avatar_remaining_text': UserProfile.format_remaining(avatar_remaining),
        'nickname_remaining_seconds': int(nickname_remaining.total_seconds()),
        'avatar_remaining_seconds': int(avatar_remaining.total_seconds()),
    }
    return render(request, 'blog/profile.html', context)
