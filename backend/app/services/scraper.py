import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext
from app.core.config import settings


async def fetch_tweet_content(url: str) -> dict:
    """
    Uses Playwright to:
    1. Navigate to tweet URL
    2. Wait for content to load
    3. Extract tweet text
    4. If part of thread, extract thread context
    5. Return structured content

    Returns:
        {
            "full_content": str,
            "thread_content": str | None,
            "author": str,
            "success": bool,
            "error": str | None
        }
    """
    result = {
        "full_content": None,
        "thread_content": None,
        "author": None,
        "success": False,
        "error": None
    }

    async with async_playwright() as p:
        try:
            browser_args = {
                "headless": settings.PLAYWRIGHT_HEADLESS
            }

            # Use persistent context if Chrome user data dir is specified
            if settings.CHROME_USER_DATA_DIR:
                context = await p.chromium.launch_persistent_context(
                    settings.CHROME_USER_DATA_DIR,
                    **browser_args
                )
                page = await context.new_page()
            else:
                browser = await p.chromium.launch(**browser_args)
                context = await browser.new_context()
                page = await context.new_page()

            # Navigate to the tweet
            await page.goto(url, wait_until="networkidle", timeout=30000)

            # Wait for tweet content to load
            await page.wait_for_selector('[data-testid="tweetText"]', timeout=10000)

            # Extract the main tweet author
            author_element = await page.query_selector('[data-testid="User-Name"] a')
            if author_element:
                author_href = await author_element.get_attribute("href")
                result["author"] = author_href.strip("/") if author_href else None

            # Extract all tweet texts on the page (for thread context)
            tweet_elements = await page.query_selector_all('[data-testid="tweetText"]')

            all_tweets = []
            for element in tweet_elements:
                text = await element.inner_text()
                if text:
                    all_tweets.append(text.strip())

            if all_tweets:
                # First tweet is the main content
                result["full_content"] = all_tweets[0]

                # If there are more tweets, they're thread context
                if len(all_tweets) > 1:
                    result["thread_content"] = "\n\n---\n\n".join(all_tweets[1:])

                result["success"] = True
            else:
                result["error"] = "No tweet content found"

            await context.close()
            if not settings.CHROME_USER_DATA_DIR:
                await browser.close()

        except Exception as e:
            result["error"] = str(e)

    return result


async def fetch_with_retry(url: str, max_attempts: int = 3) -> dict:
    """
    Fetch tweet content with retry logic.

    Args:
        url: Tweet URL to fetch
        max_attempts: Maximum number of retry attempts

    Returns:
        Result dict from fetch_tweet_content
    """
    last_result = None

    for attempt in range(max_attempts):
        result = await fetch_tweet_content(url)

        if result["success"]:
            return result

        last_result = result

        # Wait before retry (exponential backoff)
        if attempt < max_attempts - 1:
            await asyncio.sleep(2 ** attempt)

    return last_result or {"success": False, "error": "Max retries exceeded"}
