import logging
import asyncio
from datetime import datetime
# If you see 'Import "telegram" could not be resolved', install the package:
# pip install python-telegram-bot --upgrade
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

from config import BOT_TOKEN, ADMIN_IDS, UPDATE_INTERVAL_MINUTES, MAX_FEEDS_PER_USER
from database import db
from rss_parser import rss_parser

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Recommended RSS feeds
RECOMMENDED_FEEDS = [
    ("https://techcrunch.com/feed/", "TechCrunch"),
    ("https://www.coindesk.com/arc/outboundfeeds/rss/", "CoinDesk"),
    ("https://www.cnbc.com/id/100003114/device/rss/rss.html", "CNBC"),
    ("https://ai.googleblog.com/feeds/posts/default", "Google AI"),
    ("https://www.theverge.com/rss/index.xml", "The Verge"),
    ("https://consensys.net/blog/feed/", "Consensys Blog"),
    ("https://www.technologyreview.com/feed/", "MIT Tech Review"),
    ("https://krebsonsecurity.com/feed/", "Krebs Security"),
    ("https://defipulse.com/blog/feed/", "DeFi Pulse"),
    ("https://news.ycombinator.com/rss", "Hacker News")
]

# Text messages dictionary
TEXTS = {
    'en': {
        'start': '👋 Welcome to RSS News Bot!\n\nWith me you can:\n• Add RSS feeds\n• Receive new articles automatically\n• Manage your subscriptions\n\nUse /help for assistance.',
        'help': '''📖 **Available Commands**:
        
/addfeed <url> <name> - Add an RSS feed
/myfeeds - View your feeds
/recommended - View recommended feeds
/addrecommended - Add all recommended feeds
/deletefeed <id> - Delete a feed
/settings - Bot settings
/stop - Stop notifications
/start - Resume notifications
/stats - Statistics (admin)
        
**Example**: /addfeed https://example.com/rss TechNews''',
        'feed_added': '✅ RSS feed added successfully!',
        'feed_exists': '⚠️ This RSS feed is already added.',
        'feed_limit': f'⚠️ You have reached the maximum limit of {MAX_FEEDS_PER_USER} feeds.',
        'invalid_url': '❌ Invalid URL. Please enter a valid RSS URL.',
        'my_feeds': '📰 **Your RSS Feeds**:\n\n',
        'no_feeds': '📭 You have no RSS feeds yet.\nUse /addfeed to add one.',
        'feed_deleted': '✅ Feed deleted successfully!',
        'feed_not_found': '❌ Feed not found.',
        'settings': '⚙️ **Settings**:\n\n',
        'language': '🌍 Language:',
        'interval': '⏰ Check interval (minutes):',
        'send_method': '📨 Send method:',
        'individual': 'Individual messages',
        'digest': 'Daily digest',
        'stats': '📊 **Bot Statistics**:\n\n',
        'new_post': '📰 **{feed_name}**\n\n**{title}**\n\n{description}\n\n🔗 {link}',
        'checking_feeds': '🔍 Checking feeds for new articles...',
        'no_new_posts': '📭 No new articles.',
        'new_posts_found': '✅ {count} new articles found!',
        'error': '❌ An error occurred. Please try again.',
        'test_feed': '🔍 Testing feed...',
        'test_success': '✅ **Feed tested successfully!**',
        'test_error': '❌ Error:',
        'feed_title': 'Feed Title:',
        'feed_url': 'URL:',
        'feed_description': 'Description:',
        'available_posts': 'Available posts:',
        'last_posts': 'Last 3 posts:',
        'usage': 'Usage:',
        'test_feed_btn': '🔍 Test feed',
        'delete_feed_btn': '❌',
        'test_btn': '🔍 Test',
        'deleted_success': '✅ Feed deleted successfully!',
        'delete_error': '❌ Error deleting feed.',
        'not_found': '❌ Feed not found.',
        'admin_only': '❌ This command is for administrators only.',
        'total_feeds': 'Total feeds:',
        'total_users': 'Total users:',
        'total_posts_sent': 'Total posts sent:',
        'top_feeds': 'Top 5 feeds:',
        'never_checked': 'Never',
        'recommended_feeds': '⭐ **Recommended Feeds**:\n\nClick a button to add a recommended feed:\n\n',
        'recommended_added': '✅ Recommended feed "{feed_name}" added successfully!',
        'view_recommended': '⭐ View Recommended',
        'add_all_result': '✅ **Feed Addition Result**:\n\n',
        'added_feeds': '**Added ({count})**:\n',
        'existing_feeds': '\n**Already Exist ({count})**:\n',
        'welcome_feeds': '📰 **Latest Articles** from your feeds:\n\n',
        'keep_all': '✅ Keep All',
        'customize': '⚙️ Customize',
        'reset': '🔄 Reset'
    },
    'ro': {
        'start': '👋 Bun venit la RSS News Bot!\n\nCu mine poți:\n• Adăuga fluxuri RSS\n• Primești știri noi automat\n• Gestionezi abonamentele\n\nFolosește /help pentru ajutor.',
        'help': '''📖 **Comenzi disponibile**:
        
/addfeed <url> <nume> - Adaugă un flux RSS
/myfeeds - Vezi fluxurile tale
/recommended - Vezi fluxurile recomandate
/addrecommended - Adaugă toate fluxurile recomandate
/deletefeed <id> - Șterge un flux
/settings - Setări bot
/stop - Oprește notificările
/start - Repornește notificările
/stats - Statistici (admin)
        
**Exemplu**: /addfeed https://example.com/rss StiriIT''',
        'feed_added': '✅ Flux RSS adăugat cu succes!',
        'feed_exists': '⚠️ Acest flux RSS este deja adăugat.',
        'feed_limit': f'⚠️ Ai atins limita maximă de {MAX_FEEDS_PER_USER} fluxuri.',
        'invalid_url': '❌ URL invalid. Te rog introdu un URL RSS valid.',
        'my_feeds': '📰 **Fluxurile tale RSS**:\n\n',
        'no_feeds': '📭 Nu ai niciun flux RSS adăugat.\nFolosește /addfeed pentru a adăuga unul.',
        'feed_deleted': '✅ Flux șters cu succes!',
        'feed_not_found': '❌ Fluxul nu a fost găsit.',
        'settings': '⚙️ **Setări**:\n\n',
        'language': '🌍 Limbă:',
        'interval': '⏰ Interval verificare (minute):',
        'send_method': '📨 Metodă trimitere:',
        'individual': 'Mesaje individuale',
        'digest': 'Digest zilnic',
        'stats': '📊 **Statistici Bot**:\n\n',
        'new_post': '📰 **{feed_name}**\n\n**{title}**\n\n{description}\n\n🔗 {link}',
        'checking_feeds': '🔍 Verific fluxurile pentru știri noi...',
        'no_new_posts': '📭 Nu sunt știri noi.',
        'new_posts_found': '✅ {count} știri noi găsite!',
        'error': '❌ A apărut o eroare. Încearcă din nou.',
        'test_feed': '🔍 Testez fluxul...',
        'test_success': '✅ **Flux testat cu succes!**',
        'test_error': '❌ Eroare:',
        'feed_title': 'Titlu flux:',
        'feed_url': 'URL:',
        'feed_description': 'Descriere:',
        'available_posts': 'Postări disponibile:',
        'last_posts': 'Ultimele 3 postări:',
        'usage': 'Utilizare:',
        'test_feed_btn': '🔍 Testează fluxul',
        'delete_feed_btn': '❌',
        'test_btn': '🔍 Test',
        'deleted_success': '✅ Flux șters cu succes!',
        'delete_error': '❌ Eroare la ștergere.',
        'not_found': '❌ Fluxul nu a fost găsit.',
        'admin_only': '❌ Această comandă este doar pentru administatori.',
        'total_feeds': 'Total fluxuri:',
        'total_users': 'Total utilizatori:',
        'total_posts_sent': 'Total postări trimise:',
        'top_feeds': 'Top 5 fluxuri:',
        'never_checked': 'Niciodată',
        'recommended_feeds': '⭐ **Fluxuri Recomandate**:\n\nFă clic pe un buton pentru a adăuga un flux recomandat:\n\n',
        'recommended_added': '✅ Fluxul recomandat "{feed_name}" adăugat cu succes!',
        'view_recommended': '⭐ Vezi Recomandate',
        'add_all_result': '✅ **Rezultat adăugare fluxuri**:\n\n',
        'added_feeds': '**Adăugate ({count})**:\n',
        'existing_feeds': '\n**Deja existente ({count})**:\n',
        'welcome_feeds': '📰 **Ultimele articole** din fluxurile tale:\n\n',
        'keep_all': '✅ Păstrează Toate',
        'customize': '⚙️ Personalizează',
        'reset': '🔄 Reset'
    }
}

