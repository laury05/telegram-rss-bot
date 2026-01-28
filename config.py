import os
from dotenv import load_dotenv

load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]

# RSS configuration
UPDATE_INTERVAL_MINUTES = 10
MAX_POSTS_PER_FEED = 5
DATE_FORMAT = "%d.%m.%Y %H:%M"

# Database
DATABASE_NAME = "rss_bot.db"

# Limits
MAX_FEEDS_PER_USER = 25
