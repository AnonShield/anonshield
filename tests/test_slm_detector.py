
import unittest
from unittest.mock import MagicMock, patch
from src.anon.slm.detectors.slm_detector import SLMEntityDetector, DetectedEntity
from src.anon.slm.prompts import PromptManager, PromptTemplate

class TestSLMDetector(unittest.TestCase):

    def setUp(self):
        """Set up a new SLMEntityDetector instance before each test."""
        self.mock_slm_client = MagicMock()
        self.mock_prompt_manager = MagicMock()

        # Configure the prompt manager to return a usable template
        mock_template = PromptTemplate("System Prompt", "User Prompt: {text}")
        self.mock_prompt_manager.get.return_value = mock_template

        self.detector = SLMEntityDetector(
            slm_client=self.mock_slm_client,
            prompt_manager=self.mock_prompt_manager,
            entities_to_preserve=set(),
            allow_list=set(),
            confidence_threshold=0.7,
            use_cache=True,
            prompt_version="v1"
        )

    def test_detect_entities_success(self):
        """Test successful detection of entities from a valid SLM response."""
        sample_text = "John Doe works at Contoso Corp."
        mock_response = {
            "entities": [
                {"text": "John Doe", "type": "PERSON", "confidence": 0.9},
                {"text": "Contoso Corp", "type": "ORGANIZATION", "confidence": 0.8}
            ]
        }
        self.mock_slm_client.query_json.return_value = mock_response

        results = self.detector.detect_entities([sample_text], language="en")

        self.mock_prompt_manager.get.assert_called_once_with("entity_detector", version="v1", language="en")
        self.mock_slm_client.query_json.assert_called_once()
        self.assertEqual(len(results), 1)
        
        labels = results[0]["label"]
        self.assertEqual(len(labels), 2)
        self.assertEqual(labels[0], [0, 8, "PERSON"])  # "John Doe"
        self.assertEqual(labels[1], [18, 30, "ORGANIZATION"])  # "Contoso Corp"

    def test_detect_entities_api_error(self):
        """Test that the detector handles an API error gracefully."""
        sample_text = "Some text that causes an error."
        self.mock_slm_client.query_json.return_value = {"error": "Internal Server Error"}
        
        # Disable fallback to isolate the error handling
        self.detector.fallback_to_regex = False

        results = self.detector.detect_entities([sample_text])

        self.assertEqual(results, [])
        self.mock_slm_client.query_json.assert_called_once()

    def test_parsing_hallucinated_entity(self):
        """Test that the detector filters out entities not present in the original text."""
        sample_text = "This is a simple sentence."
        mock_response = {
            "entities": [
                # This entity is "hallucinated" by the SLM and doesn't exist in the text.
                {"text": "Non-existent Entity", "type": "MISC", "confidence": 0.9}
            ]
        }
        self.mock_slm_client.query_json.return_value = mock_response

        results = self.detector.detect_entities([sample_text])

        # The result should be empty as the only detected entity was invalid.
        self.assertEqual(results, [])

    def test_low_confidence_entity_filtered(self):
        """Test that entities below the confidence threshold are filtered out."""
        sample_text = "An entity with low confidence."
        mock_response = {
            "entities": [
                {"text": "low confidence", "type": "PHRASE", "confidence": 0.5} # Below threshold of 0.7
            ]
        }
        self.mock_slm_client.query_json.return_value = mock_response

        results = self.detector.detect_entities([sample_text])

        self.assertEqual(results, [])

    def test_merge_overlapping_entities(self):
        """Unit test for the _merge_overlapping_entities private method."""
        # Create entities where "John Doe" contains "John"
        entities = [
            DetectedEntity(text='John', entity_type='PERSON', start=0, end=4, score=0.8),
            DetectedEntity(text='John Doe', entity_type='PERSON', start=0, end=8, score=0.9),
            DetectedEntity(text='New York', entity_type='LOCATION', start=12, end=20, score=0.85)
        ]
        
        # The method expects entities sorted by start position, which they already are.
        merged = self.detector._merge_overlapping_entities(entities)

        self.assertEqual(len(merged), 2)
        # It should keep "John Doe" (higher score and longer) and discard "John".
        self.assertEqual(merged[0].text, "John Doe")
        self.assertEqual(merged[1].text, "New York")

    def test_caching_behavior(self):
        """Test if the cache is being used correctly."""
        sample_text = "This text will be cached."
        mock_response = {"entities": [{"text": "cached", "type": "VERB", "confidence": 0.9}]}
        self.mock_slm_client.query_json.return_value = mock_response

        # First call - should miss cache and call the client
        results1 = self.detector.detect_entities([sample_text])
        self.assertEqual(self.mock_slm_client.query_json.call_count, 1)
        self.assertGreater(len(results1), 0)

        # Second call - should hit cache and NOT call the client again
        results2 = self.detector.detect_entities([sample_text])
        self.assertEqual(self.mock_slm_client.query_json.call_count, 1, "Client should not be called on cache hit.")
        self.assertEqual(results1, results2)

        # Clear cache and call again - should call the client again
        self.detector.clear_cache()
        results3 = self.detector.detect_entities([sample_text])
        self.assertEqual(self.mock_slm_client.query_json.call_count, 2, "Client should be called after cache clear.")
        self.assertEqual(results1, results3)

if __name__ == "__main__":
    unittest.main()
