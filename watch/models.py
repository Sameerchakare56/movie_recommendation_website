from django.db import models
from django.contrib.auth.models import User
from django.db import models
from django.utils.html import format_html
from multiselectfield import MultiSelectField
from django.db.models import Count, Avg


class Movie(models.Model):
    GENRE_CHOICES = [('Horror', 'Horror'),
        ('Action', 'Action'),
        ('Comedy', 'Comedy'),
        ('Drama', 'Drama'),
        ('Romantic', 'Romantic'),
        ('Thriller', 'Thriller'),
        ('Fantasy', 'Fantasy'),
        ('Sci-Fi', 'Sci-Fi'),
        ('Superhero', 'Superhero'),
        ('Documentary', 'Documentary'),
        ('Animation', 'Animation'),
        ('Adventure', 'Adventure'),
        ('Crime', 'Crime'),
        ('Mystery', 'Mystery'),
        ('Biography', 'Biography'),
        ('History', 'History'),
        ('Family','Family'),
        ('Other', 'Other'),
           ]
    
    title = models.CharField(max_length=100)
    genres = MultiSelectField(choices=GENRE_CHOICES, default=['Other'])
    description = models.TextField()
    release_date = models.DateField()
    poster = models.ImageField(upload_to='posters/', null=True, blank=True)
    movie_link = models.URLField(max_length=200, null=True, blank=True)
    
    def poster_preview(self):
        if self.poster:
            return format_html('<img src="{}" style="height: 50px;"/>', self.poster.url)
        return "-"
    poster_preview.short_description = 'Poster Preview'
    poster_preview.allow_tags = True

    def __str__(self):
        return self.title


class UserInteraction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    watched = models.BooleanField(default=False)  # 1 or 0
    watch_date = models.DateTimeField(auto_now_add=True)
    rating = models.IntegerField(null=True, blank=True)  # Rating from 1-5
    review = models.TextField(blank=True, null=True)  # String review
    last_updated = models.DateTimeField(auto_now=True)  # Track when the interaction was last updated

    class Meta:
        unique_together = ('user', 'movie')  # One interaction per user per movie
        ordering = ['-watch_date']  # Most recent first

    def __str__(self):
        return f"{self.user.username} - {self.movie.title}"

    def get_rating_display(self):
        """Returns a string representation of the rating with stars"""
        if self.rating:
            return "⭐" * self.rating
        return "No rating"

    def get_watch_status(self):
        """Returns a string representation of watch status"""
        return "Watched" if self.watched else "Not Watched"

    @property
    def has_review(self):
        """Returns True if the user has written a review"""
        return bool(self.review and self.review.strip())


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_pic = models.ImageField(upload_to='profile_pics/', null=True, blank=True, default='default3.png')
    birthday = models.DateField(null=True, blank=True)
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True)
    mobile_no = models.CharField(max_length=15, blank=True)
    
    def __str__(self):
        return self.user.username
    

def get_trending_movies(user=None, num=10):
    watched_movie_ids = []
    if user is not None:
        watched_movie_ids = UserInteraction.objects.filter(
            user=user
        ).values_list('movie_id', flat=True).distinct()
    trending = Movie.objects.annotate(
        avg_rating=Avg('userinteraction__rating')
    ).exclude(id__in=watched_movie_ids).order_by('-avg_rating', '-id')[:num]
    return trending
    
