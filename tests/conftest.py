# Additional test files for comprehensive coverage

# tests/conftest.py
"""Pytest configuration and shared fixtures."""

from unittest.mock import MagicMock

import pytest

from li_extractor.logging_ import StructuredLogger


@pytest.fixture
def mock_logger():
    """Create mock logger for testing."""
    return MagicMock(spec=StructuredLogger)


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir()
    (output_dir / "session").mkdir()
    return output_dir


@pytest.fixture
def sample_post_data():
    """Sample post data for testing."""
    return {
        "post_id": "test-post-123",
        "author_name": "John Doe",
        "posted_at": "2025-08-27T10:30:00Z",
        "text": "Excited to share insights on #AI and #MachineLearning! Check out this article: https://example.com/ai-trends",
        "hashtags": ["AI", "MachineLearning"],
        "links": ["https://example.com/ai-trends"],
        "reactions_count": 42,
        "comments_count": 5,
    }


@pytest.fixture
def sample_extraction_data(sample_post_data):
    """Sample extraction result data."""
    return {
        "profile_url": "https://linkedin.com/in/johndoe/",
        "fetched_at": "2025-08-27T12:00:00Z",
        "total_posts": 1,
        "posts": [sample_post_data],
        "extraction_duration_seconds": 45.5,
        "reason": "completed",
    }
