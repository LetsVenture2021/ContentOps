#!/usr/bin/env python3
"""
Test Suite for Content Draft Generation

Tests all aspects of the content generation pipeline including:
- Content opportunity fetching
- Source mention retrieval
- Draft generation for each platform
- Validation logic
- Notion updates
- Error handling
"""

import os
import json
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Mock environment variables before importing the module
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["NOTION_TOKEN"] = "test-token"

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

# Import the module to test
import generate_content_draft as gcd

# Load test fixtures
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
with open(os.path.join(FIXTURES_DIR, "sample_content_opportunities.json")) as f:
    TEST_DATA = json.load(f)


class TestContentOpportunityFetching(unittest.TestCase):
    """Test fetching content opportunities from Notion."""
    
    @patch('generate_content_draft.notion_query')
    def test_fetch_content_opportunities_success(self, mock_query):
        """Test successful fetching of content opportunities."""
        # Mock Notion API response
        mock_query.return_value = [{
            "id": "test-001",
            "properties": {
                "Topic": {"type": "title", "title": [{"plain_text": "Test Topic"}]},
                "Audience": {"type": "select", "select": {"name": "Operator"}},
                "Platform Target": {"type": "select", "select": {"name": "BiggerPockets"}},
                "Source Mentions": {"type": "relation", "relation": [{"id": "mention-001"}]},
                "Key Points": {"type": "rich_text", "rich_text": [{"plain_text": "- Point 1\n- Point 2"}]},
                "Proof Points": {"type": "rich_text", "rich_text": [{"plain_text": "- Proof 1"}]},
                "Priority": {"type": "number", "number": 2}
            }
        }]
        
        opportunities = gcd.fetch_content_opportunities()
        
        self.assertEqual(len(opportunities), 1)
        self.assertEqual(opportunities[0]["topic"], "Test Topic")
        self.assertEqual(opportunities[0]["audience"], "Operator")
        self.assertEqual(opportunities[0]["platform_target"], "BiggerPockets")
        self.assertEqual(len(opportunities[0]["key_points"]), 2)
    
    @patch('generate_content_draft.notion_query')
    def test_fetch_content_opportunities_empty(self, mock_query):
        """Test handling of no content opportunities."""
        mock_query.return_value = []
        
        opportunities = gcd.fetch_content_opportunities()
        
        self.assertEqual(len(opportunities), 0)
    
    @patch('generate_content_draft.notion_query')
    def test_fetch_content_opportunities_with_defaults(self, mock_query):
        """Test default values when properties are missing."""
        mock_query.return_value = [{
            "id": "test-002",
            "properties": {
                "Topic": {"type": "title", "title": []},
                "Audience": {"type": "select", "select": None},
                "Platform Target": {"type": "select", "select": None}
            }
        }]
        
        opportunities = gcd.fetch_content_opportunities()
        
        self.assertEqual(opportunities[0]["topic"], "Untitled")
        self.assertEqual(opportunities[0]["audience"], "Operator")
        self.assertEqual(opportunities[0]["platform_target"], "BiggerPockets")


class TestSourceMentionRetrieval(unittest.TestCase):
    """Test retrieval of source mentions."""
    
    @patch('generate_content_draft.notion_get_page')
    def test_retrieve_source_mentions_success(self, mock_get_page):
        """Test successful retrieval of source mentions."""
        mock_get_page.return_value = {
            "properties": {
                "Source Text": {"type": "rich_text", "rich_text": [{"plain_text": "Test mention text"}]},
                "Platform": {"type": "select", "select": {"name": "Reddit"}},
                "Author": {"type": "rich_text", "rich_text": [{"plain_text": "test_user"}]},
                "URL": {"type": "url", "url": "https://example.com"}
            }
        }
        
        mentions = gcd.retrieve_source_mentions(["mention-001"])
        
        self.assertEqual(len(mentions), 1)
        self.assertEqual(mentions[0]["source_text"], "Test mention text")
        self.assertEqual(mentions[0]["platform"], "Reddit")
        self.assertEqual(mentions[0]["author"], "test_user")
    
    @patch('generate_content_draft.notion_get_page')
    def test_retrieve_source_mentions_with_errors(self, mock_get_page):
        """Test handling of errors during retrieval."""
        # First call succeeds, second fails
        mock_get_page.side_effect = [
            {"properties": {"Source Text": {"type": "rich_text", "rich_text": [{"plain_text": "Text 1"}]}}},
            Exception("API Error")
        ]
        
        with patch('generate_content_draft.log'):
            mentions = gcd.retrieve_source_mentions(["mention-001", "mention-002"])
        
        # Should only return successful retrieval
        self.assertEqual(len(mentions), 1)
    
    def test_format_source_mentions(self):
        """Test formatting of source mentions for LLM prompt."""
        mentions = TEST_DATA["sample_mentions"][:2]
        
        formatted = gcd.format_source_mentions(mentions)
        
        self.assertIn("[MENTION 1]", formatted)
        self.assertIn("BiggerPockets", formatted)
        self.assertIn("investor_mike", formatted)
    
    def test_format_source_mentions_empty(self):
        """Test formatting with no mentions."""
        formatted = gcd.format_source_mentions([])
        
        self.assertEqual(formatted, "No source mentions available.")


