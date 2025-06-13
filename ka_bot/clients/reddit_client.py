# ==============================================================================
# File: reddit_client.py
# ==============================================================================
import asyncio

import asyncpraw

class RedditClient:
    def __init__(self, data_queue, config, db_manager, subreddits):
        self._config, self._data_queue, self._db, self.subreddits_to_monitor = config, data_queue, db_manager, subreddits
        self.reddit = asyncpraw.Reddit(client_id=config.REDDIT_CLIENT_ID, client_secret=config.REDDIT_CLIENT_SECRET, user_agent=config.REDDIT_USER_AGENT)
        print("Reddit client initialized.")

    async def stream_comments(self):
        subreddits_str = "+".join(self.subreddits_to_monitor)
        print(f"Starting to stream comments from subreddits: {subreddits_str}")
        try:
            subreddit = await self.reddit.subreddit(subreddits_str)
            async for comment in subreddit.stream.comments(skip_existing=True):
                author, subreddit_name, content = (comment.author.name if comment.author else "[deleted]"), comment.subreddit.display_name, comment.body
                self._db.execute_query("INSERT INTO social_posts (source, content, author, subreddit) VALUES (%s, %s, %s, %s);", ('reddit', content, author, subreddit_name))
                post_id = self._db.execute_query("SELECT lastval();", fetch='one')[0]
                if post_id: await self._data_queue.put({'type': 'social_post', 'text': content, 'post_id': post_id})
        except Exception as e:
            print(f"Error in Reddit stream: {e}. Restarting..."); await asyncio.sleep(30); await self.stream_comments()