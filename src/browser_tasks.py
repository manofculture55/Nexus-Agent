"""
browser_tasks.py — NEXUS Browser Automation
Provides browser automation using Selenium with the Microsoft Edge WebDriver
(msedgedriver.exe shipped in src/). Supports opening URLs, searching the web,
and scraping visible text from web pages.

Phase 23 of the NEXUS implementation plan.

NOTE: This module requires the 'selenium' package and a compatible
msedgedriver.exe. If the Edge version changes, download a matching
driver from https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
"""

import os
import re
import time

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EDGE_DRIVER_PATH = os.path.join(os.path.dirname(__file__), "msedgedriver.exe")


# ---------------------------------------------------------------------------
# Lazy Selenium import with clear error message
# ---------------------------------------------------------------------------
def _check_selenium():
    """
    Verify that selenium is installed and the Edge driver exists.
    Returns (webdriver, Service) or raises an informative error.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.service import Service
        from selenium.webdriver.edge.options import Options
    except ImportError:
        raise RuntimeError(
            "Selenium is not installed. Run: pip install selenium"
        )

    if not os.path.isfile(EDGE_DRIVER_PATH):
        raise FileNotFoundError(
            f"Edge WebDriver not found at: {EDGE_DRIVER_PATH}\n"
            "Download the correct version from:\n"
            "https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/"
        )

    return webdriver, Service, Options


# ---------------------------------------------------------------------------
# Internal helper — create an Edge browser instance
# ---------------------------------------------------------------------------
def _create_browser(headless=False):
    """
    Create and return a Selenium Edge browser instance.

    Args:
        headless: If True, run browser in the background (no visible window).
                  If False (default), open a visible browser window.

    Returns:
        A selenium.webdriver.Edge instance.
    """
    webdriver, Service, Options = _check_selenium()

    options = Options()
    if headless:
        options.add_argument("--headless=new")

    # Suppress unnecessary logging
    options.add_argument("--log-level=3")
    options.add_argument("--disable-logging")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    service = Service(executable_path=EDGE_DRIVER_PATH)

    try:
        browser = webdriver.Edge(service=service, options=options)
        return browser
    except Exception as e:
        error_msg = str(e)
        if "This version of Microsoft Edge WebDriver" in error_msg:
            raise RuntimeError(
                "Edge WebDriver version mismatch!\n"
                "Your msedgedriver.exe version doesn't match your installed Edge browser.\n"
                "Download the matching version from:\n"
                "https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/\n"
                f"\nOriginal error: {error_msg}"
            )
        raise RuntimeError(f"Failed to start Edge browser: {error_msg}")


# ---------------------------------------------------------------------------
# Public API — open_browser
# ---------------------------------------------------------------------------
def open_browser(url):
    """
    Open Microsoft Edge and navigate to the given URL.

    Args:
        url: The URL to open (e.g. "https://google.com").

    Returns:
        A status message string.
    """
    # Normalise the URL — add https:// if missing
    url = _normalise_url(url)

    try:
        browser = _create_browser(headless=False)
        browser.get(url)
        title = browser.title or url
        return f"Opened Edge browser: {title}\nURL: {url}"
    except Exception as e:
        return f"Could not open browser: {e}"


# ---------------------------------------------------------------------------
# Public API — search_web
# ---------------------------------------------------------------------------
def search_web(query):
    """
    Open Edge and perform a web search using Bing.

    Args:
        query: The search query string.

    Returns:
        A status message string.
    """
    if not query or not query.strip():
        return "Please provide a search query."

    # Use Bing (works offline-friendly with Edge, no consent screens)
    search_url = f"https://www.bing.com/search?q={_url_encode(query)}"

    try:
        browser = _create_browser(headless=False)
        browser.get(search_url)
        return f"Searching the web for: \"{query}\"\nOpened in Edge browser."
    except Exception as e:
        return f"Could not perform web search: {e}"


# ---------------------------------------------------------------------------
# Public API — scrape_text
# ---------------------------------------------------------------------------
def scrape_text(url):
    """
    Open a web page in headless Edge and extract the visible text content.
    Useful for reading articles, documentation, or simple web pages.

    Args:
        url: The URL to scrape.

    Returns:
        The extracted text (truncated to ~3000 chars) or an error message.
    """
    url = _normalise_url(url)

    try:
        browser = _create_browser(headless=True)
        browser.get(url)

        # Wait briefly for page to load
        time.sleep(2)

        # Get the page text (body only, strips scripts/styles)
        text = browser.find_element("tag name", "body").text
        browser.quit()

        if not text or not text.strip():
            return f"No readable text found on: {url}"

        # Clean up excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text.strip())

        # Truncate if very long
        if len(text) > 3000:
            text = text[:3000] + "\n\n[... content truncated — page too long ...]"

        return f"Content from: {url}\n{'─' * 40}\n{text}"

    except Exception as e:
        return f"Could not scrape page: {e}"
    finally:
        # Ensure browser is closed even on error
        try:
            browser.quit()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _normalise_url(url):
    """Add https:// prefix if the URL doesn't have a scheme."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _url_encode(text):
    """Simple URL-encoding for search queries."""
    try:
        from urllib.parse import quote_plus
        return quote_plus(text)
    except ImportError:
        # Fallback — basic encoding
        return text.replace(" ", "+").replace("&", "%26")
