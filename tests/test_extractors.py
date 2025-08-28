# tests/test_extractors.py
"""Tests for DOM extraction utilities."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from li_extractor.extractors import PostExtractor
from li_extractor.logging_ import StructuredLogger


class TestPostExtractor:
    """Test cases for PostExtractor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_logger = MagicMock(spec=StructuredLogger)
        self.extractor = PostExtractor(self.mock_logger)

    def test_extract_hashtags(self):
        """Test hashtag extraction from text."""
        test_cases = [
            ("Excited about #AI and #MachineLearning!", ["ai", "machinelearning"]),
            ("No hashtags here", []),
            ("#SingleHashtag", ["singlehashtag"]),
            ("Multiple #AI #ML #Tech #Innovation", ["ai", "innovation", "ml", "tech"]),
            ("Mixed case #AI #ai #Ai", ["ai"]),  # Should deduplicate
            (
                "Unicode #Développement #データサイエンス",
                ["développement", "データサイエンス"],
            ),
        ]

        for text, expected in test_cases:
            result = self.extractor._extract_hashtags(text)
            assert result == expected, f"Failed for '{text}'"

    def test_parse_engagement_counts(self):
        """Test engagement count parsing."""
        test_cases = [
            ("120 reactions • 45 comments", (120, 45)),
            ("5 reactions", (5, None)),
            ("10 comments", (None, 10)),
            ("1,234 reactions • 567 comments", (1234, 567)),
            ("No engagement text", (None, None)),
            ("0 reactions • 0 comments", (0, 0)),
        ]

        for text, expected in test_cases:
            result = self.extractor._parse_engagement_counts(text)
            assert result == expected, f"Failed for '{text}'"

    def test_normalize_count(self):
        """Test count normalization."""
        test_cases = [
            ("123", 123),
            ("1,234", 1234),
            ("1,234,567", 1234567),
            ("0", 0),
        ]

        for count_str, expected in test_cases:
            result = self.extractor._normalize_count(count_str)
            assert result == expected, f"Failed for '{count_str}'"

    def test_normalize_count_invalid(self):
        """Test count normalization with invalid input."""
        invalid_cases = ["", "abc", None]

        for count_str in invalid_cases:
            result = self.extractor._normalize_count(count_str)
            assert result == 0, f"Should return 0 for '{count_str}'"

    def test_parse_single_count(self):
        """Test single count parsing."""
        test_cases = [
            ("123 reactions", 123),
            ("1,234", 1234),
            ("No numbers here", None),
            ("5", 5),
        ]

        for text, expected in test_cases:
            result = self.extractor._parse_single_count(text)
            assert result == expected, f"Failed for '{text}'"

    @pytest.mark.asyncio
    async def test_extract_post_data_with_mock(self):
        """Test post data extraction with mocked DOM."""
        # Create mock post element
        mock_element = AsyncMock()
        mock_element.get_attribute = AsyncMock()
        mock_element.query_selector = AsyncMock()
        mock_element.query_selector_all = AsyncMock(return_value=[])

        # Mock page
        mock_page = AsyncMock()
        mock_page.url = "https://linkedin.com/in/test/"

        # Configure mock responses
        mock_element.get_attribute.side_effect = lambda attr: {
            "data-id": "test-post-123"
        }.get(attr)

        # Mock author name element
        mock_author_element = AsyncMock()
        mock_author_element.inner_text = AsyncMock(return_value="John Doe")

        # Mock text element
        mock_text_element = AsyncMock()
        mock_text_element.inner_text = AsyncMock(
            return_value="Great insights on #AI and #ML!"
        )

        # Mock time element
        mock_time_element = AsyncMock()
        mock_time_element.get_attribute = AsyncMock(return_value="2025-08-27T10:30:00Z")
        mock_time_element.inner_text = AsyncMock(return_value="2h")

        # Configure query_selector to return appropriate elements
        def mock_query_selector(selector):
            if "author" in selector or "name" in selector:
                return mock_author_element
            elif "text" in selector or "commentary" in selector:
                return mock_text_element
            elif selector == "time":
                return mock_time_element
            return None

        mock_element.query_selector.side_effect = mock_query_selector

        # Test extraction
        result = await self.extractor.extract_post_data(mock_element, mock_page)

        assert result is not None
        assert result["post_id"] == "test-post-123"
        assert result["author_name"] == "John Doe"
        assert result["text"] == "Great insights on #AI and #ML!"
        assert result["hashtags"] == ["ai", "ml"]
