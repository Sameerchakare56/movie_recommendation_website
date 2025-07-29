from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import RegisterForm, LoginForm, ProfileUpdateForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .forms import RegisterForm

from django.utils import timezone
from .models import Movie, UserInteraction, Profile

import json
import os
from django.conf import settings
from .templatetags.recommendation import get_trending_movies
from django.db.models import Count, Q, Avg
from django.http import JsonResponse
from django.views.decorators.http import require_POST

def adventure_movies(request):
    adventure_movies = Movie.objects.filter(genres__contains='Adventure')
    return render(request, 'adventure_movies.html', {'movies': adventure_movies})
def Movies(request, movie_id=None):
    # Get all movies from database
    db_movies = Movie.objects.all()
    
    # Get movies from poster files
    posters_dir = os.path.join(settings.MEDIA_ROOT, 'posters')
    poster_files = []

    if os.path.exists(posters_dir):
        for filename in os.listdir(posters_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                poster_files.append({
                    'title': os.path.splitext(filename)[0].replace("_", " ").title(),
                    'poster_url': f'/media/posters/{filename}',
                    'is_poster_file': True  # Flag to identify poster file movies
                })

    # Get movies for each genre
    genre_movies = {}
    for genre in Movie.GENRE_CHOICES:
        genre_name = genre[0]
        if genre_name != 'Other':  # Skip the 'Other' category
            genre_movies[genre_name] = Movie.objects.filter(genres__contains=genre_name)

    # Get user profile data if user is authenticated
    profile = None
    if request.user.is_authenticated:
        profile, created = Profile.objects.get_or_create(user=request.user)
        now = timezone.now()
        last_login = request.user.last_login
        time_spent = now - last_login if last_login else None
    else:
        time_spent = None

    # Get trending movies
    trending_movies = get_trending_movies()

    # Initialize variables for movie detail
    selected_movie = None
    similar_movies = None
    interaction = None
    average_rating = None
    reviews = None

    # If a specific movie is selected
    if movie_id:
        selected_movie = get_object_or_404(Movie, id=movie_id)
        
        # Get user interaction if authenticated
        if request.user.is_authenticated:
            interaction, created = UserInteraction.objects.get_or_create(
                user=request.user,
                movie=selected_movie
            )
        
        # Calculate average rating for the movie
        average_rating = UserInteraction.objects.filter(
            movie=selected_movie,
            rating__isnull=False
        ).aggregate(Avg('rating'))['rating__avg']
        
        if average_rating:
            average_rating = round(average_rating, 1)
        else:
            average_rating = "N/A"

        # Get all reviews for this movie, most recent first
        reviews = UserInteraction.objects.filter(movie=selected_movie).exclude(review__isnull=True).exclude(review='').order_by('-watch_date')
        
        # Get similar movies based on genres
        similar_movies = Movie.objects.filter(
            genres__in=selected_movie.genres
        ).exclude(
            id=selected_movie.id  # Exclude the current movie
        ).annotate(
            genre_match_count=Count('genres', filter=Q(genres__in=selected_movie.genres))
        ).order_by('-genre_match_count', '-release_date')[:6]  # Get top 6 similar movies
        
        # If user is authenticated, get movies that similar users liked
        if request.user.is_authenticated:
            # Get users who rated this movie highly
            similar_users = UserInteraction.objects.filter(
                movie=selected_movie,
                rating__gte=4
            ).values_list('user_id', flat=True)
            
            # Get movies that similar users rated highly
            similar_user_movies = Movie.objects.filter(
                userinteraction__user__in=similar_users,
                userinteraction__rating__gte=4
            ).exclude(
                id=selected_movie.id  # Exclude the current movie
            ).annotate(
                similar_user_count=Count('userinteraction__user', distinct=True)
            ).order_by('-similar_user_count', '-release_date')[:6]
            
            # Combine both sets of similar movies, prioritizing genre matches
            similar_movies = list(similar_movies) + list(similar_user_movies)
            # Remove duplicates while preserving order
            seen = set()
            similar_movies = [m for m in similar_movies if not (m.id in seen or seen.add(m.id))]
            similar_movies = similar_movies[:6]  # Keep only top 6

    context = {
        'movies': db_movies,  # Use database movies instead of poster files
        'genre_movies': genre_movies,
        'profile': profile,
        'time_spent': time_spent,
        'trending_movies': trending_movies,
        'selected_movie': selected_movie,
        'similar_movies': similar_movies,
        'interaction': interaction,
        'average_rating': average_rating,
        'reviews': reviews,
    }
    return render(request, 'Movies.html', context)
    
def home(request):
    # Get all movies from database
    db_movies = Movie.objects.all()
    
    # Get movies from poster files
    posters_dir = os.path.join(settings.MEDIA_ROOT, 'posters')
    poster_files = []

    if os.path.exists(posters_dir):
        for filename in os.listdir(posters_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                poster_files.append({
                    'title': os.path.splitext(filename)[0].replace("_", " ").title(),
                    'poster_url': f'/media/posters/{filename}',
                    'is_poster_file': True  # Flag to identify poster file movies
                })

    # Get movies for each genre
    genre_movies = {}
    for genre in Movie.GENRE_CHOICES:
        genre_name = genre[0]
        if genre_name != 'Other':  # Skip the 'Other' category
            genre_movies[genre_name] = Movie.objects.filter(genres__contains=genre_name)

    # Get user profile data if user is authenticated
    profile = None
    if request.user.is_authenticated:
        profile, created = Profile.objects.get_or_create(user=request.user)
        now = timezone.now()
        last_login = request.user.last_login
        time_spent = now - last_login if last_login else None
    else:
        time_spent = None

    # Get trending movies
    trending_movies = get_trending_movies()

    context = {
        'movies': db_movies,  # Use database movies instead of poster files
        'genre_movies': genre_movies,
        'profile': profile,
        'time_spent': time_spent,
        'trending_movies': trending_movies,
    }
    return render(request, 'home.html', context)

def profile(request):
    if request.user.is_authenticated:
        now = timezone.now()
        last_login = request.user.last_login

        # Calculate the time spent since last login
        time_spent = now - last_login if last_login else None

        context = {
            'time_spent': time_spent,
        }
        return render(request, 'profile.html', context)



class CustomLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('watch-home')




def register_view(request):
    if request.user.is_authenticated:
        return redirect('watch-home')  # If user already logged in, redirect to home

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful. Please log in.")
            return redirect('login')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('watch-home')  # Already logged in

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('watch-home')
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, "You have been logged out.")
        return redirect('watch-home')
    return redirect('watch-home')  # If accessed via GET, just redirect to home


def home_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'home.html')
@login_required
def profile_view(request):
    # Get or create the user's profile
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    now = timezone.now()
    last_login = request.user.last_login

    # Calculate the time spent since last login
    time_spent = now - last_login if last_login else None

    context = {
        'time_spent': time_spent,
    }
    return render(request, 'profile.html', context)

