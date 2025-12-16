

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.decomposition import TruncatedSVD
from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime, timedelta
import pickle
import os

from .cache import cache_get, cache_set, get_cache_key

logger = logging.getLogger(__name__)


class HybridRecommendationEngine:
    """Hybrid recommendation engine combining CBF and CF approaches"""

    def __init__(self, cache_expiry: int = 3600):
        self.cache_expiry = cache_expiry
        self.tfidf_vectorizer = None
        self.scaler = StandardScaler()
        self.encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
        self.svd = TruncatedSVD(n_components=20, random_state=42)

        # Model storage paths
        self.models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
        os.makedirs(self.models_dir, exist_ok=True)

        # Initialize components
        self.user_factors = None
        self.item_factors = None
        self.content_similarity_matrix = None
        self.resource_features = None

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for TF-IDF vectorization"""
        if not text:
            return ""
        # Basic preprocessing - in production, use more sophisticated NLP
        return text.lower().strip()

    def _create_resource_features(self, resources_df: pd.DataFrame) -> np.ndarray:
        try:
            # --- Text features ---
            text_features = []
            for _, row in resources_df.iterrows():
                combined_text = f"{row.get('title', '')} {row.get('description', '')} {' '.join(row.get('tags', []))}"
                text_features.append(self._preprocess_text(combined_text))

            if not self.tfidf_vectorizer:
                self.tfidf_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
                text_vectors = self.tfidf_vectorizer.fit_transform(text_features)
            else:
                text_vectors = self.tfidf_vectorizer.transform(text_features)

            # --- Categorical features ---
            categorical_cols = ['difficulty', 'media_type', 'learning_style']
            categorical_data = resources_df[categorical_cols].fillna('unknown')
            categorical_vectors = self.encoder.fit_transform(categorical_data)

            # --- Numerical features ---
            numerical_cols = ['duration_minutes', 'rating', 'rating_count']
            numerical_data = resources_df[numerical_cols].fillna(0)
            numerical_vectors = self.scaler.fit_transform(numerical_data)

            # --- Combine all features ---
            combined_features = np.hstack([
                text_vectors.toarray(),
                categorical_vectors,
                numerical_vectors
            ])

            # --- Clean invalid values ---
            if not np.isfinite(combined_features).all():
                logger.warning("Non-finite values detected in feature matrix — replacing with zeros")
                combined_features = np.nan_to_num(combined_features, nan=0.0, posinf=0.0, neginf=0.0)

            # --- Guard against degenerate matrices ---
            if combined_features.shape[0] == 0 or combined_features.shape[1] == 0:
                logger.warning("Empty feature matrix — returning zeros")
                return np.zeros((len(resources_df), 20))

            # --- Dimensionality reduction (safe SVD) ---
            n_components = min(20, combined_features.shape[1] - 1)
            self.svd = TruncatedSVD(n_components=n_components, random_state=42)
            reduced_features = self.svd.fit_transform(combined_features)

            # Handle NaNs after SVD
            reduced_features = np.nan_to_num(reduced_features)

            return reduced_features

        except Exception as e:
            logger.error(f"Error creating resource features: {e}")
            return np.zeros((len(resources_df), 20))


    def _create_user_profile(self, user_data: Dict, user_interactions: List[Dict]) -> np.ndarray:
        """Create user profile vector based on preferences and interaction history"""
        try:
            profile_vector = np.zeros(20)  # Match SVD components

            # User preferences contribution
            if user_data.get('preferred_difficulty'):
                # Simple preference encoding - in production, use learned embeddings
                pref_idx = hash(user_data['preferred_difficulty']) % 100
                profile_vector[pref_idx] += 0.3

            if user_data.get('preferred_learning_style'):
                pref_idx = hash(user_data['preferred_learning_style']) % 100
                profile_vector[pref_idx] += 0.3

            # Interaction history contribution (weighted by recency)
            now = datetime.utcnow()
            for interaction in user_interactions[-50:]:  # Last 50 interactions
                interaction_time = interaction.get('created_at', now)
                if isinstance(interaction_time, str):
                    interaction_time = datetime.fromisoformat(interaction_time.replace('Z', '+00:00'))

                # Recency weight (newer interactions have higher weight)
                days_old = (now - interaction_time).days
                recency_weight = max(0.1, 1.0 / (1.0 + days_old / 30.0))  # Decay over 30 days

                # Different interaction types have different weights
                interaction_type = interaction.get('interaction_type', 'view')
                type_weight = {
                    'complete': 1.0,
                    'rate': 0.8,
                    'save': 0.6,
                    'like': 0.4,
                    'view': 0.2
                }.get(interaction_type, 0.1)

                # Add resource features to user profile
                resource_id = interaction.get('resource_id')
                if resource_id and resource_id < len(self.resource_features):
                    profile_vector += self.resource_features[resource_id] * recency_weight * type_weight

            # Normalize
            if np.linalg.norm(profile_vector) > 0:
                profile_vector = profile_vector / np.linalg.norm(profile_vector)

            return profile_vector

        except Exception as e:
            logger.error(f"Error creating user profile: {e}")
            return np.zeros(100)

    def _content_based_scoring(self, user_profile: np.ndarray, candidate_resources: List[int]) -> Dict[int, float]:
        """Calculate content-based similarity scores"""
        scores = {}

        try:
            for resource_id in candidate_resources:
                if resource_id < len(self.resource_features):
                    resource_vector = self.resource_features[resource_id]
                    # Ensure both vectors have same dimensionality
                    if len(user_profile) == len(resource_vector):
                        similarity = cosine_similarity(
                            user_profile.reshape(1, -1),
                            resource_vector.reshape(1, -1)
                        )[0][0]
                        scores[resource_id] = float(similarity)
                    else:
                        # Fallback: use basic similarity based on available data
                        scores[resource_id] = 0.1
                else:
                    scores[resource_id] = 0.0

        except Exception as e:
            logger.error(f"Error in content-based scoring: {e}")

        return scores

    def _collaborative_filtering_scoring(self, user_id: int, candidate_resources: List[int],
                                       user_interactions: List[Dict]) -> Dict[int, float]:
        """Calculate collaborative filtering scores using simple popularity-based approach"""
        scores = {}

        try:
            # Simple CF: boost resources that similar users have interacted with
            # In production, this would use trained MF/NCF models

            # Get user's interaction history
            user_liked_resources = set()
            user_completed_resources = set()

            for interaction in user_interactions:
                if interaction.get('interaction_type') in ['rate', 'like', 'save']:
                    user_liked_resources.add(interaction['resource_id'])
                elif interaction.get('interaction_type') == 'complete':
                    user_completed_resources.add(interaction['resource_id'])

            # Simple scoring based on user's preferences and global popularity
            # This is a placeholder - real CF would use trained models
            for resource_id in candidate_resources:
                base_score = 0.1  # Base popularity score

                # Boost based on user's learning style preferences
                # This would be more sophisticated in production

                scores[resource_id] = base_score

        except Exception as e:
            logger.error(f"Error in collaborative filtering scoring: {e}")

        return scores

    def get_recommendations(self, user_id: int, user_data: Dict, user_interactions: List[Dict],
                          resources_df: pd.DataFrame, limit: int = 10) -> List[Dict]:
        """Get hybrid recommendations for a user"""
        try:
            cache_key = get_cache_key("recommendations", user_id, limit)

            # Check cache first
            cached_result = cache_get(cache_key)
            if cached_result:
                return cached_result

            # Create resource features if not done
            if self.resource_features is None:
                self.resource_features = self._create_resource_features(resources_df)

            # Create user profile
            user_profile = self._create_user_profile(user_data, user_interactions)

            # Get candidate resources (exclude already interacted ones)
            interacted_resource_ids = set()
            for interaction in user_interactions:
                interacted_resource_ids.add(interaction['resource_id'])

            candidate_resources = [
                i for i in range(len(resources_df))
                if i not in interacted_resource_ids
            ]

            # Calculate scores
            cbf_scores = self._content_based_scoring(user_profile, candidate_resources)
            cf_scores = self._collaborative_filtering_scoring(user_id, candidate_resources, user_interactions)

            # Hybrid scoring
            hybrid_scores = {}
            for resource_id in candidate_resources:
                cbf_score = cbf_scores.get(resource_id, 0.0)
                cf_score = cf_scores.get(resource_id, 0.0)

                # Weight combination based on user history length
                if len(user_interactions) < 5:
                    # Cold start: rely more on content-based
                    hybrid_score = 0.8 * cbf_score + 0.2 * cf_score
                else:
                    # Established user: balance both approaches
                    hybrid_score = 0.4 * cbf_score + 0.6 * cf_score

                hybrid_scores[resource_id] = hybrid_score

            # Rank and select top recommendations
            sorted_resources = sorted(
                hybrid_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:limit]

            # Format results
            recommendations = []
            for resource_id, score in sorted_resources:
                if resource_id < len(resources_df):
                    resource_data = resources_df.iloc[resource_id].to_dict()
                    resource_data['recommendation_score'] = score
                    resource_data['recommendation_reason'] = self._get_recommendation_reason(
                        cbf_scores.get(resource_id, 0),
                        cf_scores.get(resource_id, 0)
                    )
                    recommendations.append(resource_data)

            # Cache results
            cache_set(cache_key, recommendations, self.cache_expiry)

            return recommendations

        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            # Fallback: return popular resources
            return self._get_popular_resources(resources_df, limit)

    def _get_recommendation_reason(self, cbf_score: float, cf_score: float) -> str:
        """Generate human-readable recommendation reason"""
        if cbf_score > cf_score:
            return "Based on your learning preferences and content similarity"
        elif cf_score > cbf_score:
            return "Popular among users with similar interests"
        else:
            return "Recommended based on your profile and community preferences"

    def _get_popular_resources(self, resources_df: pd.DataFrame, limit: int) -> List[Dict]:
        """Fallback: return most popular resources"""
        try:
            # Sort by rating and rating count
            popular = resources_df.sort_values(
                ['rating', 'rating_count'],
                ascending=[False, False]
            ).head(limit)

            recommendations = []
            for _, row in popular.iterrows():
                resource_data = row.to_dict()
                resource_data['recommendation_score'] = row['rating'] / 5.0  # Normalize to 0-1
                resource_data['recommendation_reason'] = "Popular resource"
                recommendations.append(resource_data)

            return recommendations

        except Exception as e:
            logger.error(f"Error getting popular resources: {e}")
            return []

    def train_models(self, interactions_df: pd.DataFrame, resources_df: pd.DataFrame):
        """Train the recommendation models (offline process)"""
        try:
            logger.info("Starting model training...")

            # Create resource features
            self.resource_features = self._create_resource_features(resources_df)

            # In production, this would train actual ML models
            # For now, just store the feature matrix
            self._save_models()

            logger.info("Model training completed")

        except Exception as e:
            logger.error(f"Error training models: {e}")

    def _save_models(self):
        """Save trained models to disk"""
        try:
            model_data = {
                'tfidf_vectorizer': self.tfidf_vectorizer,
                'scaler': self.scaler,
                'encoder': self.encoder,
                'svd': self.svd,
                'resource_features': self.resource_features
            }

            model_path = os.path.join(self.models_dir, 'recommendation_models.pkl')
            with open(model_path, 'wb') as f:
                pickle.dump(model_data, f)

        except Exception as e:
            logger.error(f"Error saving models: {e}")

    def _load_models(self):
        """Load trained models from disk"""
        try:
            model_path = os.path.join(self.models_dir, 'recommendation_models.pkl')
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    model_data = pickle.load(f)

                self.tfidf_vectorizer = model_data.get('tfidf_vectorizer')
                self.scaler = model_data.get('scaler')
                self.encoder = model_data.get('encoder')
                self.svd = model_data.get('svd')
                self.resource_features = model_data.get('resource_features')

        except Exception as e:
            logger.error(f"Error loading models: {e}")


# Global recommendation engine instance
recommendation_engine = HybridRecommendationEngine()