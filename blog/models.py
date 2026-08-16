from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class UserProfile(models.Model):
    """Extended user profile for blog users."""
    ROLES = (
        ('user', 'User'),
        ('author', 'Author'),
        ('admin', 'Admin'),
    )

    NICKNAME_COOLDOWN = timedelta(days=3)
    AVATAR_COOLDOWN = timedelta(hours=1)

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLES, default='user')
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.png', null=True, blank=True)
    subscribe_to_new_posts = models.BooleanField(default=False)
    last_nickname_change = models.DateTimeField(null=True, blank=True, default=None)
    last_avatar_change = models.DateTimeField(null=True, blank=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)

    DEFAULT_AVATAR = 'avatars/default.png'

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def has_custom_avatar(self):
        """True when the user uploaded a real avatar (not the default placeholder)."""
        if not self.avatar or not getattr(self.avatar, 'name', None):
            return False
        return self.avatar.name != self.DEFAULT_AVATAR

    def _remaining(self, last_change, cooldown):
        if not last_change:
            return timedelta(0)
        elapsed = timezone.now() - last_change
        remaining = cooldown - elapsed
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    def nickname_cooldown_remaining(self):
        return self._remaining(self.last_nickname_change, self.NICKNAME_COOLDOWN)

    def avatar_cooldown_remaining(self):
        return self._remaining(self.last_avatar_change, self.AVATAR_COOLDOWN)

    def can_change_nickname(self):
        return self.nickname_cooldown_remaining().total_seconds() <= 0

    def can_change_avatar(self):
        return self.avatar_cooldown_remaining().total_seconds() <= 0

    @staticmethod
    def format_remaining(delta):
        """Human-readable remaining cooldown, e.g. '2 days and 14 hours'."""
        total_seconds = int(max(delta.total_seconds(), 0))
        if total_seconds <= 0:
            return 'now'

        days, rem = divmod(total_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)

        parts = []
        if days:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if not days and minutes:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if not parts:
            parts.append('less than a minute')

        if len(parts) == 1:
            return parts[0]
        if len(parts) == 2:
            return f"{parts[0]} and {parts[1]}"
        return f"{parts[0]}, {parts[1]} and {parts[2]}"


class Post(models.Model):
    """Blog post model."""
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )

    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    image = models.ImageField(upload_to='posts/', null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes_count = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_comment_count(self):
        return self.comments.count()

    def update_average_rating(self):
        rating_data = self.ratings.aggregate(avg=models.Avg('value'))
        self.average_rating = rating_data['avg'] or 0.00
        self.save(update_fields=['average_rating'])


class Comment(models.Model):
    """Comment model for blog posts."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.title}"


class Like(models.Model):
    """Like model for tracking post likes."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')

    def __str__(self):
        return f"{self.user.username} liked {self.post.title}"


class Rating(models.Model):
    """Post rating model."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    value = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} rated {self.post.title} {self.value}"


class Announcement(models.Model):
    """Announcement created by Admins."""
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='announcements')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Subscription(models.Model):
    """Subscription record for users."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    subscribed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} subscription: {self.subscribed}"
