# ==============================================================================
# File: news_client.py
# NEW FILE: Fetches financial news headlines via RSS.
# ==============================================================================
import asyncio
import aiohttp
import feedparser


class FinancialNewsClient:
    """Simple RSS-based news fetcher."""

    def __init__(self, data_queue):
        self._queue = data_queue
        self._feeds = [
            "https://feeds.marketwatch.com/marketwatch/topstories/",
            "https://finance.yahoo.com/rss/topstories",
        ]
        self._seen_links = set()
        print("Financial News client initialized.")

    async def poll(self, interval=300):
        """Periodically fetches RSS feeds and posts new articles."""
        while True:
            for url in self._feeds:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as resp:
                            text = await resp.text()
                    feed = feedparser.parse(text)
                    for entry in feed.entries:
                        link = entry.get("link")
                        if link in self._seen_links:
                            continue
                        self._seen_links.add(link)
                        title = entry.get("title", "")
                        summary = entry.get("summary", "")
                        content = f"{title}. {summary}"
                        await self._queue.put({"type": "news_post", "text": content})
                except Exception as e:
                    print(f"NEWS_CLIENT_ERROR: {e}")
            await asyncio.sleep(interval)
