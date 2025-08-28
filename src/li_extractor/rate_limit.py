# src/li_extractor/rate_limit.py
"""Rate limiting utilities with jitter and action tracking."""

import asyncio
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

from .logging_ import StructuredLogger

T = TypeVar("T")


class ActionTracker:
    """Tracks action timing and maintains rate limiting."""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.action_times: list[float] = []
        self.total_actions = 0
        self.total_duration = 0.0

    async def execute_action(
        self,
        action: Callable[..., Any],
        min_ms: int = 100,
        max_ms: int = 400,
        wait_for_network: bool = False,
        page: Any = None,
    ) -> Any:
        """Execute action with timing and rate limiting."""
        start_time = time.time()

        try:
            # Execute the action
            result = await action() if asyncio.iscoroutinefunction(action) else action()

            # Wait for network idle if requested
            if wait_for_network and page:
                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    # Network idle timeout is not critical
                    pass

            # Rate limiting with jitter
            jitter_ms = random.randint(min_ms, max_ms)
            await asyncio.sleep(jitter_ms / 1000.0)

            # Track timing
            duration = time.time() - start_time
            self.action_times.append(duration)
            self.total_actions += 1
            self.total_duration += duration

            # Keep only last 10 actions for rolling average
            if len(self.action_times) > 10:
                self.action_times.pop(0)

            avg_duration = sum(self.action_times) / len(self.action_times)

            self.logger.debug(
                f"Action completed: {action.__name__}",
                metrics={
                    "action_name": action.__name__,
                    "duration_ms": duration * 1000,
                    "jitter_ms": jitter_ms,
                    "avg_duration_ms": avg_duration * 1000,
                    "total_actions": self.total_actions,
                },
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                f"Action failed: {action.__name__}",
                context={
                    "action_name": action.__name__,
                    "duration_ms": duration * 1000,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    def get_metrics(self) -> dict[str, float]:
        """Get current action metrics."""
        if not self.action_times:
            return {
                "total_actions": 0,
                "avg_action_duration_ms": 0.0,
                "actions_per_second": 0.0,
            }

        avg_duration = sum(self.action_times) / len(self.action_times)
        actions_per_second = 1.0 / avg_duration if avg_duration > 0 else 0.0

        return {
            "total_actions": self.total_actions,
            "avg_action_duration_ms": avg_duration * 1000,
            "actions_per_second": actions_per_second,
        }


async def sleep_with_jitter(min_ms: int = 100, max_ms: int = 400) -> None:
    """Sleep with random jitter."""
    jitter_ms = random.randint(min_ms, max_ms)
    await asyncio.sleep(jitter_ms / 1000.0)
