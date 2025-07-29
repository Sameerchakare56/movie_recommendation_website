import tensorflow as tf
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from django.contrib.auth.models import User
from watch.models import Movie, UserInteraction
from django.db.models import Count, Avg, F, Q, OuterRef, Subquery, Exists

# 1. Load data from Django ORM
data = pd.DataFrame(list(
    UserInteraction.objects.values('user_id', 'movie_id', 'rating')
))

# Load genres for each movie
movie_genres = pd.DataFrame(list(
    Movie.objects.values('id', 'genres')
))

# 2. Map user and movie IDs to indices
user_ids = data['user_id'].unique()
movie_ids = data['movie_id'].unique()
user_lookup = {user: idx for idx, user in enumerate(user_ids)}
movie_lookup = {movie: idx for idx, movie in enumerate(movie_ids)}

# Map genres to indices
all_genres = set()
for genres in movie_genres['genres']:
    if genres:  # Check if genres is not None
        all_genres.update(genres)
genre_lookup = {genre: idx for idx, genre in enumerate(all_genres)}

data['user_id'] = data['user_id'].map(user_lookup)
data['movie_id'] = data['movie_id'].map(movie_lookup)

# Create a dictionary of movie genres for faster lookup
movie_genres_dict = dict(zip(movie_genres['id'], movie_genres['genres']))

# Map movie genres to indices safely
def get_genre_indices(movie_id):
    genres = movie_genres_dict.get(movie_id, [])
    return [genre_lookup[genre] for genre in genres if genre in genre_lookup]

data['genre_idx'] = data['movie_id'].apply(get_genre_indices)

# 3. Prepare input data
user_input = data['user_id'].values
movie_input = data['movie_id'].values
genre_input = data['genre_idx'].values
ratings = data['rating'].values

# Example input features
X = data[['user_id', 'movie_id']].values
y = data['rating'].values

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

class NCF(tf.keras.Model):
    def __init__(self, num_users, num_movies, num_genres, embedding_dim):
        super(NCF, self).__init__()
        
        # Embedding layers for users and movies
        self.user_embedding = tf.keras.layers.Embedding(num_users, embedding_dim)
        self.movie_embedding = tf.keras.layers.Embedding(num_movies, embedding_dim)
        
        # MLP layers for interaction
        self.mlp_layer_1 = tf.keras.layers.Dense(128, activation='relu')
        self.mlp_layer_2 = tf.keras.layers.Dense(64, activation='relu')
        self.output_layer = tf.keras.layers.Dense(1)
        
    def call(self, inputs):
        user_input, movie_input = inputs
        user_embedding = self.user_embedding(user_input)
        movie_embedding = self.movie_embedding(movie_input)
        
        # Combine user and movie embeddings
        x = tf.concat([user_embedding, movie_embedding], axis=1)
        
        # Pass through MLP layers
        x = self.mlp_layer_1(x)
        x = self.mlp_layer_2(x)
        
        # Output the predicted rating
        return self.output_layer(x)

# Set the number of users, movies, and embedding dimension
embedding_dim = 8
num_users = len(user_ids)
num_movies = len(movie_ids)

# Instantiate the model
model = NCF(num_users, num_movies, len(all_genres), embedding_dim)

# Compile and Train the Model
model.compile(optimizer='adam', loss='mean_squared_error')

# Convert inputs to tensors
user_input_train_tensor = tf.convert_to_tensor(X_train[:, 0], dtype=tf.int32)
movie_input_train_tensor = tf.convert_to_tensor(X_train[:, 1], dtype=tf.int32)
ratings_train_tensor = tf.convert_to_tensor(y_train, dtype=tf.float32)

# Train the model
model.fit([user_input_train_tensor, movie_input_train_tensor], ratings_train_tensor, epochs=10)

# Evaluate the model
user_input_test_tensor = tf.convert_to_tensor(X_test[:, 0], dtype=tf.int32)
movie_input_test_tensor = tf.convert_to_tensor(X_test[:, 1], dtype=tf.int32)
ratings_test_tensor = tf.convert_to_tensor(y_test, dtype=tf.float32)

loss = model.evaluate([user_input_test_tensor, movie_input_test_tensor], ratings_test_tensor)
print(f"Test Loss: {loss}")

def get_unwatched_movies(user):
    watched_interactions = UserInteraction.objects.filter(
        user=user,
        movie=OuterRef('pk'),
        watched=True
    )
    return Movie.objects.annotate(
        has_watched=Exists(watched_interactions)
    ).filter(has_watched=False)

