# src/li_extractor/output.py
"""Output file generation and validation."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .logging_ import EventCodes, StructuredLogger
from .models import LinkedInPost, LinkedInPostsExtraction


class OutputManager:
    """Manage output file generation and validation."""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger

    def write_results(
        self,
        posts_data: list[dict[str, Any]],
        profile_url: str,
        output_path: Path,
        extraction_duration: float | None = None,
        reason: str | None = None,
    ) -> None:
        """Write extraction results to JSON file."""
        try:
            self.logger.info(
                "Starting output generation",
                event_code=EventCodes.WRITE_STARTED,
                context={
                    "output_path": str(output_path),
                    "posts_count": len(posts_data),
                },
            )

            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Validate individual posts
            validated_posts = []
            validation_errors = 0

            for i, post_data in enumerate(posts_data):
                try:
                    post = LinkedInPost(**post_data)
                    validated_posts.append(post)
                except ValidationError as e:
                    validation_errors += 1
                    self.logger.warning(
                        f"Post validation failed for post {i+1}",
                        event_code=EventCodes.SCHEMA_VALIDATION_ERROR,
                        context={
                            "post_index": i + 1,
                            "validation_errors": str(e)[:500],
                        },
                    )

            # Create extraction result
            extraction_result = LinkedInPostsExtraction(
                profile_url=profile_url,
                fetched_at=datetime.now(timezone.utc),
                total_posts=len(validated_posts),
                posts=validated_posts,
                extraction_duration_seconds=extraction_duration,
                reason=reason,
            )

            # Write to file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    extraction_result.dict(),
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=self._json_serializer,
                )

            self.logger.info(
                "Output written successfully",
                event_code=EventCodes.WRITE_OK,
                context={
                    "output_path": str(output_path),
                    "posts_written": len(validated_posts),
                    "validation_errors": validation_errors,
                    "file_size_bytes": output_path.stat().st_size,
                },
            )

        except Exception as e:
            self.logger.error(
                f"Failed to write output: {e}",
                event_code=EventCodes.WRITE_FAILED,
                context={"output_path": str(output_path), "error": str(e)[:500]},
                exc_info=True,
            )

    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for datetime and other objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def export_schema(self, schema_path: Path) -> bool:
        """Export JSON schema to file."""
        try:
            schema = LinkedInPostsExtraction.get_json_schema()
            schema_path.parent.mkdir(parents=True, exist_ok=True)

            with open(schema_path, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2, ensure_ascii=False)

            self.logger.info(
                "JSON schema exported", context={"schema_path": str(schema_path)}
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to export schema: {e}",
                context={"schema_path": str(schema_path)},
                exc_info=True,
            )
            # return False
            #     exc_info=True,
            # )
            return False
