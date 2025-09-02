# tests/e2e/test_navigation.py
"""End-to-end tests for LinkedIn navigation."""

import os

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

    def should_run_e2e_tests(self) -> bool:
        """Check if e2e tests should run based on environment."""
        return os.getenv("RUN_E2E_TESTS", "false").lower() == "true"

    @pytest.mark.asyncio
    async def test_profile_navigation(self, browser_manager, navigator, tmp_path):
        """Test navigation to LinkedIn profile posts."""
        if not self.should_run_e2e_tests():
            pytest.skip("E2E tests disabled. Set RUN_E2E_TESTS=true to enable.")

        storage_path = tmp_path / "storage.json"
        test_profile = os.getenv(
            "TEST_LINKEDIN_PROFILE", "https://www.linkedin.com/in/juansebastianmd/"
        )

        try:
            # Start browser (will require manual login if no session)
            page = await browser_manager.start_browser(
                storage_state_path=storage_path,
                headless=os.getenv("E2E_HEADLESS", "false").lower() == "true",
                timeout=30000,
            )

            # Test navigation
            success = await navigator.navigate_to_posts(page, test_profile)
            assert success, "Should successfully navigate to posts section"

            # Verify we're on the right page
            current_url = page.url
            assert any(
                keyword in current_url
                for keyword in ["recent-activity", "posts", "activity"]
            ), f"Expected to be on posts page, but got: {current_url}"

        finally:
            await browser_manager.close()

    @pytest.mark.asyncio
    async def test_posts_loading(self, browser_manager, navigator, tmp_path):
        """Test loading posts from profile."""
        if not self.should_run_e2e_tests():
            pytest.skip("E2E tests disabled. Set RUN_E2E_TESTS=true to enable.")

        storage_path = tmp_path / "storage.json"
        test_profile = os.getenv(
            "TEST_LINKEDIN_PROFILE", "https://www.linkedin.com/in/juansebastianmd/"
        )

        try:
            page = await browser_manager.start_browser(
                storage_state_path=storage_path,
                headless=os.getenv("E2E_HEADLESS", "false").lower() == "true",
            )

            # Navigate to posts
            nav_success = await navigator.navigate_to_posts(page, test_profile)
            assert nav_success, "Navigation should succeed"

            # Load posts with short timeout for testing
            posts = await navigator.load_posts(page, min_posts=3, max_seconds=20)

            assert len(posts) > 0, "Should find at least some posts"
            print(f"Found {len(posts)} posts")

        finally:
            await browser_manager.close()

    @pytest.mark.asyncio
    async def test_full_extraction(self, browser_manager, navigator, tmp_path):
        """Test complete extraction workflow."""
        if not self.should_run_e2e_tests():
            pytest.skip("E2E tests disabled. Set RUN_E2E_TESTS=true to enable.")

        storage_path = tmp_path / "storage.json"
        test_profile = os.getenv(
            "TEST_LINKEDIN_PROFILE", "https://www.linkedin.com/in/juansebastianmd/"
        )

        try:
            page = await browser_manager.start_browser(
                storage_state_path=storage_path,
                headless=os.getenv("E2E_HEADLESS", "false").lower() == "true",
            )

            # Navigate and load posts
            await navigator.navigate_to_posts(page, test_profile)
            post_elements = await navigator.load_posts(
                page, min_posts=2, max_seconds=15
            )

            # Extract data
            if post_elements:
                posts_data = await navigator.extract_posts_data(post_elements, page)

                assert len(posts_data) > 0, "Should extract some post data"
                print(f"Extracted {len(posts_data)} posts")

                # Verify data structure
                for i, post in enumerate(posts_data):
                    print(f"Post {i+1}: ID={post.get('post_id', 'N/A')[:20]}...")
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
                        assert field in post, f"Missing field '{field}' in post {i+1}"

        finally:
            await browser_manager.close()


# Add a utility test that can run without LinkedIn access
class TestNavigatorUnit:
    """Unit tests for navigator components that don't require LinkedIn."""

    @pytest.fixture
    def logger(self, tmp_path):
        """Create test logger."""
        log_file = tmp_path / "test.log"
        return StructuredLogger("test_navigator", log_file, "DEBUG")

    @pytest.fixture
    def navigator(self, logger):
        """Create LinkedIn navigator."""
        return LinkedInNavigator(logger)

    def test_construct_posts_url(self, navigator):
        """Test URL construction for posts section."""
        test_cases = [
            (
                "https://www.linkedin.com/in/johndoe/",
                "https://www.linkedin.com/in/johndoe/recent-activity/posts/",
            ),
            (
                "https://www.linkedin.com/in/johndoe",
                "https://www.linkedin.com/in/johndoe/recent-activity/posts/",
            ),
            (
                "https://www.linkedin.com/in/johndoe/recent-activity",
                "https://www.linkedin.com/in/johndoe/recent-activity/posts",
            ),
        ]

        for profile_url, expected_posts_url in test_cases:
            result = navigator._construct_posts_url(profile_url)
            assert result == expected_posts_url, f"Failed for {profile_url}"
