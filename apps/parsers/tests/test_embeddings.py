"""
Unit tests for embedding generator.
"""

import unittest
from apps.parsers.embeddings import EmbeddingGenerator, generate_embedding


class TestEmbeddingGenerator(unittest.TestCase):
    """Test cases for EmbeddingGenerator class."""
    
    @classmethod
    def setUpClass(cls):
        """Initialize generator once for all tests."""
        cls.generator = EmbeddingGenerator()
    
    def test_embedding_dimensions(self):
        """Test that embeddings have correct dimensions (768)."""
        text = "artículo sobre derechos laborales"
        embedding = self.generator.generate(text)
        
        self.assertEqual(len(embedding), 768)
        self.assertIsInstance(embedding, list)
        self.assertTrue(all(isinstance(x, float) for x in embedding))
    
    def test_spanish_text_embedding(self):
        """Test embedding generation for Spanish legal text."""
        text = "El trabajador tiene derecho a indemnización por despido injustificado"
        embedding = self.generator.generate(text)
        
        self.assertEqual(len(embedding), 768)
        # Check that embedding is not all zeros
        self.assertGreater(sum(abs(x) for x in embedding), 0)
    
    def test_empty_text(self):
        """Test handling of empty text."""
        embedding = self.generator.generate("")
        
        # Should return zero vector for empty text
        self.assertEqual(len(embedding), 768)
        self.assertEqual(sum(embedding), 0.0)
    
    def test_long_text_truncation(self):
        """Test that long texts are truncated properly."""
        # Create text with 400 words (exceeds 300 word limit)
        long_text = " ".join(["palabra"] * 400)
        embedding = self.generator.generate(long_text)
        
        # Should still generate valid embedding
        self.assertEqual(len(embedding), 768)
        self.assertGreater(sum(abs(x) for x in embedding), 0)
    
    def test_batch_generation(self):
        """Test batch embedding generation."""
        texts = [
            "artículo 1 sobre contratos",
            "artículo 2 sobre garantías",
            "artículo 3 sobre sanciones"
        ]
        
        embeddings = self.generator.generate_batch(texts)
        
        self.assertEqual(len(embeddings), 3)
        for embedding in embeddings:
            self.assertEqual(len(embedding), 768)
            self.assertTrue(all(isinstance(x, float) for x in embedding))
    
    def test_embedding_similarity(self):
        """Test that similar texts have high cosine similarity."""
        text1 = "derechos del trabajador en caso de despido"
        text2 = "garantías laborales frente a terminación de contrato"
        text3 = "procedimiento de amparo constitucional"
        
        emb1 = self.generator.generate(text1)
        emb2 = self.generator.generate(text2)
        emb3 = self.generator.generate(text3)
        
        # Similar texts should have higher similarity
        sim_similar = self.generator.compute_similarity(emb1, emb2)
        sim_different = self.generator.compute_similarity(emb1, emb3)
        
        # Law texts about labor rights should be more similar to each other
        # than to a text about constitutional amparo
        self.assertGreater(sim_similar, sim_different)
        
        # Similarities should be in valid range [-1, 1]
        self.assertGreaterEqual(sim_similar, -1.0)
        self.assertLessEqual(sim_similar, 1.0)
        self.assertGreaterEqual(sim_different, -1.0)
        self.assertLessEqual(sim_different, 1.0)
    
    def test_identical_texts(self):
        """Test that  identical texts have similarity ~1.0."""
        text = "artículo 27 constitucional sobre propiedad"
        
        emb1 = self.generator.generate(text)
        emb2 = self.generator.generate(text)
        
        similarity = self.generator.compute_similarity(emb1, emb2)
        
        # Should be very close to 1.0 (allowing for floating point errors)
        self.assertAlmostEqual(similarity, 1.0, places=5)
    
    def test_convenience_function(self):
        """Test the convenience generate_embedding function."""
        text = "ley federal del trabajo"
        embedding = generate_embedding(text)
        
        self.assertEqual(len(embedding), 768)
        self.assertTrue(all(isinstance(x, float) for x in embedding))
    
    def test_model_loaded(self):
        """Test that model is properly loaded."""
        self.assertIsNotNone(self.generator.model)
        self.assertEqual(self.generator.dimensions, 768)


if __name__ == '__main__':
    unittest.main()
