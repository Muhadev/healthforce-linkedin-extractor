# src/li_extractor/cli.py
"""Command-line interface for LinkedIn posts extractor."""

import asyncio
import sys
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .browser import BrowserManager
from .logging_ import EventCodes, StructuredLogger
from .navigator import LinkedInNavigator
from .output import OutputManager

app = typer.Typer(help="LinkedIn Posts Extractor - Enterprise-grade extraction tool")
console = Console()


@app.command()
def extract(
    profile_url: str = typer.Option(
        ..., "--profile-url", help="LinkedIn profile URL to extract posts from"
    ),
    min_posts: int = typer.Option(
        10, "--min-posts", help="Minimum number of posts to extract"
    ),
    max_seconds: int = typer.Option(
        60, "--max-seconds", help="Maximum extraction time in seconds"
    ),
    out_dir: Path = typer.Option(
        Path("out"), "--out-dir", help="Output directory path"
    ),
    storage_state: Path = typer.Option(
        Path("out/session/storage.json"),
        "--storage-state",
        help="Playwright storage state path",
    ),
    headless: bool = typer.Option(
        False, "--headless/--headful", help="Run browser in headless mode"
    ),
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level"),
) -> None:
    """Extract recent posts from a LinkedIn profile."""

    # Setup paths
    out_dir.mkdir(parents=True, exist_ok=True)
    log_file = out_dir / "run.log"
    output_file = out_dir / "li_posts.json"

    # Initialize logger
    logger = StructuredLogger("li_extractor", log_file, log_level)

    console.print("Starting LinkedIn Posts Extractor", style="bold green")
    console.print(f"Profile: {profile_url}")
    console.print(f"Target: {min_posts} posts (max {max_seconds}s)")
    console.print(f"Output: {output_file}")
    console.print(f"Logs: {log_file}")

    try:
        # Run the extraction
        result = asyncio.run(
            run_extraction(
                profile_url=profile_url,
                min_posts=min_posts,
                max_seconds=max_seconds,
                output_file=output_file,
                storage_state=storage_state,
                headless=headless,
                logger=logger,
            )
        )

        if result:
            console.print("Extraction completed successfully!", style="bold green")
            sys.exit(0)
        else:
            console.print("Extraction failed!", style="bold red")
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\nExtraction cancelled by user", style="yellow")
        logger.info("Extraction cancelled by user")
        sys.exit(1)
    except Exception as e:
        console.print(f"Fatal error: {e}", style="bold red")
        logger.error(
            f"Fatal error in CLI: {e}",
            event_code=EventCodes.UNCAUGHT_EXCEPTION,
            exc_info=True,
        )
        sys.exit(1)


async def run_extraction(
    profile_url: str,
    min_posts: int,
    max_seconds: int,
    output_file: Path,
    storage_state: Path,
    headless: bool,
    logger: StructuredLogger,
) -> bool:
    """Run the complete extraction process."""

    start_time = time.time()
    browser_manager = None

    try:
        logger.info(
            "Starting LinkedIn posts extraction",
            context={
                "profile_url": profile_url,
                "min_posts": min_posts,
                "max_seconds": max_seconds,
                "headless": headless,
                "trace_id": logger.trace_id,
            },
        )

        # Initialize components
        browser_manager = BrowserManager(logger)
        navigator = LinkedInNavigator(logger)
        output_manager = OutputManager(logger)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:

            # Start browser
            task = progress.add_task("Starting browser...", total=None)
            page = await browser_manager.start_browser(
                storage_state_path=storage_state, headless=headless
            )

            # Navigate to posts
            progress.update(task, description="Navigating to posts section...")
            navigation_success = await navigator.navigate_to_posts(page, profile_url)

            if not navigation_success:
                logger.error("Failed to navigate to posts section")
                return False

            # Load posts
            progress.update(task, description="Loading posts...")
            post_elements = await navigator.load_posts(page, min_posts, max_seconds)

            if not post_elements:
                logger.warning("No posts found")
                # Still create output file with empty results
                success = output_manager.write_results(
                    posts_data=[],
                    profile_url=profile_url,
                    output_path=output_file,
                    extraction_duration=time.time() - start_time,
                    reason="no_posts_found",
                )
                return success

            # Extract post data
            progress.update(
                task, description=f"Extracting data from {len(post_elements)} posts..."
            )
            posts_data = await navigator.extract_posts_data(post_elements, page)

            # Write results
            progress.update(task, description="Writing results...")

            extraction_duration = time.time() - start_time
            reason = "completed"

            if len(posts_data) < min_posts and extraction_duration >= max_seconds:
                reason = "timeout"
            elif len(posts_data) >= min_posts:
                reason = "min_posts_met"

            success = output_manager.write_results(
                posts_data=posts_data,
                profile_url=profile_url,
                output_path=output_file,
                extraction_duration=extraction_duration,
                reason=reason,
            )

            if not success:
                logger.error("Failed to write output file")
                return False

            progress.update(task, description="Complete!")

        # Final metrics
        final_metrics = {
            "posts_extracted": len(posts_data),
            "extraction_duration_seconds": extraction_duration,
            "reason": reason,
            "min_posts_target": min_posts,
            "max_seconds_limit": max_seconds,
        }

        if hasattr(navigator, "action_tracker"):
            final_metrics.update(navigator.action_tracker.get_metrics())

        logger.info("Extraction completed successfully", context=final_metrics)

        return True

    except Exception as e:
        logger.error(
            f"Extraction failed: {e}",
            event_code=EventCodes.UNCAUGHT_EXCEPTION,
            exc_info=True,
        )
        return False

    finally:
        if browser_manager:
            try:
                await browser_manager.close()
            except Exception as e:
                logger.error(f"Error closing browser: {e}")


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
