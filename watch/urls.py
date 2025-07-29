"""
URL configuration for watch project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import include, path
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from .views import home_view, register_view, CustomLoginView, logout_view,Movies
from . import views
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('adventure/', views.adventure_movies, name='adventure_movies'),
    path('admin/', admin.site.urls),
    path('', views.home, name='watch-home'),
    path('trending/', views.trending, name='trending'),
    path('dashboard/', views.profile_view, name='dashboard'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('Movies/', Movies, name='Movies'),
    path('Movies/<int:movie_id>/', Movies, name='movie_detail'),
    path('movie/<int:movie_id>/', views.movie_detail, name='movie_detail_old'),
    path('search/', views.search_movies, name='search_movies'),
    path('update_watched/<int:movie_id>/', views.update_watched, name='update_watched'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)