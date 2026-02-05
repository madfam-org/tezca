"""
Embedding generator for semantic search using sentence-transformers.

Generates multilingual embeddings optimized for Spanish legal text.
"""

from sentence_transformers import SentenceTransformer
from typing import List, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generate embeddings for legal text using sentence-transformers.
    
    Uses paraphrase-multilingual-mpnet-base-v2 for excellent Spanish support.
    Generates 768-dimensional embeddings suitable for semantic search.
    """
    
    def __init__(self, model_name: str = 'paraphrase-multilingual-mpnet-base-v2'):
        """
        Initialize embedding generator with multilingual model.
        
        Args:
            model_name: Name of sentence-transformer model to use.
                       Default: paraphrase-multilingual-mpnet-base-v2 (768-dim)
        """
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dimensions = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Embedding dimensions: {self.dimensions}")
    
    def generate(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed (will be preprocessed)
            
        Returns:
            768-dimensional embedding vector as list of floats
            
        Example:
            >>> generator = EmbeddingGenerator()
            >>> embedding = generator.generate("artículo sobre derechos laborales")
            >>> len(embedding)
            768
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding generation")
            return [0.0] * self.dimensions
        
        # Preprocess text
        text = self._preprocess(text)
        
        # Generate embedding
        embedding = self.model.encode(text, convert_to_numpy=True)
        
        return embedding.tolist()
    
    def generate_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Uses batching for improved performance when processing many texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in each batch (default: 32)
            
        Returns:
            List of embedding vectors, one per input text
            
        Example:
            >>> generator = EmbeddingGenerator()
            >>> texts = ["artículo 1", "artículo 2", "artículo 3"]
            >>> embeddings = generator.generate_batch(texts)
            >>> len(embeddings)
            3
        """
        if not texts:
            logger.warning("Empty text list provided for batch embedding generation")
            return []
        
        # Preprocess all texts
        processed_texts = [self._preprocess(t) for t in texts]
        
        # Batch generation for efficiency
        logger.info(f"Generating embeddings for {len(texts)} texts (batch_size={batch_size})")
        embeddings = self.model.encode(
            processed_texts,
            convert_to_numpy=True,
            show_progress_bar=True,
            batch_size=batch_size
        )
        
        return [emb.tolist() for emb in embeddings]
    
    def _preprocess(self, text: str) -> str:
        """
        Preprocess text for embedding generation.
        
        - Strips whitespace
        - Truncates to model's max length (~300 words for safety)
        
        Args:
            text: Raw text
            
        Returns:
            Preprocessed text suitable for embedding
        """
        text = text.strip()
        
        # Truncate to max length (model limit is 384 tokens)
        # For mpnet, ~300 words is safe to stay under token limit
        words = text.split()
        if len(words) > 300:
            text = ' '.join(words[:300])
            logger.debug(f"Truncated text from {len(words)} to 300 words")
        
        return text
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between -1 and 1
            (1 = identical, 0 = orthogonal, -1 = opposite)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Cosine similarity = dot product / (norm1 * norm2)
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        
        return float(similarity)


def generate_embedding(text: str, model_name: str = 'paraphrase-multilingual-mpnet-base-v2') -> List[float]:
    """
    Convenience function to generate a single embedding.
    
    Creates a new EmbeddingGenerator instance for one-off usage.
    For batch processing, instantiate EmbeddingGenerator directly for better performance.
    
    Args:
        text: Text to embed
        model_name: Model to use (default: paraphrase-multilingual-mpnet-base-v2)
        
    Returns:
        Embedding vector as list of floats
    """
    generator = EmbeddingGenerator(model_name=model_name)
    return generator.generate(text)
