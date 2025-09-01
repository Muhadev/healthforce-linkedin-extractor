# src/li_extractor/extractors.py
"""DOM extraction utilities for LinkedIn posts."""

import re
from typing import Any
from urllib.parse import urljoin, urlparse

from playwright.async_api import ElementHandle, Page

from .logging_ import EventCodes, StructuredLogger
from .timeparse import TimeParser


class PostExtractor:
    """Extract structured data from LinkedIn post DOM elements."""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.time_parser = TimeParser()

        # Regex for hashtag extraction (Unicode-aware)
        # self.hashtag_pattern = re.compile(r"(?i)(?<!\w)#([\p{L}0-9_]+)", re.UNICODE)
        self.hashtag_pattern = re.compile(r"(?i)(?<!\w)#([A-Za-z0-9_]+)", re.UNICODE)

        # Regex for count parsing (handles various formats)
        self.count_pattern = re.compile(r"(\d+(?:,\d+)*)", re.UNICODE)

    async def extract_post_data(
        self, post_element: ElementHandle, page: Page
    ) -> dict[str, Any] | None:
        """Extract all data from a single post element."""
        try:
            post_data: dict[str, Any] = {
                "post_id": None,
                "author_name": None,
                "posted_at": None,
                "text": None,
                "hashtags": [],
                "links": [],
                "reactions_count": None,
                "comments_count": None,
            }

            # Extract post ID from data attributes or href
            post_id = await self._extract_post_id(post_element)
            post_data["post_id"] = post_id or f"unknown_{hash(str(post_element))}"

            # Extract author name
            post_data["author_name"] = await self._extract_author_name(post_element)

            # Extract timestampf
            post_data["posted_at"] = await self._extract_timestamp(post_element)

            # Extract post text
            post_data["text"] = await self._extract_text_content(post_element)

            # Extract hashtags from text
            if isinstance(post_data["text"], str):
                post_data["hashtags"] = self._extract_hashtags(post_data["text"])

            # Extract links
            post_data["links"] = await self._extract_links(post_element, page.url)

            # Extract reaction and comment counts
            reactions, comments = await self._extract_engagement_counts(post_element)
            post_data["reactions_count"] = reactions
            post_data["comments_count"] = comments

            self.logger.info(
                "Post extracted successfully",
                event_code=EventCodes.POST_FOUND,
                context={"post_id": post_data["post_id"][:50]},  # Truncate for logs
            )

            return post_data

        except Exception as e:
            self.logger.warning(
                f"Failed to extract post data: {str(e)}",
                event_code=EventCodes.PARSE_WARNING,
                context={"error": str(e)[:200]},  # Truncate error message
            )
            return None

    async def _extract_post_id(self, post_element: ElementHandle) -> str | None:
        """Extract unique post identifier."""
        try:
            # Try data-id attribute
            data_id = await post_element.get_attribute("data-id")
            if data_id:
                return data_id

            # Try to find permalink in post
            permalink_selector = 'a[href*="/posts/"], a[href*="/activity-"]'
            permalink = await post_element.query_selector(permalink_selector)
            if permalink:
                href = await permalink.get_attribute("href")
                if href:
                    # Extract post ID from URL
                    match = re.search(r"/posts/([^/?]+)", href)
                    if match:
                        return match.group(1)

            return None

        except Exception:
            return None

    async def _extract_author_name(self, post_element: ElementHandle) -> str | None:
        """Extract post author name."""
        try:
            # Try various selectors for author name
            selectors = [
                '[data-test-id="post-author-name"]',
                ".feed-shared-actor__name",
                ".update-components-actor__name",
                'span[aria-label*="name"] span[aria-hidden="true"]',
                ".feed-shared-actor__title",
            ]

            for selector in selectors:
                element = await post_element.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and text.strip():
                        return text.strip()

            return None

        except Exception:
            self.logger.debug(
                "Could not extract author name",
                event_code=EventCodes.FIELD_MISSING,
                context={"field": "author_name"},
            )
            return None

    async def _extract_timestamp(self, post_element: ElementHandle) -> str | None:
        """Extract and normalize post timestamp."""
        try:
            # Try time element with datetime attribute
            time_element = await post_element.query_selector("time")
            if time_element:
                datetime_attr = await time_element.get_attribute("datetime")
                if datetime_attr:
                    parsed = self.time_parser.parse_relative_time(datetime_attr)
                    if parsed:
                        return parsed.isoformat()

                # Fallback to time element text
                time_text = await time_element.inner_text()
                if time_text:
                    parsed = self.time_parser.parse_relative_time(time_text.strip())
                    if parsed:
                        return parsed.isoformat()

            # Try aria-label with timestamp
            selectors = [
                '[aria-label*="ago"]',
                '[aria-label*="hours"]',
                '[aria-label*="minutes"]',
                '[aria-label*="days"]',
            ]

            for selector in selectors:
                element = await post_element.query_selector(selector)
                if element:
                    aria_label = await element.get_attribute("aria-label")
                    if aria_label:
                        parsed = self.time_parser.parse_relative_time(aria_label)
                        if parsed:
                            return parsed.isoformat()

            return None

        except Exception:
            self.logger.debug(
                "Could not extract timestamp",
                event_code=EventCodes.FIELD_MISSING,
                context={"field": "posted_at"},
            )
            return None

    async def _extract_text_content(self, post_element: ElementHandle) -> str | None:
        """Extract main post text content."""
        try:
            # Try various selectors for post content
            selectors = [
                '[data-test-id="post-text"]',
                ".feed-shared-text",
                ".update-components-text",
                ".feed-shared-update-v2__commentary",
                '.break-words span[dir="ltr"]',
            ]

            for selector in selectors:
                element = await post_element.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and text.strip():
                        return text.strip()

            return None

        except Exception:
            self.logger.debug(
                "Could not extract text content",
                event_code=EventCodes.FIELD_MISSING,
                context={"field": "text"},
            )
            return None

    def _extract_hashtags(self, text: str) -> list[str]:
        """Extract hashtags from post text."""
        if not text:
            return []

        hashtags = self.hashtag_pattern.findall(text)
        # Normalize to lowercase and deduplicate
        return sorted({tag.lower() for tag in hashtags if tag})

    async def _extract_links(
        self, post_element: ElementHandle, base_url: str
    ) -> list[str]:
        """Extract external links from post."""
        try:
            links = []

            # Find all links in the post
            link_elements = await post_element.query_selector_all("a[href]")

            for link_element in link_elements:
                href = await link_element.get_attribute("href")
                if not href:
                    continue

                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, href)
                parsed = urlparse(absolute_url)

                # Only include external links (not LinkedIn internal links)
                if parsed.netloc and not parsed.netloc.endswith("linkedin.com"):
                    if absolute_url not in links:
                        links.append(absolute_url)

            return links

        except Exception:
            return []

    async def _extract_engagement_counts(
        self, post_element: ElementHandle
    ) -> tuple[int | None, int | None]:
        """Extract reaction and comment counts."""
        reactions_count = None
        comments_count = None

        try:
            # Try to find engagement section
            engagement_selectors = [
                ".social-counts-reactions__count",
                '[aria-label*="reaction"]',
                ".feed-shared-social-action-bar",
                ".social-counts",
            ]

            for selector in engagement_selectors:
                element = await post_element.query_selector(selector)
                if element:
                    # Get aria-label which often contains counts like "120 reactions • 45 comments"
                    aria_label = await element.get_attribute("aria-label")
                    if aria_label:
                        reactions_count, comments_count = self._parse_engagement_counts(
                            aria_label
                        )
                        if reactions_count is not None or comments_count is not None:
                            break

                    # Try text content as fallback
                    text = await element.inner_text()
                    if text:
                        reactions_count, comments_count = self._parse_engagement_counts(
                            text
                        )
                        if reactions_count is not None or comments_count is not None:
                            break

            # Try separate selectors for reactions and comments
            if reactions_count is None:
                reactions_count = await self._extract_single_count(
                    post_element,
                    [
                        '[aria-label*="reaction"]',
                        ".reactions-count",
                        '[data-test-id="reactions-count"]',
                    ],
                )

            if comments_count is None:
                comments_count = await self._extract_single_count(
                    post_element,
                    [
                        '[aria-label*="comment"]',
                        ".comments-count",
                        '[data-test-id="comments-count"]',
                    ],
                )

            if reactions_count is not None or comments_count is not None:
                self.logger.debug(
                    "Engagement counts parsed",
                    event_code=EventCodes.COUNTS_PARSED,
                    context={"reactions": reactions_count, "comments": comments_count},
                )

            return reactions_count, comments_count

        except Exception:
            return None, None

    async def _extract_single_count(
        self, post_element: ElementHandle, selectors: list[str]
    ) -> int | None:
        """Extract a single count using multiple selectors."""
        for selector in selectors:
            try:
                element = await post_element.query_selector(selector)
                if element:
                    aria_label = await element.get_attribute("aria-label")
                    if aria_label:
                        count = self._parse_single_count(aria_label)
                        if count is not None:
                            return count

                    text = await element.inner_text()
                    if text:
                        count = self._parse_single_count(text)
                        if count is not None:
                            return count
            except Exception:
                continue

        return None

    def _parse_engagement_counts(self, text: str) -> tuple[int | None, int | None]:
        """Parse engagement counts from text like '120 reactions • 45 comments'."""
        reactions_count = None
        comments_count = None

        # Look for patterns like "X reactions" and "Y comments"
        reactions_match = re.search(
            r"(\d+(?:,\d+)*)\s+(?:reaction|like)", text, re.IGNORECASE
        )
        if reactions_match:
            reactions_count = self._normalize_count(reactions_match.group(1))

        comments_match = re.search(r"(\d+(?:,\d+)*)\s+comment", text, re.IGNORECASE)
        if comments_match:
            comments_count = self._normalize_count(comments_match.group(1))

        return reactions_count, comments_count

    def _parse_single_count(self, text: str) -> int | None:
        """Parse a single count from text."""
        # Extract first number found
        match = self.count_pattern.search(text)
        if match:
            return self._normalize_count(match.group(1))
        return None

    def _normalize_count(self, count_str: str) -> int:
        """Normalize count string to integer (handle commas, etc.)."""
        try:
            # Remove commas and convert to int
            return int(count_str.replace(",", ""))
        except (ValueError, AttributeError):
            return 0
        # except (ValueError, AttributeError):
        #     return 0
