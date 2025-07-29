from django.contrib import admin
from .models import Movie, UserInteraction


def get_recommended_movies(user, num=5):
    # Recommend movies the user hasn't rated yet
    rated_movie_ids = UserInteraction.objects.filter(user=user).values_list('movie_id', flat=True)
    return Movie.objects.exclude(id__in=rated_movie_ids)[:num]

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['title', 'genres', 'release_date', 'poster_preview']
    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(UserInteraction)
class UserInteractionAdmin(admin.ModelAdmin):
    list_display = ['user', 'movie', 'watched', 'rating', 'review', 'watch_date']
    list_filter = ['watched', 'rating', 'watch_date']
    search_fields = ['user__username', 'movie__title', 'review']