def get_recommended_movies(user, num=10):
    # Get user index from lookup
    user_idx = user_lookup.get(user.id)
    if user_idx is None:
        return get_trending_movies(user, num)  # Fallback to trending if user not in training data
    
    # Use robust unwatched movie filtering
    unwatched_movies = get_unwatched_movies(user)
    
    # Get the genres this user typically watches
    user_preferred_genres = Movie.objects.filter(
        userinteraction__user=user,
        userinteraction__rating__gte=4  # Movies they rated highly
    ).values_list('genres', flat=True)
    
    # Flatten the list of genres
    preferred_genres = []
    for genres in user_preferred_genres:
        if genres:
            preferred_genres.extend(genres)
    
    # Convert movie IDs to indices
    movie_indices = []
    valid_movies = []
    for movie in unwatched_movies:
        movie_idx = movie_lookup.get(movie.id)
        if movie_idx is not None:
            movie_indices.append(movie_idx)
            valid_movies.append(movie)
    
    if not valid_movies:
        return get_trending_movies(user, num)  # Fallback to trending if no valid movies
    
    # Create input tensors for prediction
    user_input = tf.convert_to_tensor([user_idx] * len(movie_indices), dtype=tf.int32)
    movie_input = tf.convert_to_tensor(movie_indices, dtype=tf.int32)
    
    # Get predictions from model
    predictions = model([user_input, movie_input])
    predicted_ratings = predictions.numpy().flatten()
    
    # Combine predictions with genre matching
    movie_scores = []
    for movie, pred_rating in zip(valid_movies, predicted_ratings):
        # Base score is the predicted rating
        score = float(pred_rating)
        
        # Boost score for movies matching user's preferred genres
        if movie.genres:
            matching_genres = set(movie.genres) & set(preferred_genres)
            genre_boost = len(matching_genres) * 0.2  # 0.2 boost per matching genre
            score += genre_boost
        
        movie_scores.append((movie, score))
    
    # Sort by final score
    movie_scores.sort(key=lambda x: x[1], reverse=True)
    return [movie for movie, _ in movie_scores[:num]]

def get_trending_movies(user=None, num=20):
    from django.db.models import Count, Avg, Q
    
    # Use robust unwatched movie filtering
    unwatched_movies = Movie.objects.all()
    if user is not None:
        unwatched_movies = get_unwatched_movies(user)
    
    # Annotate with popularity metrics
    trending_movies = unwatched_movies.annotate(
        watch_count=Count('userinteraction', filter=Q(userinteraction__watched=True)),
        avg_rating=Avg('userinteraction__rating')
    )
    
    # Convert to list to apply NCF predictions
    movies_list = list(trending_movies)
    
    if user is not None and user.id in user_lookup:
        user_idx = user_lookup[user.id]
        
        # Get user's preferred genres
        user_preferred_genres = Movie.objects.filter(
            userinteraction__user=user,
            userinteraction__rating__gte=4
        ).values_list('genres', flat=True)
        
        preferred_genres = []
        for genres in user_preferred_genres:
            if genres:
                preferred_genres.extend(genres)
        
        # Prepare data for NCF predictions
        movie_indices = []
        valid_movies = []
        
        for movie in movies_list:
            # Skip if movie has been watched by the user
            if user is not None and UserInteraction.objects.filter(user=user, movie=movie, watched=True).exists():
                continue
                
            movie_idx = movie_lookup.get(movie.id)
            if movie_idx is not None:
                movie_indices.append(movie_idx)
                valid_movies.append(movie)
        
        if valid_movies:
            # Create input tensors for prediction
            user_input = tf.convert_to_tensor([user_idx] * len(movie_indices), dtype=tf.int32)
            movie_input = tf.convert_to_tensor(movie_indices, dtype=tf.int32)
            
            # Get predictions from model
            predictions = model([user_input, movie_input])
            predicted_ratings = predictions.numpy().flatten()
            
            # Combine predictions with movies
            movie_scores = []
            for movie, pred_rating in zip(valid_movies, predicted_ratings):
                # Calculate combined score using watch count, avg rating, and predicted rating
                watch_count_norm = float(movie.watch_count) / trending_movies.aggregate(max_count=Count('userinteraction'))['max_count'] if movie.watch_count else 0
                avg_rating_norm = float(movie.avg_rating) / 5 if movie.avg_rating else 0
                pred_rating_norm = float(pred_rating) / 5
                
                # Genre matching boost
                genre_boost = 0
                if movie.genres:
                    matching_genres = set(movie.genres) & set(preferred_genres)
                    genre_boost = len(matching_genres) * 0.05  # Reduced genre boost to 0.05 per matching genre
                
                # Combined score (weighted average) - Adjusted weights
                combined_score = (
                    0.3 * watch_count_norm +  # Increased weight for watch count
                    0.3 * avg_rating_norm +   # Increased weight for average rating
                    0.3 * pred_rating_norm +  # Increased weight for predicted rating
                    0.1 * genre_boost         # Reduced weight for genre boost
                )
                
                movie_scores.append((movie, combined_score))
            
            # Sort by combined score
            movie_scores.sort(key=lambda x: x[1], reverse=True)
            return [movie for movie, _ in movie_scores[:num]]
    
    # Fallback to basic trending if user not in training data
    # Filter out watched movies for the user
    if user is not None:
        trending_movies = trending_movies.exclude(
            userinteraction__user=user,
            userinteraction__watched=True
        )
    
    # Get more movies than needed to ensure we have enough after filtering
    trending_movies = trending_movies.order_by('-watch_count', '-avg_rating', '-id')[:num*2]
    
    # If we still don't have enough movies, get some random unwatched movies
    if len(trending_movies) < num:
        remaining = num - len(trending_movies)
        additional_movies = Movie.objects.exclude(
            id__in=trending_movies.values_list('id', flat=True)
        )
        if user is not None:
            additional_movies = additional_movies.exclude(
                userinteraction__user=user,
                userinteraction__watched=True
            )
        additional_movies = additional_movies.order_by('?')[:remaining]
        trending_movies = list(trending_movies) + list(additional_movies)
    
    return trending_movies[:num]