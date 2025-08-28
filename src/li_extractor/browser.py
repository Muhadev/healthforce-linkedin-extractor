# src/li_extractor/browser.py
"""Playwright browser management with session persistence."""

from pathlib import Path

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from .logging_ import EventCodes, StructuredLogger


class BrowserManager:
    """Manages Playwright browser lifecycle and session state."""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def start_browser(
        self, storage_state_path: Path, headless: bool = False, timeout: int = 30000
    ) -> Page:
        """Start browser with session management."""
        self.playwright = await async_playwright().start()

        # Launch browser
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
            ],
        )

        # Create context with or without storage state
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        # Try to load existing storage state
        if storage_state_path.exists():
            try:
                context_options["storage_state"] = str(storage_state_path)
                self.context = await self.browser.new_context(
                    storage_state=str(storage_state_path)
                )

                # Test if session is still valid
                test_page = await self.context.new_page()
                await test_page.goto("https://www.linkedin.com/feed/", timeout=timeout)

                # Check if we're logged in (look for feed or profile elements)
                try:
                    await test_page.wait_for_selector(
                        'nav[aria-label="Primary Navigation"], .global-nav__me',
                        timeout=5000,
                    )
                    await test_page.close()

                    self.logger.info(
                        "Existing session loaded successfully",
                        event_code=EventCodes.SESSION_REUSED,
                        context={"storage_path": str(storage_state_path)},
                    )

                except Exception:
                    # Session is invalid, need to re-authenticate
                    await test_page.close()
                    await self.context.close()
                    raise ValueError("Session expired") from None

            except Exception as e:
                self.logger.warning(
                    f"Storage state invalid: {e}",
                    event_code=EventCodes.STORAGE_INVALID,
                    context={"storage_path": str(storage_state_path)},
                )

                # Remove invalid storage state
                if storage_state_path.exists():
                    storage_state_path.unlink()

                # Create new context without storage state
                self.context = await self.browser.new_context()
                await self._handle_login_required(storage_state_path)
        else:
            # No existing session, create new context
            self.context = await self.browser.new_context()
            await self._handle_login_required(storage_state_path)

        # Create the main page
        if self.context is not None:
            self.page = await self.context.new_page()
        else:
            raise RuntimeError("Browser context is not initialized")

        # Set default timeouts
        if self.page is not None:
            self.page.set_default_timeout(timeout)
            self.page.set_default_navigation_timeout(timeout)

        return self.page

    async def _handle_login_required(self, storage_state_path: Path) -> None:
        """Handle manual login and save session."""
        self.logger.info(
            "Manual login required - opening browser",
            event_code=EventCodes.LOGIN_REQUIRED,
        )

        # Create login page
        if self.context is not None:
            login_page = await self.context.new_page()
        else:
            raise RuntimeError("Browser context is not initialized")

        await login_page.goto("https://www.linkedin.com/login")

        # Wait for user to complete login
        self.logger.info("Please complete LinkedIn login in the browser window...")

        try:
            # Wait for successful login (presence of feed or profile navigation)
            await login_page.wait_for_selector(
                'nav[aria-label="Primary Navigation"], .global-nav__me, #global-nav',
                timeout=300000,  # 5 minutes
            )

            # Save storage state
            if self.context is not None:
                storage_state_path.parent.mkdir(parents=True, exist_ok=True)
                await self.context.storage_state(path=str(storage_state_path))
            else:
                raise RuntimeError("Browser context is not initialized")

            self.logger.info(
                "Login successful - session saved",
                event_code=EventCodes.STORAGE_SAVED,
                context={"storage_path": str(storage_state_path)},
            )

        except Exception as e:
            self.logger.error(
                f"Login timeout or failed: {e}",
                event_code=EventCodes.UNCAUGHT_EXCEPTION,
                exc_info=True,
            )
            raise
        finally:
            await login_page.close()

    async def close(self) -> None:
        """Clean up browser resources."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            await self.playwright.stop()
            await self.playwright.stop()
