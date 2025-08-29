"""
DOM helpers that encapsulate common Playwright patterns.
These are used by new *v2 functions* without touching existing code.
"""
from typing import Optional, Sequence, Any
from .logging import logger

try:
    from playwright.async_api import Page, Locator
except Exception:  # pragma: no cover
    Page = Any
    Locator = Any

async def click_human_like(page: "Page", locator_or_selector: Any, *, delay_ms: int = 60, timeout: Optional[float] = None) -> None:
    """
    Click with a short delay to mimic human behavior. Keeps defaults minimal.
    - If locator passed: uses locator.click
    - If string passed: uses page.click
    """
    if hasattr(locator_or_selector, "click"):
        await locator_or_selector.click(delay=delay_ms, timeout=timeout)
    else:
        await page.click(locator_or_selector, delay=delay_ms, timeout=timeout)

async def find_element_with_fallbacks(page: "Page", selectors: Sequence[str], *, timeout: Optional[float] = None) -> Optional["Locator"]:
    """
    Try a list of selectors in order – returns the first that resolves, else None.
    Does NOT raise to keep parity with many existing helpers.
    """
    for sel in selectors:
        try:
            loc = page.locator(sel)
            # Use a very short wait if timeout provided, else rely on existing waits outside.
            if timeout:
                await loc.wait_for(state="visible", timeout=timeout)
            return loc
        except Exception as e:
            logger.debug(f"Selector failed: {sel} ({e})")
    return None

__all__ = ["click_human_like", "find_element_with_fallbacks"]