@login_required
def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    
    # Get or create user interaction
    interaction, created = UserInteraction.objects.get_or_create(
        user=request.user,
        movie=movie
    )
    
    # Handle rating submission
    if request.method == 'POST':
        rating = request.POST.get('rating')
        review = request.POST.get('review')
        watched = request.POST.get('watched') == 'on'
        
        if rating:
            interaction.rating = int(rating)
        if review:
            interaction.review = review
        interaction.watched = watched
        interaction.save()
        
        messages.success(request, 'Your interaction has been saved!')
        return redirect('movie_detail', movie_id=movie_id)
    
    # Calculate average rating for the movie
    average_rating = UserInteraction.objects.filter(
        movie=movie,
        rating__isnull=False
    ).aggregate(Avg('rating'))['rating__avg']
    
    if average_rating:
        average_rating = round(average_rating, 1)
    else:
        average_rating = "N/A"

    # Get all reviews for this movie
    reviews = UserInteraction.objects.filter(movie=movie).exclude(review__isnull=True).exclude(review='')
    
    # Get similar movies based on genres
    similar_movies = Movie.objects.filter(
        genres__in=movie.genres
    ).exclude(
        id=movie.id  # Exclude the current movie
    ).annotate(
        genre_match_count=Count('genres', filter=Q(genres__in=movie.genres))
    ).order_by('-genre_match_count', '-release_date')[:6]  # Get top 6 similar movies
    
    # If user is authenticated, get movies that similar users liked
    if request.user.is_authenticated:
        # Get users who rated this movie highly
        similar_users = UserInteraction.objects.filter(
            movie=movie,
            rating__gte=4
        ).values_list('user_id', flat=True)
        
        # Get movies that similar users rated highly
        similar_user_movies = Movie.objects.filter(
            userinteraction__user__in=similar_users,
            userinteraction__rating__gte=4
        ).exclude(
            id=movie.id  # Exclude the current movie
        ).annotate(
            similar_user_count=Count('userinteraction__user', distinct=True)
        ).order_by('-similar_user_count', '-release_date')[:6]
        
        # Combine both sets of similar movies, prioritizing genre matches
        similar_movies = list(similar_movies) + list(similar_user_movies)
        # Remove duplicates while preserving order
        seen = set()
        similar_movies = [m for m in similar_movies if not (m.id in seen or seen.add(m.id))]
        similar_movies = similar_movies[:6]  # Keep only top 6
    
    context = {
        'movie': movie,
        'interaction': interaction,
        'reviews': reviews,
        'similar_movies': similar_movies,
        'average_rating': average_rating,
    }
    return render(request, 'movie_detail.html', context)

@login_required
def profile_update(request):
    # Get or create the user's profile
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('dashboard')
    else:
        form = ProfileUpdateForm(instance=profile)
    
    return render(request, 'profile_update.html', {'form': form})

