from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import re
from .models import Post, Comment, UserProfile


class UserRegisterForm(forms.ModelForm):
    """Custom user registration form with strict validation"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-lg',
            'style': 'background-color: #282838; border-color: #3A3A4C; color: #FFFFFF;',
            'placeholder': _('Enter password'),
        }),
        label=_('Password')
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-lg',
            'style': 'background-color: #282838; border-color: #3A3A4C; color: #FFFFFF;',
            'placeholder': _('Confirm password'),
        }),
        label=_('Confirm Password')
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
                'style': 'background-color: #282838; border-color: #3A3A4C; color: #FFFFFF;',
                'placeholder': _('Enter username'),
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
                'style': 'background-color: #282838; border-color: #3A3A4C; color: #FFFFFF;',
                'placeholder': _('Enter email'),
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
                'style': 'background-color: #282838; border-color: #3A3A4C; color: #FFFFFF;',
                'placeholder': _('First name (optional)'),
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
                'style': 'background-color: #282838; border-color: #3A3A4C; color: #FFFFFF;',
                'placeholder': _('Last name (optional)'),
            }),
        }

    def clean_username(self):
        """Validation Rule 1: Check if username already exists"""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError(_('This username is already taken. Please choose another one.'))
        if len(username) < 3:
            raise ValidationError(_('Username must be at least 3 characters long.'))
        return username

    def clean_password(self):
        """Validation Rule 2: Strict password strength validation"""
        password = self.cleaned_data.get('password')

        if len(password) < 8:
            raise ValidationError(_('Password must be at least 8 characters long.'))

        if password.isdigit():
            raise ValidationError(_('Password cannot contain only numbers.'))
        if password.isalpha():
            raise ValidationError(_('Password must contain both letters and numbers/symbols.'))

        weak_passwords = ['12345678', 'password', '1234', 'admin', 'user', 'qwerty', 'abc123']
        if password.lower() in weak_passwords:
            raise ValidationError(_('This password is too common. Please choose a stronger password.'))

        has_letter = re.search(r'[a-zA-Z]', password)
        has_digit_or_special = re.search(r'[0-9!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password)

        if not (has_letter and has_digit_or_special):
            raise ValidationError(_('Password must contain a mix of letters and numbers/special characters.'))

        return password

    def clean_password2(self):
        """Ensure passwords match"""
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        if password and password2 and password != password2:
            raise ValidationError(_('Passwords do not match.'))
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            UserProfile.objects.get_or_create(user=user)
        return user


class UserLoginForm(forms.Form):
    """User login form"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-lg',
            'style': 'background-color: #282838; border-color: #3A3A4C; color: #FFFFFF;',
            'placeholder': _('Username'),
        }),
        label=_('Username')
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-lg',
            'style': 'background-color: #282838; border-color: #3A3A4C; color: #FFFFFF;',
            'placeholder': _('Password'),
        }),
        label=_('Password')
    )


class PostForm(forms.ModelForm):
    """Form for creating and editing blog posts (status via action buttons)."""

    class Meta:
        model = Post
        fields = ('title', 'content', 'image')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'flux-input',
                'placeholder': _('Give your post a title'),
            }),
            'content': forms.Textarea(attrs={
                'class': 'flux-input flux-textarea',
                'placeholder': _('Write a caption… use #hashtags inline'),
                'rows': 8,
            }),
            'image': forms.FileInput(attrs={
                'class': 'flux-file-input',
                'accept': 'image/*',
                'id': 'id_image',
            }),
        }
        labels = {
            'title': _('Title'),
            'content': _('Caption'),
            'image': _('Cover Image'),
        }


class ProfileEditForm(forms.Form):
    """Edit username and avatar with cooldown enforcement."""
    username = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'flux-input',
            'placeholder': _('Username'),
            'autocomplete': 'username',
        }),
        label=_('Username'),
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'flux-file-input',
            'accept': 'image/*',
            'id': 'id_profile_avatar',
        }),
        label=_('Avatar'),
    )

    def __init__(self, user, profile, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.profile = profile
        self.fields['username'].initial = user.username

        if not profile.can_change_nickname():
            remaining = UserProfile.format_remaining(profile.nickname_cooldown_remaining())
            self.fields['username'].disabled = True
            self.fields['username'].help_text = (
                _('You can change your username again in %(remaining)s.') % {'remaining': remaining}
            )

        if not profile.can_change_avatar():
            remaining = UserProfile.format_remaining(profile.avatar_cooldown_remaining())
            self.fields['avatar'].disabled = True
            self.fields['avatar'].help_text = (
                _('You can change your avatar again in %(remaining)s.') % {'remaining': remaining}
            )

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if self.fields['username'].disabled:
            return self.user.username

        if not username:
            return self.user.username

        if len(username) < 3:
            raise ValidationError(_('Username must be at least 3 characters long.'))

        if not re.match(r'^[\w.@+-]+$', username):
            raise ValidationError(_('Username may only contain letters, digits, and @/./+/-/_ characters.'))

        if username != self.user.username:
            if not self.profile.can_change_nickname():
                remaining = UserProfile.format_remaining(self.profile.nickname_cooldown_remaining())
                raise ValidationError(
                    _('You can change your username again in %(remaining)s.') % {'remaining': remaining}
                )
            if User.objects.filter(username=username).exclude(pk=self.user.pk).exists():
                raise ValidationError(_('This username is already taken. Please choose another one.'))

        return username

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if self.fields['avatar'].disabled:
            return None

        if avatar and not self.profile.can_change_avatar():
            remaining = UserProfile.format_remaining(self.profile.avatar_cooldown_remaining())
            raise ValidationError(
                _('You can change your avatar again in %(remaining)s.') % {'remaining': remaining}
            )
        return avatar

    def save(self):
        changed = False
        username = self.cleaned_data.get('username')
        avatar = self.cleaned_data.get('avatar')
        now = timezone.now()

        if username and username != self.user.username:
            self.user.username = username
            self.user.save(update_fields=['username'])
            self.profile.last_nickname_change = now
            changed = True

        if avatar:
            self.profile.avatar = avatar
            self.profile.last_avatar_change = now
            changed = True

        if changed:
            self.profile.save()
        return self.profile


class CommentForm(forms.ModelForm):
    """Form for adding comments."""
    class Meta:
        model = Comment
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
                'style': 'background-color: #282838; border-color: #3A3A4C; color: #FFFFFF;',
                'placeholder': _('Add your comment...'),
                'rows': 4
            }),
        }


class RatingForm(forms.Form):
    """Form used by users to submit a post rating."""
    value = forms.ChoiceField(
        choices=[(i, str(i)) for i in range(1, 6)],
        widget=forms.RadioSelect(attrs={'class': 'rating-options'})
    )
