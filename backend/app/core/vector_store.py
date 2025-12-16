"""
Vector database for content indexing and semantic search.
Uses FAISS for efficient similarity search and vector indexing.
"""

import numpy as np
import pandas as pd
import faiss
import pickle
import os
import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

from .cache import cache_get, cache_set, get_cache_key

logger = logging.getLogger(__name__)


class VectorStore:
    """Vector database for content indexing and semantic search"""

    def __init__(self, dimension: int = 384, index_type: str = "IndexIVFFlat"):
        self.dimension = dimension
        self.index_type = index_type
        self.index = None
        self.vectors = None
        self.metadata = []
        self.id_mapping = {}  # Maps FAISS indices to resource IDs

        # Storage paths
        self.store_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
        os.makedirs(self.store_dir, exist_ok=True)

        # Initialize with a basic index
        self._initialize_index()

    def _initialize_index(self):
        """Initialize FAISS index"""
        try:
            if self.index_type == "IndexIVFFlat":
                # IVF with PQ for larger datasets
                quantizer = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine
                self.index = faiss.IndexIVFFlat(quantizer, self.dimension, 100, faiss.METRIC_INNER_PRODUCT)
            else:
                # Simple flat index for smaller datasets
                self.index = faiss.IndexFlatIP(self.dimension)

            logger.info(f"Initialized FAISS index: {self.index_type}")

        except Exception as e:
            logger.error(f"Failed to initialize FAISS index: {e}")
            # Fallback to simple flat index
            self.index = faiss.IndexFlatIP(self.dimension)

    def _preprocess_text(self, text: str) -> str:
        """Basic text preprocessing for embeddings"""
        if not text:
            return ""
        # In production, this would use more sophisticated NLP preprocessing
        return text.lower().strip()

    def _create_text_embedding(self, text: str) -> np.ndarray:
        """Create text embedding (placeholder - would use actual embedding model)"""
        # This is a placeholder. In production, you would use:
        # - sentence-transformers for semantic embeddings
        # - OpenAI embeddings
        # - BERT-based models
        # - Custom transformer models

        # Simple hash-based embedding for demonstration
        # In production, replace with actual embedding model
        import hashlib

        # Create a deterministic embedding based on text content
        hash_obj = hashlib.md5(text.encode('utf-8'))
        hash_bytes = hash_obj.digest()

        # Convert hash to float array and normalize
        embedding = np.array([b / 255.0 for b in hash_bytes], dtype=np.float32)

        # Pad or truncate to required dimension
        if len(embedding) < self.dimension:
            embedding = np.pad(embedding, (0, self.dimension - len(embedding)))
        else:
            embedding = embedding[:self.dimension]

        # L2 normalize for cosine similarity
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def _create_resource_vector(self, resource_data: Dict[str, Any]) -> np.ndarray:
        """Create feature vector for a resource"""
        try:
            # Text-based features
            text_features = []
            title = self._preprocess_text(resource_data.get('title', ''))
            description = self._preprocess_text(resource_data.get('description', ''))

            # Combine title and description
            combined_text = f"{title} {description}"

            # Add tags if available
            tags = resource_data.get('tags', [])
            if tags:
                combined_text += f" {' '.join(tags)}"

            text_embedding = self._create_text_embedding(combined_text)

            # Categorical features (one-hot encoded conceptually)
            media_type = resource_data.get('media_type', '')
            difficulty = resource_data.get('difficulty', '')
            learning_style = resource_data.get('learning_style', '')

            # Create categorical embeddings
            cat_embedding = self._create_text_embedding(f"{media_type} {difficulty} {learning_style}")

            # Numerical features
            duration = resource_data.get('duration_minutes', 0) / 1000.0  # Normalize
            rating = resource_data.get('rating', 0) / 5.0  # Normalize to 0-1
            rating_count = min(resource_data.get('rating_count', 0) / 1000.0, 1.0)  # Cap at 1.0

            # Combine all features
            numerical_features = np.array([duration, rating, rating_count], dtype=np.float32)

            # Concatenate all feature vectors
            combined_vector = np.concatenate([
                text_embedding,
                cat_embedding,
                numerical_features
            ])

            # Ensure correct dimension (truncate or pad if necessary)
            if len(combined_vector) > self.dimension:
                combined_vector = combined_vector[:self.dimension]
            elif len(combined_vector) < self.dimension:
                combined_vector = np.pad(combined_vector, (0, self.dimension - len(combined_vector)))

            # L2 normalize
            norm = np.linalg.norm(combined_vector)
            if norm > 0:
                combined_vector = combined_vector / norm

            return combined_vector.astype(np.float32)

        except Exception as e:
            logger.error(f"Error creating resource vector: {e}")
            # Return zero vector as fallback
            return np.zeros(self.dimension, dtype=np.float32)

    def add_resources(self, resources_df: pd.DataFrame):
        """Add resources to the vector store"""
        try:
            vectors = []
            metadata = []

            for _, row in resources_df.iterrows():
                resource_data = row.to_dict()
                vector = self._create_resource_vector(resource_data)

                vectors.append(vector)
                metadata.append(resource_data)

                # Update ID mapping
                self.id_mapping[len(metadata) - 1] = resource_data.get('id')

            # Convert to numpy array
            vectors_array = np.array(vectors, dtype=np.float32)

            # Store vectors for later use
            self.vectors = vectors_array
            self.metadata = metadata

            # Add to FAISS index
            if len(vectors_array) > 0:
                # Train the index if it's IVF
                if hasattr(self.index, 'is_trained') and not self.index.is_trained:
                    if len(vectors_array) >= 256:  # Minimum training size
                        self.index.train(vectors_array)

                # Add vectors to index
                self.index.add(vectors_array)

                logger.info(f"Added {len(vectors)} resources to vector store")

                # Save the index
                self._save_index()

        except Exception as e:
            logger.error(f"Error adding resources to vector store: {e}")

    def search_similar(self, query_text: str, top_k: int = 10,
                      filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar resources using semantic similarity"""
        try:
            # Create query vector
            query_vector = self._create_text_embedding(self._preprocess_text(query_text))
            query_vector = query_vector.reshape(1, -1).astype(np.float32)

            # Search the index
            if self.index.ntotal == 0:
                return []

            scores, indices = self.index.search(query_vector, min(top_k, self.index.ntotal))

            # Format results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx != -1 and idx < len(self.metadata):  # Valid index
                    resource_data = self.metadata[idx].copy()
                    resource_data['similarity_score'] = float(score)
                    resource_data['search_rank'] = len(results) + 1

                    # Apply filters if provided
                    if self._matches_filters(resource_data, filters):
                        results.append(resource_data)

            return results[:top_k]

        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []

    def _matches_filters(self, resource_data: Dict[str, Any],
                        filters: Optional[Dict[str, Any]]) -> bool:
        """Check if resource matches the provided filters"""
        if not filters:
            return True

        try:
            # Media type filter
            if 'media_type' in filters and filters['media_type']:
                if resource_data.get('media_type') != filters['media_type']:
                    return False

            # Difficulty filter
            if 'difficulty' in filters and filters['difficulty']:
                if resource_data.get('difficulty') != filters['difficulty']:
                    return False

            # Learning style filter
            if 'learning_style' in filters and filters['learning_style']:
                if resource_data.get('learning_style') != filters['learning_style']:
                    return False

            # Duration filters
            duration = resource_data.get('duration_minutes', 0)
            if 'min_duration' in filters and duration < filters['min_duration']:
                return False
            if 'max_duration' in filters and duration > filters['max_duration']:
                return False

            # Rating filter
            if 'min_rating' in filters and resource_data.get('rating', 0) < filters['min_rating']:
                return False

            # Tags filter (overlap)
            if 'tags' in filters and filters['tags']:
                resource_tags = set(resource_data.get('tags', []))
                filter_tags = set(filters['tags'])
                if not resource_tags.intersection(filter_tags):
                    return False

            return True

        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            return False

    def update_resource(self, resource_id: int, resource_data: Dict[str, Any]):
        """Update a resource in the vector store"""
        # In production, this would require rebuilding parts of the index
        # For now, we'll mark it as needing a full rebuild
        logger.info(f"Resource {resource_id} marked for update - full rebuild needed")

    def delete_resource(self, resource_id: int):
        """Delete a resource from the vector store"""
        # In production, this would require index maintenance
        # For now, we'll mark it as needing a full rebuild
        logger.info(f"Resource {resource_id} marked for deletion - full rebuild needed")

    def rebuild_index(self, resources_df: pd.DataFrame):
        """Rebuild the entire vector index"""
        try:
            logger.info("Rebuilding vector index...")

            # Reset the index
            self._initialize_index()
            self.metadata = []
            self.id_mapping = {}

            # Re-add all resources
            self.add_resources(resources_df)

            logger.info("Vector index rebuilt successfully")

        except Exception as e:
            logger.error(f"Error rebuilding vector index: {e}")

    def _save_index(self):
        """Save the FAISS index and metadata to disk"""
        try:
            index_path = os.path.join(self.store_dir, 'faiss_index.pkl')

            # Prepare data for saving
            save_data = {
                'index': faiss.serialize_index(self.index),
                'metadata': self.metadata,
                'id_mapping': self.id_mapping,
                'dimension': self.dimension,
                'index_type': self.index_type
            }

            with open(index_path, 'wb') as f:
                pickle.dump(save_data, f)

            logger.info(f"Vector store saved to {index_path}")

        except Exception as e:
            logger.error(f"Error saving vector store: {e}")

    def _load_index(self):
        """Load the FAISS index and metadata from disk"""
        try:
            index_path = os.path.join(self.store_dir, 'faiss_index.pkl')

            if os.path.exists(index_path):
                with open(index_path, 'rb') as f:
                    save_data = pickle.load(f)

                # Restore the index
                self.index = faiss.deserialize_index(save_data['index'])
                self.metadata = save_data['metadata']
                self.id_mapping = save_data['id_mapping']
                self.dimension = save_data['dimension']
                self.index_type = save_data['index_type']

                logger.info(f"Vector store loaded from {index_path}")

        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            # Initialize empty index
            self._initialize_index()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        return {
            'total_vectors': self.index.ntotal if self.index else 0,
            'dimension': self.dimension,
            'index_type': self.index_type,
            'metadata_count': len(self.metadata),
            'last_updated': datetime.utcnow().isoformat()
        }


# Global vector store instance
vector_store = VectorStore()