class TestDraftGeneration(unittest.TestCase):
    """Test draft generation for different platforms."""
    
    def _create_mock_openai_response(self, platform_target: str) -> dict:
        """Create a mock OpenAI response matching the expected schema."""
        length_map = {
            "BiggerPockets": 2500,
            "LinkedIn": 1000,
            "X": 200,  # X validation counts tweets (via \n\n), but body still needs 100+ words for schema
            "Substack": 3000
        }
        
        body = " ".join(["word"] * length_map.get(platform_target, 1000))
        
        return {
            "headline": f"Test Headline for {platform_target}",
            "hook": "This is a compelling hook that grabs attention and establishes relevance for the reader.",
            "body": body,
            "key_points_formatted": [
                "Actionable takeaway 1",
                "Actionable takeaway 2",
                "Actionable takeaway 3"
            ],
            "proof_points_formatted": [
                "Data point or example 1",
                "Case study or stat 2"
            ],
            "cta": "Platform-appropriate call-to-action",
            "seo_metadata": {
                "title_tag": "SEO Optimized Title Tag Here",
                "meta_description": "This is a compelling meta description that summarizes the content in 150-160 characters for search engines.",
                "keywords": ["keyword1", "keyword2", "keyword3"],
                "suggested_tags": ["tag1", "tag2", "tag3"]
            },
            "image_placeholders": [
                "[IMAGE_0] Hero image showing real estate concept",
                "[IMAGE_1] Section break with chart",
                "[IMAGE_2] Social card for sharing"
            ],
            "content_structure_notes": "Structured this way to match platform requirements and audience expectations."
        }
    
    @patch('generate_content_draft.requests.post')
    def test_generate_draft_biggerpockets(self, mock_post):
        """Test draft generation for BiggerPockets."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps(self._create_mock_openai_response("BiggerPockets"))
                }
            }]
        }
        mock_post.return_value = mock_response
        
        with patch('generate_content_draft.log'):
            draft = gcd.generate_draft_with_openai(
                topic="Test Topic",
                audience="Operator",
                platform_target="BiggerPockets",
                priority=2,
                key_points=["Point 1", "Point 2"],
                proof_points=["Proof 1"],
                mentions=[]
            )
        
        self.assertIn("headline", draft)
        self.assertIn("body", draft)
        self.assertIn("seo_metadata", draft)
    
    @patch('generate_content_draft.requests.post')
    def test_generate_draft_linkedin(self, mock_post):
        """Test draft generation for LinkedIn."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps(self._create_mock_openai_response("LinkedIn"))
                }
            }]
        }
        mock_post.return_value = mock_response
        
        with patch('generate_content_draft.log'):
            draft = gcd.generate_draft_with_openai(
                topic="Test Topic",
                audience="CashBuyer",
                platform_target="LinkedIn",
                priority=1,
                key_points=["Point 1"],
                proof_points=["Proof 1"],
                mentions=[]
            )
        
        self.assertEqual(len(draft["key_points_formatted"]), 3)
    
    @patch('generate_content_draft.requests.post')
    def test_generate_draft_x_twitter(self, mock_post):
        """Test draft generation for X (Twitter)."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps(self._create_mock_openai_response("X"))
                }
            }]
        }
        mock_post.return_value = mock_response
        
        with patch('generate_content_draft.log'):
            draft = gcd.generate_draft_with_openai(
                topic="Test Topic",
                audience="Operator",
                platform_target="X",
                priority=2,
                key_points=["Point 1"],
                proof_points=["Proof 1"],
                mentions=[]
            )
        
        self.assertIn("body", draft)
    
    @patch('generate_content_draft.requests.post')
    def test_generate_draft_substack(self, mock_post):
        """Test draft generation for Substack."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps(self._create_mock_openai_response("Substack"))
                }
            }]
        }
        mock_post.return_value = mock_response
        
        with patch('generate_content_draft.log'):
            draft = gcd.generate_draft_with_openai(
                topic="Test Topic",
                audience="HNWI/LP",
                platform_target="Substack",
                priority=3,
                key_points=["Point 1"],
                proof_points=["Proof 1"],
                mentions=[]
            )
        
        self.assertIn("image_placeholders", draft)
        self.assertTrue(len(draft["image_placeholders"]) > 0)
    
    @patch('generate_content_draft.requests.post')
    def test_generate_draft_retry_on_failure(self, mock_post):
        """Test retry logic on API failure."""
        # First two calls fail, third succeeds
        mock_post.side_effect = [
            Exception("Timeout"),
            Exception("Rate limit"),
            Mock(json=lambda: {
                "choices": [{
                    "message": {
                        "content": json.dumps(self._create_mock_openai_response("LinkedIn"))
                    }
                }]
            })
        ]
        
        with patch('generate_content_draft.log'):
            with patch('time.sleep'):  # Skip actual sleep
                draft = gcd.generate_draft_with_openai(
                    topic="Test",
                    audience="Operator",
                    platform_target="LinkedIn",
                    priority=2,
                    key_points=[],
                    proof_points=[],
                    mentions=[],
                    max_retries=3
                )
        
        self.assertIn("headline", draft)


