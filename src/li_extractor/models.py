# src/li_extractor/models.py
"""Pydantic models for LinkedIn posts data with JSON Schema export."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, validator


class LinkedInPost(BaseModel):
    """Individual LinkedIn post model."""

    post_id: str = Field(..., description="Unique post identifier")
    author_name: str | None = Field(None, description="Post author name")
    posted_at: datetime | None = Field(None, description="Post timestamp in UTC")
    text: str | None = Field(None, description="Post text content")
    hashtags: list[str] = Field(default_factory=list, description="Extracted hashtags")
    links: list[str] = Field(default_factory=list, description="External links")
    reactions_count: int | None = Field(None, ge=0, description="Number of reactions")
    comments_count: int | None = Field(None, ge=0, description="Number of comments")

    @validator("hashtags", pre=True)
    def normalize_hashtags(cls, v: Any) -> list[str]:
        """Normalize hashtags to lowercase unique list."""
        if not v:
            return []
        if isinstance(v, str):
            v = [v]
        return sorted({tag.lower().strip("#") for tag in v if tag})

    @validator("links", pre=True)
    def validate_links(cls, v: Any) -> list[str]:
        """Validate and deduplicate links."""
        if not v:
            return []
        if isinstance(v, str):
            v = [v]

        unique_links = []
        seen = set()

        for link in v:
            if link and link not in seen:
                # Basic URL validation (consider using more robust validation if needed)
                if link.startswith(("http://", "https://")):
                    unique_links.append(link)
                    seen.add(link)

        return unique_links


class LinkedInPostsExtraction(BaseModel):
    """Complete LinkedIn posts extraction result."""

    profile_url: str = Field(..., description="Source LinkedIn profile URL")
    fetched_at: datetime = Field(..., description="Extraction timestamp in UTC")
    total_posts: int = Field(..., ge=0, description="Total number of posts extracted")
    posts: list[LinkedInPost] = Field(
        default_factory=list, description="Extracted posts"
    )

    extraction_duration_seconds: float | None = Field(None, ge=0)
    reason: str | None = Field(
        None, description="Reason for stopping (timeout, min_met, etc.)"
    )

    @validator("total_posts", always=True)
    def sync_total_posts(cls, v: int, values: dict[str, Any]) -> int:
        """Ensure total_posts matches actual posts count."""
        posts = values.get("posts", [])
        return len(posts) if posts else v

    @classmethod
    def get_json_schema(cls) -> dict[str, Any]:
        """Get JSON Schema for the model."""
        return cls.schema()


class ExtractionMetrics(BaseModel):
    """Metrics collected during extraction."""

    actions_performed: int = 0
    average_action_duration_ms: float = 0.0
    scrolls_performed: int = 0
    posts_found: int = 0
    posts_parsed: int = 0
    parse_errors: int = 0
    network_wait_time_ms: float = 0.0
