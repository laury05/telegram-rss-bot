import feedparser
import aiohttp
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from config import MAX_POSTS_PER_FEED

logger = logging.getLogger(__name__)

class RSSParser:
    def __init__(self):
        self.session = None
    
    async def create_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        if self.session:
            await self.session.close()
    
    async def fetch_feed(self, url: str) -> Dict[str, Any]:
        """Fetch RSS feed content"""
        try:
            await self.create_session()
            
            async with self.session.get(url, timeout=30) as response:
                if response.status == 200:
                    content = await response.text()
                    feed = feedparser.parse(content)
                    
                    if feed.bozo:
                        logger.warning(f"Error parsing feed {url}: {feed.bozo_exception}")
                    
                    return {
                        'title': feed.feed.get('title', 'No title'),
                        'link': feed.feed.get('link', ''),
                        'description': feed.feed.get('description', ''),
                        'entries': feed.entries[:MAX_POSTS_PER_FEED],
                        'status': 'success'
                    }
                else:
                    return {'status': 'error', 'message': f'HTTP Error: {response.status}'}
        
        except Exception as e:
            logger.error(f"Error fetching feed {url}: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def parse_entry(self, entry) -> Dict[str, Any]:
        """Parse an RSS entry"""
        published = entry.get('published_parsed', entry.get('updated_parsed', None))
        
        return {
            'title': entry.get('title', 'No title'),
            'link': entry.get('link', ''),
            'description': entry.get('description', ''),
            'summary': entry.get('summary', ''),
            'published': datetime(*published[:6]) if published else datetime.now(),
            'guid': entry.get('id', entry.get('link', '')),
            'author': entry.get('author', ''),
            'categories': entry.get('tags', []),
            'media_content': entry.get('media_content', [])
        }
    
    async def check_new_posts(self, feed_id: int, url: str, last_guid: str = None) -> List[Dict[str, Any]]:
        """Check for new posts in an RSS feed"""
        feed_data = await self.fetch_feed(url)
        
        if feed_data['status'] != 'success':
            return []
        
        new_posts = []
        
        for entry in feed_data['entries']:
            post = self.parse_entry(entry)
            
            # If we have a last_guid, check if the post is new
            if last_guid:
                if post['guid'] == last_guid:
                    break
            
            new_posts.append(post)
        
        return new_posts

# Global RSS parser instance
rss_parser = RSSParser()