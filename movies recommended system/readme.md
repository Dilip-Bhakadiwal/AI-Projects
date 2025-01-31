# Movie Recommendation System

## Overview
This project is a Movie Recommendation System that suggests movies based on their similarity to a given movie. The system uses content-based filtering to recommend movies by analyzing various features such as genres, keywords, cast, crew, and overview. The project is implemented using Python and leverages libraries like Pandas, NLTK, and Scikit-learn.

## Features
- **Content-Based Filtering**: Recommends movies based on the similarity of their content.
- **Data Preprocessing**: Cleans and processes movie data to extract relevant features.
- **Cosine Similarity**: Uses cosine similarity to measure the similarity between movies.
- **Stemming**: Applies stemming to reduce words to their root form for better matching.

## Dataset
The dataset used in this project is the **TMDB 5000 Movie Dataset**, which contains information about 5000 movies, including:

- **Movies Metadata**: Budget, genres, keywords, overview, tagline, etc.
- **Credits**: Cast and crew information.

## Libraries Used
- **Pandas**: For data manipulation and analysis.
- **NLTK**: For natural language processing tasks like stemming.
- **Scikit-learn**: For feature extraction (`CountVectorizer`) and similarity computation (`cosine_similarity`).

## How It Works
1. **Data Loading**: The dataset is loaded and merged based on movie titles.
2. **Data Preprocessing**:
   - Extracts and processes genres, keywords, cast, and crew.
   - Combines these features into a single `'tags'` column.
   - Applies stemming to the tags for better matching.
3. **Feature Extraction**:
   - Uses `CountVectorizer` to convert the tags into a matrix of token counts.
4. **Similarity Computation**:
   - Computes cosine similarity between movies based on their tags.
5. **Recommendation**:
   - Given a movie, the system recommends the top 7 most similar movies.