class TestDraftValidation(unittest.TestCase):
    """Test draft validation logic."""
    
    def test_validate_draft_biggerpockets_success(self):
        """Test successful validation for BiggerPockets."""
        draft = {
            "headline": "Test Headline for BiggerPockets",
            "hook": "This is a compelling hook with sufficient length.",
            "body": " ".join(["word"] * 2500),  # 2500 words
            "key_points_formatted": ["Point 1", "Point 2", "Point 3"],
            "proof_points_formatted": [],
            "cta": "Call to action",
            "seo_metadata": {},
            "image_placeholders": [],
            "content_structure_notes": "Notes"
        }
        
        is_valid, errors = gcd.validate_draft(draft, "BiggerPockets", "Operator")
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_draft_length_too_short(self):
        """Test validation fails when content is too short."""
        draft = {
            "headline": "Test Headline",
            "hook": "Short hook but long enough.",
            "body": " ".join(["word"] * 100),  # Only 100 words (too short for BiggerPockets)
            "key_points_formatted": ["Point 1", "Point 2", "Point 3"],
            "proof_points_formatted": [],
            "cta": "Call to action",
            "seo_metadata": {},
            "image_placeholders": [],
            "content_structure_notes": "Notes"
        }
        
        is_valid, errors = gcd.validate_draft(draft, "BiggerPockets", "Operator")
        
        self.assertFalse(is_valid)
        self.assertTrue(any("Word count" in e for e in errors))
    
    def test_validate_draft_compliance_hnwi(self):
        """Test compliance validation for HNWI/LP audience."""
        draft = {
            "headline": "Investment Returns",
            "hook": "This is a hook about investments.",
            "body": "We promise guaranteed returns of 20% per year with no risk. " * 200,
            "key_points_formatted": ["Point 1", "Point 2", "Point 3"],
            "proof_points_formatted": [],
            "cta": "Call to action",
            "seo_metadata": {},
            "image_placeholders": [],
            "content_structure_notes": "Notes"
        }
        
        is_valid, errors = gcd.validate_draft(draft, "LinkedIn", "HNWI/LP")
        
        self.assertFalse(is_valid)
        self.assertTrue(any("Compliance violation" in e for e in errors))
        self.assertTrue(any("guaranteed returns" in e for e in errors))
    
    def test_validate_draft_missing_key_points(self):
        """Test validation fails with insufficient key points."""
        draft = {
            "headline": "Test Headline",
            "hook": "Test hook with sufficient length.",
            "body": " ".join(["word"] * 1000),
            "key_points_formatted": ["Point 1"],  # Only 1 point (need 3+)
            "proof_points_formatted": [],
            "cta": "Call to action",
            "seo_metadata": {},
            "image_placeholders": [],
            "content_structure_notes": "Notes"
        }
        
        is_valid, errors = gcd.validate_draft(draft, "LinkedIn", "Operator")
        
        self.assertFalse(is_valid)
        self.assertTrue(any("key points" in e.lower() for e in errors))
    
    def test_validate_draft_x_tweet_count(self):
        """Test validation for X platform tweet count."""
        # Valid tweet count (10 tweets) - need to create body with sufficient length
        tweet_texts = ["This is a tweet with sufficient text to make it realistic and meet length requirements"] * 10
        draft = {
            "headline": "Test headline",
            "hook": "Test hook with enough text",
            "body": "\n\n".join(tweet_texts),  # 10 tweets with proper separators
            "key_points_formatted": ["Point 1", "Point 2", "Point 3"],
            "proof_points_formatted": [],
            "cta": "Call to action",
            "seo_metadata": {},
            "image_placeholders": [],
            "content_structure_notes": "Notes"
        }
        
        is_valid, errors = gcd.validate_draft(draft, "X", "Operator")
        
        self.assertTrue(is_valid, f"Validation failed with errors: {errors}")


