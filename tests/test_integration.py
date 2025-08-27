# tests/test_integration.py
"""Integration tests for complete workflows."""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from li_extractor.cli import run_extraction


@pytest.mark.asyncio
async def test_full_extraction_workflow(temp_output_dir, sample_extraction_data):
    """Test complete extraction workflow."""
    
    # Mock all the components
    mock_browser_manager = AsyncMock()
    mock_navigator = AsyncMock()
    mock_output_manager = MagicMock()
    mock_logger = MagicMock()
    
    # Configure mocks
    mock_page = AsyncMock()
    mock_browser_manager.start_browser.return_value = mock_page
    mock_navigator.navigate_to_posts.return_value = True
    mock_navigator.load_posts.return_value = [MagicMock()]  # Mock post elements
    mock_navigator.extract_posts_data.return_value = sample_extraction_data["posts"]
    mock_output_manager.write_results.return_value = True
    
    # Patch the classes
    with patch('li_extractor.cli.BrowserManager', return_value=mock_browser_manager), \
         patch('li_extractor.cli.LinkedInNavigator', return_value=mock_navigator), \
         patch('li_extractor.cli.OutputManager', return_value=mock_output_manager):
        
        result = await run_extraction(
            profile_url="https://linkedin.com/in/test/",
            min_posts=10,
            max_seconds=60,
            output_file=temp_output_dir / "output.json",
            storage_state=temp_output_dir / "session" / "storage.json",
            headless=True,
            logger=mock_logger
        )
    
    assert result is True
    
    # Verify method calls
    mock_browser_manager.start_browser.assert_called_once()
    mock_navigator.navigate_to_posts.assert_called_once()
    mock_navigator.load_posts.assert_called_once()
    mock_navigator.extract_posts_data.assert_called_once()
    mock_output_manager.write_results.assert_called_once()
    mock_browser_manager.close.assert_called_once()


@pytest.mark.asyncio
async def test_extraction_with_navigation_failure(temp_output_dir):
    """Test extraction handling navigation failure."""
    
    mock_browser_manager = AsyncMock()
    mock_navigator = AsyncMock()
    mock_logger = MagicMock()
    
    # Configure navigation to fail
    mock_navigator.navigate_to_posts.return_value = False
    
    with patch('li_extractor.cli.BrowserManager', return_value=mock_browser_manager), \
         patch('li_extractor.cli.LinkedInNavigator', return_value=mock_navigator):
        
        result = await run_extraction(
            profile_url="https://linkedin.com/in/test/",
            min_posts=10,
            max_seconds=60,
            output_file=temp_output_dir / "output.json",
            storage_state=temp_output_dir / "session" / "storage.json",
            headless=True,
            logger=mock_logger
        )
    
    assert result is False


@pytest.mark.asyncio
async def test_extraction_with_no_posts(temp_output_dir):
    """Test extraction when no posts are found."""
    
    mock_browser_manager = AsyncMock()
    mock_navigator = AsyncMock()
    mock_output_manager = MagicMock()
    mock_logger = MagicMock()
    
    # Configure to find no posts
    mock_navigator.navigate_to_posts.return_value = True
    mock_navigator.load_posts.return_value = []
    mock_output_manager.write_results.return_value = True
    
    with patch('li_extractor.cli.BrowserManager', return_value=mock_browser_manager), \
         patch('li_extractor.cli.LinkedInNavigator', return_value=mock_navigator), \
         patch('li_extractor.cli.OutputManager', return_value=mock_output_manager):
        
        result = await run_extraction(
            profile_url="https://linkedin.com/in/test/",
            min_posts=10,
            max_seconds=60,
            output_file=temp_output_dir / "output.json",
            storage_state=temp_output_dir / "session" / "storage.json",
            headless=True,
            logger=mock_logger
        )
    
    assert result is True  # Should still succeed with empty results
    
    # Verify empty results were written
    call_args = mock_output_manager.write_results.call_args
    assert call_args[1]['posts_data'] == []
    assert call_args[1]['reason'] == 'no_posts_found'