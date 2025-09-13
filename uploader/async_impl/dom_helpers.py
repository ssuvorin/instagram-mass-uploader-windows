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
            # Support XPath selectors by prefixing with "xpath="
            formatted = f"xpath={sel}" if isinstance(sel, str) and sel.startswith('//') else sel
            loc = page.locator(formatted).first()
            # Prefer returning only when element is actually visible
            wait_timeout = timeout if timeout is not None else 800  # short per-selector wait when not provided
            try:
                await loc.wait_for(state="visible", timeout=wait_timeout)
                return loc
            except Exception as wait_err:
                # If visible wait failed, try a quick attached check before skipping
                try:
                    await loc.wait_for(state="attached", timeout=200)
                    # If attached, attempt a quick visibility probe
                    if await loc.is_visible():
                        return loc
                except Exception:
                    pass
                logger.debug(f"Selector not visible yet, skipping: {formatted} ({wait_err})")
                continue
        except Exception as e:
            logger.debug(f"Selector failed: {sel} ({e})")
            continue
    return None

__all__ = ["click_human_like", "find_element_with_fallbacks"]
