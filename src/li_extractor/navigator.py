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
            # First try direct navigation to posts URL
            posts_url = self._construct_posts_url(profile_url)

            self.logger.info(
                f"Attempting direct navigation to posts URL: {posts_url}",
                context={"posts_url": posts_url},
            )

            await self.action_tracker.execute_action(
                lambda: page.goto(posts_url, wait_until="networkidle"),
                wait_for_network=True,
                page=page,
            )

            # Wait a bit for page to load
            await asyncio.sleep(3)

            # Check if we successfully landed on a posts page
            if await self._verify_posts_page(page):
                self.logger.info(
                    "Successfully navigated to posts section via direct URL",
                    event_code=EventCodes.POSTS_TAB_OPENED,
                    context={"posts_url": posts_url},
                )
                return True

            # If direct navigation failed, try UI navigation
            self.logger.info("Direct navigation failed, trying UI navigation")
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

        # Handle different URL formats
        if "/recent-activity" in base_url:
            return base_url.replace("/recent-activity", "/recent-activity/posts/")
        else:
            return f"{base_url}/recent-activity/posts/"

    async def _verify_posts_page(self, page: Page) -> bool:
        """Verify we're on a posts page."""
        try:
            # Check URL first
            current_url = page.url
            if "/recent-activity" in current_url or "/posts" in current_url:
                # Look for posts-specific elements
                posts_indicators = [
                    ".scaffold-finite-scroll",
                    ".feed-container",
                    '[data-test-id="posts-container"]',
                    ".pv-recent-activity-detail__outlet",
                    ".pv-profile-section__card-item",
                    ".pvs-list",
                    ".artdeco-card",
                    ".pv-recent-activity-detail-v2",
                ]

                for selector in posts_indicators:
                    try:
                        element = await page.wait_for_selector(selector, timeout=5000)
                        if element:
                            self.logger.debug(
                                f"Posts page verified with selector: {selector}"
                            )
                            return True
                    except TimeoutError:
                        continue

                # If we're on the right URL but don't find specific selectors,
                # still consider it successful (page might be loading or have new structure)
                if "/recent-activity" in current_url:
                    self.logger.info("Posts page verified via URL pattern")
                    return True

            return False

        except Exception:
            return False

    async def _navigate_via_ui(self, page: Page, profile_url: str) -> bool:
        """Fallback navigation via UI clicks."""
        try:
            # Go to main profile first
            self.logger.info(f"Navigating to main profile: {profile_url}")
            await page.goto(profile_url, wait_until="networkidle")
            await asyncio.sleep(3)

            # Look for "Show all activity" or "Recent activity" sections
            activity_selectors = [
                # Modern LinkedIn selectors (2024)
                'a[href*="recent-activity"]:has-text("Show all")',
                'a[href*="recent-activity"]:has-text("activity")',
                'button:has-text("Show all"):visible',
                'a:has-text("Show all activity")',
                # Legacy selectors
                'a[href*="recent-activity"]',
                'text="Show all activity"',
                'text="Recent activity"',
                'text="Activity"',
                '[data-test-id="recent-activity-link"]',
                # Generic activity links
                '[aria-label*="activity"]',
                '[data-control-name*="activity"]',
            ]

            activity_found = False
            for selector in activity_selectors:
                try:
                    self.logger.debug(f"Trying activity selector: {selector}")

                    # Wait for element to be available
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element and await element.is_visible():
                        self.logger.info(
                            f"Found activity link with selector: {selector}"
                        )

                        await self.action_tracker.execute_action(
                            lambda el=element: el.click(),
                            wait_for_network=True,
                            page=page,
                        )
                        activity_found = True
                        break
                except TimeoutError:
                    continue
                except Exception as e:
                    self.logger.debug(f"Error with selector {selector}: {e}")
                    continue

            if not activity_found:
                self.logger.warning("Could not find Recent Activity link")
                return False

            # Wait for navigation and page load
            await asyncio.sleep(3)

            # Now look for "Posts" tab or section
            posts_selectors = [
                # Modern posts selectors
                'button[aria-selected="false"]:has-text("Posts")',
                'button:has-text("Posts"):visible',
                'a:has-text("Posts"):visible',
                '[data-test-id="posts-tab"]',
                # Legacy selectors
                'text="Posts"',
                'button[aria-label*="Posts"]',
                'a[href*="/posts/"]',
                # Tab-like selectors
                '.pv-profile-section__card-action-bar button:has-text("Posts")',
                '[role="tab"]:has-text("Posts")',
            ]

            posts_found = False
            for selector in posts_selectors:
                try:
                    self.logger.debug(f"Trying posts selector: {selector}")

                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element and await element.is_visible():
                        self.logger.info(f"Found posts tab with selector: {selector}")

                        await self.action_tracker.execute_action(
                            lambda el=element: el.click(),
                            wait_for_network=True,
                            page=page,
                        )
                        posts_found = True
                        break
                except TimeoutError:
                    continue
                except Exception as e:
                    self.logger.debug(f"Error with posts selector {selector}: {e}")
                    continue

            if not posts_found:
                self.logger.warning("Could not find Posts tab")
                # Check if we're already on a posts-like page
                if await self._verify_posts_page(page):
                    self.logger.info("Already on posts page, continuing")
                    posts_found = True
                else:
                    return False

            # Final verification
            await asyncio.sleep(2)
            if await self._verify_posts_page(page):
                self.logger.info(
                    "Successfully navigated to posts via UI",
                    event_code=EventCodes.POSTS_TAB_OPENED,
                )
                return True
            else:
                self.logger.warning(
                    "Navigation appeared successful but posts page not verified"
                )
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

        return posts

    async def _find_post_elements(self, page: Page) -> list[ElementHandle]:
        """Find all post elements on the current page."""
        # Updated selectors for modern LinkedIn posts
        post_selectors = [
            # Modern activity feed selectors
            ".pv-recent-activity-detail__outlet .pvs-list__paged-list-item",
            ".pv-recent-activity-detail-v2 .pvs-list__item--line-separated",
            ".pvs-list__item--with-top-padding",
            ".pvs-list__paged-list-item",
            # Legacy selectors
            '[data-id^="urn:li:activity"]',
            ".feed-shared-update-v2",
            ".update-components-update-v2",
            '[data-test-id="post"]',
            ".feed-shared-update-v2__content",
            # Generic activity items
            ".pv-profile-section__card-item",
            ".artdeco-card .pvs-list__item",
        ]

        all_posts = []

        for selector in post_selectors:
            try:
                self.logger.debug(f"Trying post selector: {selector}")
                elements = await page.query_selector_all(selector)
                if elements:
                    self.logger.debug(
                        f"Found {len(elements)} elements with selector: {selector}"
                    )
                    # Filter out duplicates by checking element handles
                    for element in elements:
                        if element not in all_posts:
                            all_posts.append(element)
                    break  # Use first selector that finds posts
            except Exception as e:
                self.logger.debug(f"Error with selector {selector}: {e}")
                continue

        self.logger.info(f"Total unique posts found: {len(all_posts)}")
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
                ".pvs-list__footer-wrapper button",
                'button:has-text("See more")',
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
    ) -> list[dict[str, Any]]:
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
