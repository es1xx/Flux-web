from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from .models import Post, UserProfile


class HashtagFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='Testpass123!')
        UserProfile.objects.get_or_create(user=self.user)

        self.post_wallpaper = Post.objects.create(
            title='Wallpaper post',
            content='My new photo #wallpaper #archlinux',
            author=self.user,
            status='published',
        )
        self.post_python = Post.objects.create(
            title='Python post',
            content='About Python #django',
            author=self.user,
            status='published',
        )
        self.draft_post = Post.objects.create(
            title='Draft post',
            content='Hidden #wallpaper',
            author=self.user,
            status='draft',
        )

    def test_hashtag_posts_page_filters_by_caption(self):
        response = self.client.get(reverse('tag_posts', args=['wallpaper']))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Wallpaper post')
        self.assertEqual(list(response.context['posts']), [self.post_wallpaper])
        self.assertNotIn(self.post_python, response.context['posts'])
        self.assertNotIn(self.draft_post, response.context['posts'])

    def test_tag_create_before_slug_matcher(self):
        self.client.login(username='tester', password='Testpass123!')
        response = self.client.get(reverse('create_tag'))
        self.assertIn(response.status_code, (301, 302))
        self.assertIn('/post/create/', response.url)

    def test_home_search_by_hashtag_query(self):
        response = self.client.get(reverse('home'), {'q': '#django'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['posts']), [self.post_python])

    def test_language_prefixed_urls(self):
        response = self.client.get('/en/')
        self.assertEqual(response.status_code, 200)
        response_uk = self.client.get('/uk/')
        self.assertEqual(response_uk.status_code, 200)
        root = self.client.get('/')
        self.assertIn(root.status_code, (301, 302))

    def test_profile_auto_creates_missing_userprofile(self):
        orphan = User.objects.create_user(username='orphan', password='Testpass123!')
        UserProfile.objects.filter(user=orphan).delete()
        self.assertFalse(UserProfile.objects.filter(user=orphan).exists())

        self.client.login(username='orphan', password='Testpass123!')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserProfile.objects.filter(user=orphan).exists())

    def test_create_post_publish_button_sets_status(self):
        self.client.login(username='tester', password='Testpass123!')
        response = self.client.post(reverse('create_post'), {
            'title': 'Published via button',
            'content': 'Hello #flux',
            'status': 'published',
        })
        self.assertIn(response.status_code, (301, 302))
        post = Post.objects.get(title='Published via button')
        self.assertEqual(post.status, 'published')

    def test_create_post_draft_button_sets_status(self):
        self.client.login(username='tester', password='Testpass123!')
        response = self.client.post(reverse('create_post'), {
            'title': 'Draft via button',
            'content': 'Hello draft',
            'status': 'draft',
        })
        self.assertIn(response.status_code, (301, 302))
        post = Post.objects.get(title='Draft via button')
        self.assertEqual(post.status, 'draft')

    def test_profile_update_does_not_shadow_gettext(self):
        self.client.login(username='tester', password='Testpass123!')
        response = self.client.post(reverse('profile'), {
            'form_type': 'edit_profile',
            'username': 'tester',
        })
        self.assertIn(response.status_code, (200, 301, 302))
        if response.status_code in (301, 302):
            self.assertIn('/profile/', response.url)

    def test_trending_hashtags_in_home_context(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        trending = list(response.context['trending_hashtags'])
        tags = [tag for tag, _count in trending]
        self.assertIn('wallpaper', tags)
        self.assertIn('django', tags)
        self.assertLessEqual(len(trending), 8)
        self.assertContains(response, 'Trending Hashtags')

        self.client.login(username='tester', password='Testpass123!')
        authed = self.client.get(reverse('home'))
        self.assertContains(authed, 'logoutConfirmModal', html=False)
        self.assertContains(authed, 'flux-nav-plus', html=False)
        self.assertContains(authed, 'flux-fab-plus', html=False)