class TestNotionUpdate(unittest.TestCase):
    """Test Notion database updates."""
    
    @patch('generate_content_draft.notion_update_page')
    @patch('generate_content_draft.log')
    def test_update_notion_with_draft_success(self, mock_log, mock_update):
        """Test successful Notion update with valid draft."""
        draft = {
            "headline": "Test Headline",
            "hook": "Test hook",
            "body": "Test body content",
            "key_points_formatted": ["Point 1"],
            "proof_points_formatted": ["Proof 1"],
            "cta": "CTA",
            "seo_metadata": {
                "title_tag": "SEO Title",
                "meta_description": "SEO Description",
                "keywords": ["kw1", "kw2"],
                "suggested_tags": ["tag1"]
            },
            "image_placeholders": ["[IMAGE_0] Description"],
            "content_structure_notes": "Notes"
        }
        
        gcd.update_notion_with_draft("test-id", draft)
        
        mock_update.assert_called_once()
        call_args = mock_update.call_args[0]
        self.assertEqual(call_args[0], "test-id")
        
        # Check that Status was set correctly
        properties = call_args[1]
        self.assertIn("Status", properties)
        self.assertEqual(properties["Status"]["status"]["name"], "Draft Ready for Review")
    
    @patch('generate_content_draft.notion_update_page')
    @patch('generate_content_draft.log')
    def test_update_notion_with_validation_errors(self, mock_log, mock_update):
        """Test Notion update when validation fails."""
        draft = {}
        errors = ["Error 1", "Error 2"]
        
        gcd.update_notion_with_draft("test-id", draft, validation_errors=errors)
        
        mock_update.assert_called_once()
        call_args = mock_update.call_args[0]
        properties = call_args[1]
        
        # Should set status to Draft Failed
        self.assertEqual(properties["Status"]["status"]["name"], "Draft Failed")


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases."""
    
    @patch('generate_content_draft.fetch_content_opportunities')
    @patch('generate_content_draft.log')
    def test_main_no_opportunities(self, mock_log, mock_fetch):
        """Test main function with no opportunities."""
        mock_fetch.return_value = []
        
        gcd.main()
        
        # Should exit gracefully
        mock_log.assert_any_call("No content opportunities found with Status='Ready to Draft'")
    
    @patch('generate_content_draft.CONTENT_GENERATION_ENABLED', False)
    @patch('generate_content_draft.log')
    def test_main_disabled(self, mock_log):
        """Test main function when generation is disabled."""
        gcd.main()
        
        mock_log.assert_any_call("Content generation is disabled (CONTENT_GENERATION_ENABLED=false)")


class TestLogging(unittest.TestCase):
    """Test logging functionality."""
    
    @patch('builtins.open', create=True)
    @patch('builtins.print')
    def test_log_writes_to_console_and_file(self, mock_print, mock_open):
        """Test that log writes to both console and file."""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        gcd.log("Test message")
        
        # Should print to console
        mock_print.assert_called_once()
        
        # Should write to file
        mock_file.write.assert_called_once()


class TestPropValue(unittest.TestCase):
    """Test Notion property value extraction."""
    
    def test_prop_value_title(self):
        """Test extraction of title property."""
        prop = {
            "type": "title",
            "title": [
                {"plain_text": "Hello "},
                {"plain_text": "World"}
            ]
        }
        
        result = gcd.prop_value(prop)
        self.assertEqual(result, "Hello World")
    
    def test_prop_value_select(self):
        """Test extraction of select property."""
        prop = {
            "type": "select",
            "select": {"name": "Option1"}
        }
        
        result = gcd.prop_value(prop)
        self.assertEqual(result, "Option1")
    
    def test_prop_value_relation(self):
        """Test extraction of relation property."""
        prop = {
            "type": "relation",
            "relation": [
                {"id": "id1"},
                {"id": "id2"}
            ]
        }
        
        result = gcd.prop_value(prop)
        self.assertEqual(result, ["id1", "id2"])


def run_tests():
    """Run all tests and report results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestContentOpportunityFetching))
    suite.addTests(loader.loadTestsFromTestCase(TestSourceMentionRetrieval))
    suite.addTests(loader.loadTestsFromTestCase(TestDraftGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestDraftValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestNotionUpdate))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestLogging))
    suite.addTests(loader.loadTestsFromTestCase(TestPropValue))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✓ ALL TESTS PASSED")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
