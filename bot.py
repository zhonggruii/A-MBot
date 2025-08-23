import os
import logging
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configure logging and timestamp the entries
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Configuration 
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID environment variable is required")

class MessageBot:
    def __init__(self):
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database to store messages"""
        # Create SQLite database file
        # Creates a db file in the dir bot.py is in
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'messages.db')
        # Connect to SQLite database
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        # To execute SQL Commands
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                message_text TEXT,
                timestamp DATETIME,
                forwarded BOOLEAN DEFAULT FALSE
            )
        ''')
        self.conn.commit()
        print("Database initialized successfully")
    
    def store_message(self, user_id, username, message_text):
        """Store message in database"""
        # Create a new pointer to insert new messages
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO messages (user_id, username, message_text, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, message_text, datetime.now()))
        self.conn.commit()
        return cursor.lastrowid
    
    def mark_forwarded(self, message_id):
        """Mark message as forwarded"""
        # To show msg forwarded 
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE messages SET forwarded = TRUE WHERE id = ?
        ''', (message_id,))
        self.conn.commit()

# Initialize bot instance
bot_instance = MessageBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "Hi! Welcome to ROC Angel & Mortal! If there is any issues with the bot \n"
        "Please contact @zhonggruii\n"
        "We hope you have fun but here are some rules:\n"
        "1. Please make a reasonable challenge i.e nothing dangerous or illegal\n"
        "2. Please issue a challenge based on your mortal's tolerance level\n"
        "3. Please be respectful and dont use profanities\n"
        "4. Please dont spam the bot"
        "5. Please indicate your mortal @ at the start of the message\n"
        "i.e @zhonggruii Please bark 3 times\n"
        "If you have doubts about whether your challenge is okay, ask your RA or HH\n\n"
        "Send a message to get started!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages and forward to channel"""
    try:
        # Get user info
        user = update.effective_user
        message_text = update.message.text
        
        if not message_text:
            await update.message.reply_text("Please send a text message.")
            return
        
        # Store message in database
        message_id = bot_instance.store_message(
            user.id, 
            user.username or "Anonymous", 
            message_text
        )
        
        # Format message for channel
        channel_message = f"{message_text}"
        
        # Send to channel
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=channel_message
        )
        
        # Mark as forwarded
        bot_instance.mark_forwarded(message_id)
        
        # Confirm to user
        await update.message.reply_text(
            "Your message has been sent to the channel!"
        )
        
        print(f"Message #{message_id} forwarded successfully")
        
    except Exception as e:
        logging.error(f"Error handling message: {e}")
        await update.message.reply_text(
            "Sorry, there was an error sending your message. Please try again."
        )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics"""
    # Count how many messages sent successfully
    cursor = bot_instance.conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM messages')
    total_messages = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM messages WHERE forwarded = TRUE')
    forwarded_messages = cursor.fetchone()[0]
    
    await update.message.reply_text(
        f"Bot Statistics:\n"
        f"Total messages received: {total_messages}\n"
        f"Successfully forwarded: {forwarded_messages}"
    )

def main():
    """Start the bot"""
    print(f"Starting bot with token: {BOT_TOKEN[:10]}...")
    print(f"Channel ID: {CHANNEL_ID}")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the bot
    print("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()