import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from coordinator.llm_grounding import GroundedLLMReasoningEngine

class TestStrictAIModeRouting(unittest.TestCase):
    def setUp(self):
        self.engine = GroundedLLMReasoningEngine()
        # Set dummy keys
        self.engine.gemini_key = "dummy_gemini_key_123"
        self.engine.groq_key = "dummy_groq_key_456"

    @patch("urllib.request.urlopen")
    def test_local_mode_bypasses_cloud_keys(self, mock_urlopen):
        """Verify that when ai_mode='local', no cloud API calls are made even if keys are set."""
        # Mock local Ollama response
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"response": "Local Ollama Answer"}'
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        ans = self.engine._call_llm_backend(
            question="How to fix bottle contamination?",
            evidence_text="Record #1",
            has_strong_match=True,
            ai_mode="local",
            cloud_api_key="dummy_user_key"
        )

        self.assertEqual(ans, "Local Ollama Answer")
        # Verify urlopen was called for localhost:11434, NOT googleapis.com or groq.com
        called_urls = [call.args[0].full_url for call in mock_urlopen.call_args_list if hasattr(call.args[0], 'full_url')]
        for url in called_urls:
            self.assertIn("localhost:11434", url)
            self.assertNotIn("googleapis.com", url)
            self.assertNotIn("groq.com", url)
        print("[TEST PASSED] ai_mode='local' strictly bypassed all cloud API calls!")

    @patch("urllib.request.urlopen")
    def test_cloud_mode_uses_cloud_key(self, mock_urlopen):
        """Verify that when ai_mode='cloud', it routes to the Cloud API."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"candidates": [{"content": {"parts": [{"text": "Cloud Gemini Answer"}]}}]}'
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        ans = self.engine._call_llm_backend(
            question="How to fix bottle contamination?",
            evidence_text="Record #1",
            has_strong_match=True,
            ai_mode="cloud",
            cloud_api_key="dummy_user_key"
        )

        self.assertEqual(ans, "Cloud Gemini Answer")
        called_url = mock_urlopen.call_args_list[0].args[0].full_url
        self.assertIn("generativelanguage.googleapis.com", called_url)
        self.assertIn("key=dummy_user_key", called_url)
        print("[TEST PASSED] ai_mode='cloud' correctly used cloud API key!")

if __name__ == "__main__":
    unittest.main()
