from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('post/create/', views.create_post, name='create_post'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/<int:pk>/edit/', views.edit_post, name='edit_post'),
    path('post/<int:pk>/delete/', views.delete_post, name='delete_post'),
    path('post/<int:pk>/like/', views.toggle_like, name='toggle_like'),
    path('post/<int:pk>/rate/', views.rate_post, name='rate_post'),
    path('comment/<int:pk>/delete/', views.delete_comment, name='delete_comment'),
    path('author/<str:username>/', views.author_posts, name='author_posts'),
    path('profile/', views.profile, name='profile'),
    path('subscribe/toggle/', views.toggle_subscription, name='toggle_subscription'),
    # Specific tag actions BEFORE dynamic slug matcher (avoids 404 on /tag/create/)
    path('tag/create/', views.create_tag, name='create_tag'),
    path('tag/<slug:tag_slug>/', views.tag_posts, name='tag_posts'),
]
