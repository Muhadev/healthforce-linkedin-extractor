# tests/e2e/test_navigation.py
"""End-to-end tests for LinkedIn navigation (requires manual setup)."""

import pytest

from li_extractor.browser import BrowserManager
from li_extractor.logging_ import StructuredLogger
from li_extractor.navigator import LinkedInNavigator

# Mark all tests as requiring live LinkedIn access
pytestmark = pytest.mark.e2e


class TestLinkedInNavigationE2E:
    """End-to-end navigation tests."""

    @pytest.fixture
    def logger(self, tmp_path):
        """Create test logger."""
        log_file = tmp_path / "test.log"
        return StructuredLogger("test_navigator", log_file, "DEBUG")

    @pytest.fixture
    def browser_manager(self, logger):
        """Create browser manager."""
        return BrowserManager(logger)

    @pytest.fixture
    def navigator(self, logger):
        """Create LinkedIn navigator."""
        return LinkedInNavigator(logger)

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires manual LinkedIn session setup")
    async def test_profile_navigation(self, browser_manager, navigator, tmp_path):
        """Test navigation to LinkedIn profile posts."""
        storage_path = tmp_path / "storage.json"
        test_profile = "https://www.linkedin.com/in/juansebastianmd/"

        try:
            # Start browser (will require manual login if no session)
            page = await browser_manager.start_browser(
                storage_state_path=storage_path,
                headless=False,  # Use headful for manual testing
            )

            # Test navigation
            success = await navigator.navigate_to_posts(page, test_profile)
            assert success, "Should successfully navigate to posts section"

            # Verify we're on the right page
            current_url = page.url
            assert "recent-activity" in current_url or "posts" in current_url

        finally:
            await browser_manager.close()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires manual LinkedIn session setup")
    async def test_posts_loading(self, browser_manager, navigator, tmp_path):
        """Test loading posts from profile."""
        storage_path = tmp_path / "storage.json"
        test_profile = "https://www.linkedin.com/in/juansebastianmd/"

        try:
            page = await browser_manager.start_browser(
                storage_state_path=storage_path, headless=False
            )

            # Navigate to posts
            await navigator.navigate_to_posts(page, test_profile)

            # Load posts with short timeout for testing
            posts = await navigator.load_posts(page, min_posts=5, max_seconds=30)

            assert len(posts) > 0, "Should find at least some posts"
            assert len(posts) <= 5, "Should respect min_posts limit"

        finally:
            await browser_manager.close()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires manual LinkedIn session setup")
    async def test_full_extraction(self, browser_manager, navigator, tmp_path):
        """Test complete extraction workflow."""
        storage_path = tmp_path / "storage.json"
        test_profile = "https://www.linkedin.com/in/juansebastianmd/"

        try:
            page = await browser_manager.start_browser(
                storage_state_path=storage_path, headless=False
            )

            # Navigate and load posts
            await navigator.navigate_to_posts(page, test_profile)
            post_elements = await navigator.load_posts(
                page, min_posts=3, max_seconds=20
            )

            # Extract data
            if post_elements:
                posts_data = await navigator.extract_posts_data(post_elements, page)

                assert len(posts_data) > 0, "Should extract some post data"

                # Verify data structure
                for post in posts_data:
                    assert "post_id" in post
                    assert post["post_id"] is not None
                    # Other fields may be None but should exist
                    required_fields = [
                        "author_name",
                        "posted_at",
                        "text",
                        "hashtags",
                        "links",
                        "reactions_count",
                        "comments_count",
                    ]
                    for field in required_fields:
                        assert field in post

        # finally:
        #     await browser_manager.close()
        #                 assert field in post

        finally:
            await browser_manager.close()
