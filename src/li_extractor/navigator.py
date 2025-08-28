# src/li_extractor/navigator.py
"""LinkedIn profile navigation and post loading."""

import asyncio
import time
from typing import Any

from playwright.async_api import ElementHandle, Page, TimeoutError

from .extractors import PostExtractor
from .logging_ import EventCodes, StructuredLogger
from .rate_limit import ActionTracker


class LinkedInNavigator:
    """Navigate LinkedIn profiles and load posts."""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.action_tracker = ActionTracker(logger)
        self.extractor = PostExtractor(logger)

    async def navigate_to_posts(self, page: Page, profile_url: str) -> bool:
        """Navigate to the posts section of a LinkedIn profile."""
        try:
            # First go to the profile
            await self.action_tracker.execute_action(
                lambda: page.goto(profile_url, wait_until="networkidle"),
                wait_for_network=True,
                page=page,
            )

            # Try direct navigation to posts URL first
            posts_url = self._construct_posts_url(profile_url)

            await self.action_tracker.execute_action(
                lambda: page.goto(profile_url, wait_until="networkidle"),
                wait_for_network=True,
                page=page,
            )

            # Verify we're on the posts page
            try:
                await page.wait_for_selector(
                    '.scaffold-finite-scroll, .feed-container, [data-test-id="posts-container"]',
                    timeout=10000,
                )

                self.logger.info(
                    "Successfully navigated to posts section",
                    event_code=EventCodes.POSTS_TAB_OPENED,
                    context={"posts_url": posts_url},
                )
                return True

            except TimeoutError:
                # Fallback: try clicking through the UI
                return await self._navigate_via_ui(page, profile_url)

        except Exception as e:
            self.logger.error(
                f"Failed to navigate to posts: {e}",
                event_code=EventCodes.NAVIGATION_ERROR,
                context={"profile_url": profile_url, "error": str(e)[:200]},
                exc_info=True,
            )
            return False

    def _construct_posts_url(self, profile_url: str) -> str:
        """Construct direct URL to posts section."""
        base_url = profile_url.rstrip("/")
        if "/recent-activity" not in base_url:
            return f"{base_url}/recent-activity/posts/"
        return base_url.replace("/recent-activity", "/recent-activity/posts")

    async def _navigate_via_ui(self, page: Page, profile_url: str) -> bool:
        """Fallback navigation via UI clicks."""
        try:
            # Go back to main profile
            await page.goto(profile_url, wait_until="networkidle")

            # Look for "Recent activity" or "Activity" link
            activity_selectors = [
                'a[href*="recent-activity"]',
                'text="Recent activity"',
                'text="Activity"',
                '[data-test-id="recent-activity-link"]',
            ]

            for selector in activity_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element is not None:
                        # lambda with default parameter to bind the variable
                        await self.action_tracker.execute_action(
                            lambda el=element: el.click(),
                            wait_for_network=True,
                            page=page,
                        )
                        break
                except TimeoutError:
                    continue
            else:
                self.logger.warning("Could not find Recent Activity link")
                return False

            # Look for "Posts" tab
            posts_selectors = [
                'text="Posts"',
                'button[aria-label*="Posts"]',
                'a[href*="/posts/"]',
                '[data-test-id="posts-tab"]',
            ]

            for selector in posts_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element is not None:
                        # lambda with default parameter to bind the variable
                        await self.action_tracker.execute_action(
                            lambda el=element: el.click(),
                            wait_for_network=True,
                            page=page,
                        )

                        self.logger.info(
                            "Navigated to posts via UI",
                            event_code=EventCodes.POSTS_TAB_OPENED,
                        )
                        return True

                except TimeoutError:
                    continue

            self.logger.warning("Could not find Posts tab")
            return False

        except Exception as e:
            self.logger.error(
                f"UI navigation failed: {e}",
                event_code=EventCodes.NAVIGATION_ERROR,
                exc_info=True,
            )
            return False

    async def load_posts(
        self, page: Page, min_posts: int = 10, max_seconds: int = 60
    ) -> list[ElementHandle]:
        """Load posts by scrolling, respecting limits."""
        start_time = time.time()
        posts: list[ElementHandle] = []
        last_post_count = 0
        consecutive_no_new_posts = 0

        while True:
            current_time = time.time()
            elapsed = current_time - start_time

            # Check time limit
            if elapsed > max_seconds:
                self.logger.info(
                    f"Reached time limit ({max_seconds}s), stopping",
                    event_code=EventCodes.LOAD_TIMEOUT,
                    context={
                        "posts_found": len(posts),
                        "elapsed_seconds": elapsed,
                        "min_posts_target": min_posts,
                    },
                )
                break

            # Find all post elements
            current_posts = await self._find_post_elements(page)

            # Check if we have enough posts
            if len(current_posts) >= min_posts:
                posts = current_posts[:min_posts]  # Take only what we need
                self.logger.info(
                    f"Minimum posts requirement met ({min_posts})",
                    event_code=EventCodes.MIN_POSTS_MET,
                    context={"posts_found": len(posts), "elapsed_seconds": elapsed},
                )
                break

            # Check if we found new posts
            if len(current_posts) > last_post_count:
                posts = current_posts
                last_post_count = len(current_posts)
                consecutive_no_new_posts = 0

                self.logger.debug(
                    f"Found {len(current_posts)} posts",
                    event_code=EventCodes.SCROLLED_BATCH,
                    context={"total_posts": len(current_posts)},
                )
            else:
                consecutive_no_new_posts += 1

                # If no new posts for several attempts, we might be at the end
                if consecutive_no_new_posts >= 3:
                    self.logger.info(
                        "No new posts found after multiple scroll attempts",
                        context={
                            "posts_found": len(posts),
                            "consecutive_failures": consecutive_no_new_posts,
                        },
                    )
                    break

            # Scroll to load more posts
            await self._scroll_to_load_more(page)

            await self.action_tracker.execute_action(
                lambda: asyncio.sleep(2),
                min_ms=500,
                max_ms=1000,
            )

        duration = time.time() - start_time
        context: dict[str, Any] = {
            "total_posts_loaded": len(posts),
            "duration_seconds": duration,
        }
        self.logger.info(
            "Post loading completed",
            context=context,
        )

        # If we exit the loop without finding enough posts, log a warning
        if len(posts) < min_posts:
            self.logger.warning(
                "Timeout while loading posts",
                event_code=EventCodes.LOAD_TIMEOUT,
                context={"timeout_seconds": max_seconds},
            )

        return posts

    async def _find_post_elements(self, page: Page) -> list[ElementHandle]:
        """Find all post elements on the current page."""
        post_selectors = [
            '[data-id^="urn:li:activity"]',
            ".feed-shared-update-v2",
            ".update-components-update-v2",
            '[data-test-id="post"]',
            ".feed-shared-update-v2__content",
        ]

        all_posts = []

        for selector in post_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    # Filter out duplicates by checking element handles
                    for element in elements:
                        if element not in all_posts:
                            all_posts.append(element)
                    break  # Use first selector that finds posts
            except Exception:
                continue

        return all_posts

    async def _scroll_to_load_more(self, page: Page) -> None:
        """Scroll down to trigger loading of more posts."""
        await self.action_tracker.execute_action(
            lambda: page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)"),
            min_ms=200,
            max_ms=500,
        )

        # Try to find and click "Show more" button if present
        try:
            show_more_selectors = [
                'button:has-text("Show more")',
                'button[aria-label*="Show more"]',
                ".scaffold-finite-scroll__load-button",
                ".pv5 button",
            ]

            for selector in show_more_selectors:
                element = await page.query_selector(selector)
                if element and await element.is_visible():

                    await self.action_tracker.execute_action(
                        lambda el=element: el.click(),
                        wait_for_network=True,
                        page=page,
                    )
                    break
        except Exception:
            # Show more button is optional
            pass

    async def extract_posts_data(
        self, post_elements: list[ElementHandle], page: Page
    ) -> list[dict[str, Any]]:  # Fix: Add type parameters
        """Extract structured data from all post elements."""
        extracted_posts: list[dict[str, Any]] = []

        for i, post_element in enumerate(post_elements):
            try:
                self.logger.debug(f"Extracting post {i+1}/{len(post_elements)}")

                post_data = await self.extractor.extract_post_data(post_element, page)

                if post_data:
                    extracted_posts.append(post_data)
                else:
                    self.logger.warning(
                        f"Failed to extract data for post {i+1}",
                        event_code=EventCodes.PARSE_WARNING,
                        context={"post_index": i + 1},
                    )

            except Exception as e:
                self.logger.warning(
                    f"Error extracting post {i+1}: {e}",
                    event_code=EventCodes.PARSE_WARNING,
                    context={"post_index": i + 1, "error": str(e)[:200]},
                    exc_info=True,
                )

        self.logger.info(
            f"Extracted data from {len(extracted_posts)}/{len(post_elements)} posts",
            context={"successful_extractions": len(extracted_posts)},
        )

        return extracted_posts
