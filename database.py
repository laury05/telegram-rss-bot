import sqlite3
import logging
from datetime import datetime
from config import DATABASE_NAME

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Table for RSS feeds
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rss_feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                name TEXT NOT NULL,
                last_checked TIMESTAMP,
                last_guid TEXT,
                is_active INTEGER DEFAULT 1,
                UNIQUE(user_id, url)
            )
        ''')
        
        # Table for user settings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                language TEXT DEFAULT 'en',
                update_interval INTEGER DEFAULT 10,
                send_as_individual INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table for post history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feed_id INTEGER,
                guid TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (feed_id) REFERENCES rss_feeds (id)
            )
        ''')
        
        self.conn.commit()
    
    def add_feed(self, user_id, url, name):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO rss_feeds (user_id, url, name, last_checked)
                VALUES (?, ?, ?, ?)
            ''', (user_id, url, name, datetime.now()))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
    
    def get_user_feeds(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, url, name, last_checked, is_active 
            FROM rss_feeds 
            WHERE user_id = ? AND is_active = 1
        ''', (user_id,))
        return cursor.fetchall()
    
    def get_all_active_feeds(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, user_id, url, name, last_checked, last_guid 
            FROM rss_feeds 
            WHERE is_active = 1
        ''')
        return cursor.fetchall()
    
    def delete_feed(self, user_id, feed_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            DELETE FROM rss_feeds 
            WHERE id = ? AND user_id = ?
        ''', (feed_id, user_id))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def update_feed_last_checked(self, feed_id, last_guid):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE rss_feeds 
            SET last_checked = ?, last_guid = ?
            WHERE id = ?
        ''', (datetime.now(), last_guid, feed_id))
        self.conn.commit()
    
    def mark_post_as_sent(self, feed_id, guid):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO sent_posts (feed_id, guid)
            VALUES (?, ?)
        ''', (feed_id, guid))
        self.conn.commit()
    
    def is_post_sent(self, feed_id, guid):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 1 FROM sent_posts 
            WHERE feed_id = ? AND guid = ?
            LIMIT 1
        ''', (feed_id, guid))
        return cursor.fetchone() is not None
    
    def get_user_settings(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM user_settings 
            WHERE user_id = ?
        ''', (user_id,))
        row = cursor.fetchone()
        
        if not row:
            # Create default settings
            cursor.execute('''
                INSERT INTO user_settings (user_id)
                VALUES (?)
            ''', (user_id,))
            self.conn.commit()
            return (user_id, 'en', 10, 1, datetime.now())
        
        return row
    
    def update_user_settings(self, user_id, **kwargs):
        cursor = self.conn.cursor()
        
        if 'language' in kwargs:
            cursor.execute('''
                UPDATE user_settings 
                SET language = ?
                WHERE user_id = ?
            ''', (kwargs['language'], user_id))
        
        if 'update_interval' in kwargs:
            cursor.execute('''
                UPDATE user_settings 
                SET update_interval = ?
                WHERE user_id = ?
            ''', (kwargs['update_interval'], user_id))
        
        if 'send_as_individual' in kwargs:
            cursor.execute('''
                UPDATE user_settings 
                SET send_as_individual = ?
                WHERE user_id = ?
            ''', (kwargs['send_as_individual'], user_id))
        
        self.conn.commit()
    
    def close(self):
        self.conn.close()

# Global database instance
db = Database()