class TelegramRSSBot:
    def __init__(self):
        self.application = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /start command"""
        user = update.effective_user
        language = db.get_user_settings(user.id)[1]
        
        # Show welcome message
        await update.message.reply_text(
            TEXTS[language]['start'],
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Auto-add recommended feeds if user doesn't have any
        user_feeds = db.get_user_feeds(user.id)
        
        if not user_feeds:
            # Add all recommended feeds
            added_count = 0
            for url, name in RECOMMENDED_FEEDS:
                feed_id = db.add_feed(user.id, url, name)
                if feed_id:
                    added_count += 1
            
            # Show confirmation
            if added_count > 0:
                await update.message.reply_text(
                    f"✅ Auto-added {added_count} recommended feeds!\n\nFetching latest articles...",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Fetch and display latest articles from each feed
                await self.display_feed_preview(update, context, language)
        else:
            # User already has feeds, show preview of latest articles
            await update.message.reply_text(
                TEXTS[language]['welcome_feeds'],
                parse_mode=ParseMode.MARKDOWN
            )
            await self.display_feed_preview(update, context, language)
    
    async def display_feed_preview(self, update: Update, context: ContextTypes.DEFAULT_TYPE, language: str):
        """Display preview of latest articles from user's feeds"""
        user = update.effective_user
        feeds = db.get_user_feeds(user.id)
        
        if not feeds:
            return
        
        # Fetch latest articles from each feed
        message = ""
        for feed_id, url, name, _, _ in feeds[:5]:  # Show max 5 feeds to avoid spam
            try:
                feed_data = await rss_parser.fetch_feed(url)
                
                if feed_data['status'] == 'success' and feed_data['entries']:
                    message += f"📌 **{name}**\n"
                    
                    # Show top 2 articles
                    for entry in feed_data['entries'][:2]:
                        title = entry.get('title', 'No title')[:80]
                        message += f"• {title}\n"
                    
                    message += "\n"
            except Exception as e:
                logger.error(f"Error fetching preview for {name}: {str(e)}")
                continue
        
        if message:
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            
            # Add action buttons
            keyboard = [
                [
                    InlineKeyboardButton(TEXTS[language]['keep_all'], callback_data="action_keep"),
                    InlineKeyboardButton(TEXTS[language]['customize'], callback_data="action_customize")
                ],
                [
                    InlineKeyboardButton(TEXTS[language]['reset'], callback_data="action_reset")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "What would you like to do?",
                reply_markup=reply_markup
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /help command"""
        user = update.effective_user
        language = db.get_user_settings(user.id)[1]
        
        await update.message.reply_text(
            TEXTS[language]['help'],
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def add_feed(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add a new RSS feed"""
        user = update.effective_user
        language = db.get_user_settings(user.id)[1]
        
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                f"Usage: /addfeed <url> <name>\nExample: /addfeed https://example.com/rss News"
            )
            return
        
        url = context.args[0]
        name = ' '.join(context.args[1:])
        
        # Simple URL validation
        if not url.startswith(('http://', 'https://')):
            await update.message.reply_text(TEXTS[language]['invalid_url'])
            return
        
        # Check maximum feeds limit
        user_feeds = db.get_user_feeds(user.id)
        if len(user_feeds) >= MAX_FEEDS_PER_USER:
            await update.message.reply_text(TEXTS[language]['feed_limit'])
            return
        
        # Try to add feed
        feed_id = db.add_feed(user.id, url, name)
        
        if feed_id:
            await update.message.reply_text(TEXTS[language]['feed_added'])
            
            # Test the feed
            keyboard = [
                [InlineKeyboardButton(TEXTS[language]['test_feed_btn'], callback_data=f"testfeed_{feed_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"Would you like to test the `{name}` feed?",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(TEXTS[language]['feed_exists'])
    
    async def recommended_feeds(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display recommended feeds"""
        user = update.effective_user
        language = db.get_user_settings(user.id)[1]
        
        message = TEXTS[language]['recommended_feeds']
        
        # Create buttons for each recommended feed
        keyboard = []
        for url, name in RECOMMENDED_FEEDS:
            keyboard.append([InlineKeyboardButton(f"⭐ {name}", callback_data=f"add_recommended_{url}_{name}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def add_all_recommended(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add all recommended feeds at once"""
        user = update.effective_user
        language = db.get_user_settings(user.id)[1]
        
        added = []
        skipped = []
        
        for url, name in RECOMMENDED_FEEDS:
            # Check if user already has this feed
            user_feeds = db.get_user_feeds(user.id)
            existing_urls = [feed[1] for feed in user_feeds]
            
            if url in existing_urls:
                skipped.append(name)
                continue
            
            # Check feed limit
            if len(user_feeds) + len(added) >= MAX_FEEDS_PER_USER:
                skipped.append(f"{name} (Limit reached)")
                continue
            
            feed_id = db.add_feed(user.id, url, name)
            if feed_id:
                added.append(name)
        
        message = TEXTS[language]['add_all_result']
        if added:
            message += TEXTS[language]['added_feeds'].format(count=len(added))
            for feed in added:
                message += f"• {feed}\n"
        
        if skipped:
            message += TEXTS[language]['existing_feeds'].format(count=len(skipped))
            for feed in skipped:
                message += f"• {feed}\n"
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    async def my_feeds(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display user's feeds"""
        user = update.effective_user
        language = db.get_user_settings(user.id)[1]
        
        feeds = db.get_user_feeds(user.id)
        
        if not feeds:
            await update.message.reply_text(TEXTS[language]['no_feeds'])
            return
        
        message = TEXTS[language]['my_feeds']
        
        for feed in feeds:
            feed_id, url, name, last_checked, is_active = feed
            last_checked_str = last_checked[:16] if last_checked else TEXTS[language]['never_checked']
            status = "✅" if is_active else "⏸️"
            
            message += f"{status} *{name}*\n"
            message += f"ID: `{feed_id}` | Last check: {last_checked_str}\n"
            message += f"URL: {url}\n\n"
        
        # Add buttons for each feed
        keyboard = []
        for feed in feeds:
            feed_id, _, name, _, _ = feed
            keyboard.append([
                InlineKeyboardButton(f"{TEXTS[language]['delete_feed_btn']} {name}", callback_data=f"delete_{feed_id}"),
                InlineKeyboardButton(TEXTS[language]['test_btn'], callback_data=f"testfeed_{feed_id}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def delete_feed(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete an RSS feed"""
        user = update.effective_user
        language = db.get_user_settings(user.id)[1]
        
        if not context.args:
            await update.message.reply_text(f"{TEXTS[language]['usage']} /deletefeed <id>\nUse /myfeeds to see feed IDs.")
            return
        
        try:
            feed_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid ID. Please enter a number.")
            return
        
        if db.delete_feed(user.id, feed_id):
            await update.message.reply_text(TEXTS[language]['feed_deleted'])
        else:
            await update.message.reply_text(TEXTS[language]['feed_not_found'])
    
    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display and manage settings"""
        user = update.effective_user
        settings = db.get_user_settings(user.id)
        language = settings[1]
        
        message = TEXTS[language]['settings']
        message += f"{TEXTS[language]['language']} {settings[1].upper()}\n"
        message += f"{TEXTS[language]['interval']} {settings[2]}\n"
        message += f"{TEXTS[language]['send_method']} "
        message += TEXTS[language]['individual'] if settings[3] else TEXTS[language]['digest']
        
        keyboard = [
            [
                InlineKeyboardButton("🌍 EN", callback_data="lang_en"),
                InlineKeyboardButton("🌍 RO", callback_data="lang_ro")
            ],
            [
                InlineKeyboardButton("⏰ 5m", callback_data="int_5"),
                InlineKeyboardButton("⏰ 10m", callback_data="int_10"),
                InlineKeyboardButton("⏰ 30m", callback_data="int_30")
            ],
            [
                InlineKeyboardButton("📨 Individual", callback_data="send_1"),
                InlineKeyboardButton("📦 Digest", callback_data="send_0")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def check_all_feeds(self, context: ContextTypes.DEFAULT_TYPE):
        """Check all feeds for new articles"""
        logger.info("Checking RSS feeds for new articles...")
        
        feeds = db.get_all_active_feeds()
        
        for feed in feeds:
            feed_id, user_id, url, name, last_checked, last_guid = feed
            
            try:
                new_posts = await rss_parser.check_new_posts(feed_id, url, last_guid)
                
                if new_posts:
                    logger.info(f"Found {len(new_posts)} new posts for {name}")
                    
                    # Send new posts
                    for post in reversed(new_posts):  # Oldest first
                        await self.send_post_to_user(context, user_id, name, post, db.get_user_settings(user_id)[1])
                        
                        # Mark post as sent
                        db.mark_post_as_sent(feed_id, post['guid'])
                    
                    # Update last_guid with newest post
                    if new_posts:
                        db.update_feed_last_checked(feed_id, new_posts[0]['guid'])
                
                await asyncio.sleep(1)  # Pause to avoid overloading
                
            except Exception as e:
                logger.error(f"Error checking feed {feed_id}: {str(e)}")
                continue
    
    async def send_post_to_user(self, context: ContextTypes.DEFAULT_TYPE, user_id: int, feed_name: str, post: dict, language: str = 'en'):
        """Send a post to user"""
        try:
            message_text = TEXTS[language]['new_post'].format(
                feed_name=feed_name,
                title=post['title'],
                description=post['description'][:500] + "..." if len(post['description']) > 500 else post['description'],
                link=post['link']
            )
            
            # Try to send message
            await context.bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=False
            )
            
        except Exception as e:
            logger.error(f"Error sending message to {user_id}: {str(e)}")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for inline buttons"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        data = query.data
        language = db.get_user_settings(user.id)[1]
        
        if data == "action_keep":
            await query.edit_message_text("✅ Great! All feeds are set up. Use /myfeeds to manage them.", parse_mode=ParseMode.MARKDOWN)
        
        elif data == "action_customize":
            await query.edit_message_text("📖 Use /myfeeds to remove feeds you don't want.", parse_mode=ParseMode.MARKDOWN)
        
        elif data == "action_reset":
            # Remove all feeds
            user_feeds = db.get_user_feeds(user.id)
            for feed_id, _, _, _, _ in user_feeds:
                db.delete_feed(user.id, feed_id)
            
            await query.edit_message_text("🔄 All feeds removed. Use /recommended to add feeds again.", parse_mode=ParseMode.MARKDOWN)
        
        elif data.startswith("add_recommended_"):
            # Extract URL and name from callback data
            parts = data.split("_", 2)  # Split into ["add", "recommended", "rest"]
            rest = parts[2]
            # Find the feed by splitting on the last underscore
            last_underscore = rest.rfind("_")
            url = rest[:last_underscore]
            name = rest[last_underscore+1:]
            
            # Check max feeds limit
            user_feeds = db.get_user_feeds(user.id)
            if len(user_feeds) >= MAX_FEEDS_PER_USER:
                await query.edit_message_text(TEXTS[language]['feed_limit'])
                return
            
            # Try to add the feed
            feed_id = db.add_feed(user.id, url, name)
            if feed_id:
                await query.edit_message_text(
                    TEXTS[language]['recommended_added'].format(feed_name=name),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(TEXTS[language]['feed_exists'])
        
        elif data.startswith("delete_"):
            feed_id = int(data.split("_")[1])
            if db.delete_feed(user.id, feed_id):
                await query.edit_message_text(TEXTS[language]['deleted_success'])
            else:
                await query.edit_message_text(TEXTS[language]['delete_error'])
        
        elif data.startswith("testfeed_"):
            feed_id = int(data.split("_")[1])
            await self.test_feed(query, feed_id, language)
        
        elif data.startswith("lang_"):
            language = data.split("_")[1]
            db.update_user_settings(user.id, language=language)
            await query.edit_message_text(f"✅ Language changed to {language.upper()}")
        
        elif data.startswith("int_"):
            interval = int(data.split("_")[1])
            db.update_user_settings(user.id, update_interval=interval)
            await query.edit_message_text(f"✅ Interval set to {interval} minutes")
        
        elif data.startswith("send_"):
            send_method = int(data.split("_")[1])
            db.update_user_settings(user.id, send_as_individual=send_method)
            method = "individual messages" if send_method else "digest"
            await query.edit_message_text(f"✅ Send method set to: {method}")
    
    async def test_feed(self, query, feed_id, language):
        """Test an RSS feed"""
        feeds = db.get_all_active_feeds()
        target_feed = None
        
        for feed in feeds:
            if feed[0] == feed_id:
                target_feed = feed
                break
        
        if not target_feed:
            await query.edit_message_text(TEXTS[language]['not_found'])
            return
        
        _, user_id, url, name, _, _ = target_feed
        
        await query.edit_message_text(TEXTS[language]['test_feed'])
        
        try:
            feed_data = await rss_parser.fetch_feed(url)
            
            if feed_data['status'] != 'success':
                await query.edit_message_text(f"{TEXTS[language]['test_error']} {feed_data.get('message', 'Unknown')}")
                return
            
            message = f"{TEXTS[language]['test_success']}\n\n"
            message += f"**{TEXTS[language]['feed_url']}** {url}\n"
            message += f"**Feed Title:** {feed_data['title']}\n"
            message += f"**Link:** {feed_data['link']}\n"
            message += f"**Description:** {feed_data['description'][:200]}...\n\n"
            message += f"**{TEXTS[language]['available_posts']}** {len(feed_data['entries'])}"
            
            if feed_data['entries']:
                message += f"\n\n**{TEXTS[language]['last_posts']}:**\n"
                for i, entry in enumerate(feed_data['entries'][:3], 1):
                    title = entry.get('title', 'No title')[:50]
                    message += f"{i}. {title}...\n"
            
            await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await query.edit_message_text(f"{TEXTS[language]['test_error']} {str(e)}")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Statistics for admins"""
        user = update.effective_user
        language = db.get_user_settings(user.id)[1]
        
        if user.id not in ADMIN_IDS:
            await update.message.reply_text(TEXTS[language]['admin_only'])
            return
        
        # Get statistics
        cursor = db.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM rss_feeds")
        total_feeds = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM rss_feeds")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sent_posts")
        total_posts = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT name, COUNT(*) as post_count 
            FROM rss_feeds f 
            JOIN sent_posts p ON f.id = p.feed_id 
            GROUP BY f.id 
            ORDER BY post_count DESC 
            LIMIT 5
        """)
        top_feeds = cursor.fetchall()
        
        message = f"{TEXTS[language]['stats']}"
        message += f"**{TEXTS[language]['total_feeds']}** {total_feeds}\n"
        message += f"**{TEXTS[language]['total_users']}** {total_users}\n"
        message += f"**{TEXTS[language]['total_posts_sent']}** {total_posts}\n\n"
        message += f"**{TEXTS[language]['top_feeds']}:**\n"
        
        for i, (name, count) in enumerate(top_feeds, 1):
            message += f"{i}. {name}: {count} posts\n"
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Error handler"""
        logger.error(f"Error: {context.error}", exc_info=context.error)
        
        if update and update.effective_message:
            language = 'en'
            if update.effective_user:
                language = db.get_user_settings(update.effective_user.id)[1]
            
            await update.effective_message.reply_text(TEXTS[language]['error'])
    
    def setup_handlers(self):
        """Setup handlers for the bot"""
        # Commands
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("addfeed", self.add_feed))
        self.application.add_handler(CommandHandler("myfeeds", self.my_feeds))
        self.application.add_handler(CommandHandler("recommended", self.recommended_feeds))
        self.application.add_handler(CommandHandler("addrecommended", self.add_all_recommended))
        self.application.add_handler(CommandHandler("deletefeed", self.delete_feed))
        self.application.add_handler(CommandHandler("settings", self.settings))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        
        # Callback for buttons
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Handler for unknown messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.help_command))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    def setup_jobs(self):
        """Setup periodic jobs"""
        job_queue = self.application.job_queue
        
        if job_queue:
            # Check feeds every X minutes
            job_queue.run_repeating(
                self.check_all_feeds,
                interval=UPDATE_INTERVAL_MINUTES * 60,
                first=10
            )
    
    async def run(self):
        """Run the bot"""
        # Create application
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Setup handlers and jobs
        self.setup_handlers()
        self.setup_jobs()
        
        # Run the bot
        await self.application.initialize()
        await self.application.start()
        
        # Start polling
        try:
            await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            logger.info("🤖 RSS Bot is running!")
            # Keep the bot running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        finally:
            # Cleanup
            await rss_parser.close_session()
            db.close()
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

# Main function
async def main():
    bot = TelegramRSSBot()
    await bot.run()

if __name__ == '__main__':
    asyncio.run(main())