def trending(request):
    # Get trending movies
    trending_movies = get_trending_movies(request.user if request.user.is_authenticated else None)
    
    # Get personalized recommendations for authenticated users
    recommended_movies = None
    new_movies = None
    favorite_movies = None
    
    if request.user.is_authenticated:
        # Get user's favorite movies (highly rated watched movies)
        favorite_movies = Movie.objects.filter(
            userinteraction__user=request.user,
            userinteraction__watched=True,
            userinteraction__rating__gte=4
        ).order_by('-userinteraction__rating', '-userinteraction__watch_date')[:10]
        
        # Get user's highly rated movies (rating >= 4)
        highly_rated_movies = UserInteraction.objects.filter(
            user=request.user,
            rating__gte=4
        ).values_list('movie__genres', flat=True)
        
        # Get user's preferred genres
        preferred_genres = []
        for genres in highly_rated_movies:
            if genres:
                preferred_genres.extend(genres)
        
        # Get movies that match user's preferred genres
        if preferred_genres:
            # Count genre occurrences
            from collections import Counter
            genre_counts = Counter(preferred_genres)
            top_genres = [genre for genre, _ in genre_counts.most_common(3)]
            
            # Get movies with matching genres using Q objects
            genre_queries = Q()
            for genre in top_genres:
                genre_queries |= Q(genres__contains=genre)
            
            # Get movies with matching genres
            recommended_movies = Movie.objects.filter(genre_queries).exclude(
                userinteraction__user=request.user,
                userinteraction__watched=True
            ).distinct()
            
            # Annotate with genre match score
            recommended_movies = recommended_movies.annotate(
                genre_match_score=Count('genres', filter=Q(genres__in=top_genres))
            ).order_by('-genre_match_score', '-release_date')[:20]
        
        # Collaborative filtering for new releases
        # Find similar users based on rating patterns
        user_ratings = UserInteraction.objects.filter(
            user=request.user,
            rating__isnull=False
        ).values_list('movie_id', 'rating')
        
        if user_ratings:
            # Get users who rated the same movies similarly
            similar_users = UserInteraction.objects.filter(
                movie__in=[r[0] for r in user_ratings],
                rating__isnull=False
            ).exclude(user=request.user).values('user').annotate(
                similarity=Count('id')
            ).order_by('-similarity')[:10]
            
            # Get movies that similar users rated highly
            similar_user_ids = [u['user'] for u in similar_users]
            new_movies = Movie.objects.filter(
                userinteraction__user__in=similar_user_ids,
                userinteraction__rating__gte=4
            ).exclude(
                userinteraction__user=request.user,
                userinteraction__watched=True
            ).annotate(
                similar_user_count=Count('userinteraction__user', distinct=True)
            ).order_by('-similar_user_count', '-release_date')[:20]
    
    # If no collaborative filtering results or user not authenticated, get regular new releases
    if not new_movies:
        new_movies = Movie.objects.all()
        if request.user.is_authenticated:
            new_movies = new_movies.exclude(
                userinteraction__user=request.user,
                userinteraction__watched=True
            )
        new_movies = new_movies.order_by('-release_date')[:20]
    
    # Get user profile data if user is authenticated
    profile = None
    if request.user.is_authenticated:
        profile, created = Profile.objects.get_or_create(user=request.user)
        now = timezone.now()
        last_login = request.user.last_login
        time_spent = now - last_login if last_login else None
    else:
        time_spent = None

    context = {
        'trending_movies': trending_movies,
        'new_movies': new_movies,
        'recommended_movies': recommended_movies,
        'favorite_movies': favorite_movies,
        'profile': profile,
        'time_spent': time_spent,
    }
    return render(request, 'trending.html', context)

def search_movies(request):
    query = request.GET.get('q', '')
    if query:
        # Capitalize each word in the query
        capitalized_query = ' '.join(word.capitalize() for word in query.split())
        
        movies = Movie.objects.filter(
            Q(title__icontains=capitalized_query) |
            Q(description__icontains=capitalized_query) |
            Q(genres__icontains=capitalized_query)
        ).distinct()
    else:
        movies = []
        capitalized_query = ''
    
    context = {
        'movies': movies,
        'query': capitalized_query,
        'search_performed': bool(query),
        'no_results': bool(query) and not movies.exists()
    }
    return render(request, 'search_results.html', context)

@login_required
@require_POST
def update_watched(request, movie_id):
    try:
        movie = Movie.objects.get(id=movie_id)
        interaction, created = UserInteraction.objects.get_or_create(user=request.user, movie=movie)
        # Set watched based on checkbox value
        interaction.watched = 'watched' in request.POST
        # Optionally update rating and review if present
        rating = request.POST.get('rating')
        if rating:
            interaction.rating = int(rating)
        review = request.POST.get('review')
        if review is not None:
            interaction.review = review
        interaction.save()
        # Redirect back to the movie detail page
        from django.urls import reverse
        return redirect(reverse('movie_detail', args=[movie_id]))
    except Movie.DoesNotExist:
        from django.http import HttpResponseNotFound
        return HttpResponseNotFound('Movie not found')