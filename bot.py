import asyncio
import os
import json
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# পরিবেশের ভ্যারিয়েবল থেকে বট টোকেন নেওয়া
BOT_TOKEN = os.getenv("BOT_TOKEN")

# আপনার প্রাইভেট বোট স্টোরেজ চ্যানেল ID
STORAGE_CHANNEL_ID = -1004375264416

# আপনার প্রদান করা মূল ও ব্যাকআপ চ্যানেলের ইনভাইট লিংক
MAIN_CHANNEL_URL = "https://t.me/+2cFW7aJB6_pkODc1"
BACKUP_CHANNEL_URL = "https://t.me/+VxzFPhQVKrViNjE1"

# বটের ইউজারনেম ও মিনি অ্যাপের নাম
BOT_USERNAME = "arohimimvirallinkjk_bot"
APP_NAME = "Master_King"

# JobQueue থেকে কল হওয়া মেসেজ ডিলিট করার ফাংশন
async def delete_message_job(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    chat_id = job_data['chat_id']
    message_id = job_data['message_id']
    
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        print(f"Successfully deleted message {message_id} in chat {chat_id}")
    except Exception as e:
        print(f"Delete failed for message {message_id}: {e}")

# স্টার্ট কমান্ড হ্যান্ডলার (ইউজার যখন অ্যাপ বা বোতামে ক্লিক করবে)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    chat_id = update.effective_chat.id

    if args:
        post_id = args[0]
        
        # vid_ থাকলে সেটা সরিয়ে মূল Message ID বের করা
        if post_id.startswith("vid_"):
            post_id = post_id.replace("vid_", "")

        try:
            # প্রাইভেট চ্যানেল থেকে পোস্টটি ইউজারের ইনবক্সে কপি করে সেন্ড করা
            sent_msg = await context.bot.copy_message(
                chat_id=chat_id,
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=int(post_id)
            )
            
            # সতর্কতামূলক মেসেজ সেন্ড
            warning_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="⏳ **সতর্কতা:** এই ভিডিওটি আগামী **১ ঘণ্টা** পর্যন্ত থাকবে, এরপর অটোমেটিক মুছে যাবে!",
                parse_mode="Markdown"
            )

            # JobQueue ব্যবহার করে ৩৬০০ সেকেন্ড (১ ঘণ্টা) পর ডিলিট করার শিডিউল সেট
            context.job_queue.run_once(
                delete_message_job, 
                when=3600, 
                data={'chat_id': chat_id, 'message_id': sent_msg.message_id}
            )
            context.job_queue.run_once(
                delete_message_job, 
                when=3600, 
                data={'chat_id': chat_id, 'message_id': warning_msg.message_id}
            )

        except Exception as e:
            await update.message.reply_text("❌ ভিডিওটি পাওয়া যায়নি বা মুছে ফেলা হয়েছে।")
    else:
        await update.message.reply_text("👋 স্বাগতম! ভিডিও দেখতে এবং আনলক করতে মিনি অ্যাপ ব্যবহার করুন।")

# ---------------- স্মার্ট অটো-বাটন হ্যান্ডলার ----------------
async def auto_add_buttons_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel_post = update.channel_post
    if not channel_post:
        return

    # যদি পোস্টে ইতিমধ্যে কোনো বাটন যুক্ত না থাকে
    if not channel_post.reply_markup:
        post_text = channel_post.text or channel_post.caption or ""
        
        # টেক্সট থেকে vid_123, ID: 123 কিংবা টেলিগ্রামের চ্যানেলের লিংক থেকে আইডি বের করার লজিক
        match = re.search(r'(?:vid_|id[:=]?\s*|\/c\/\d+\/)(\d+)', post_text, re.IGNORECASE)
        
        if match:
            video_id = match.group(1)
            # নির্দিষ্ট ভিডিও ওপেন করার ডাইরেক্ট অ্যাপ লিংক
            app_link = f"https://t.me/{BOT_USERNAME}/{APP_NAME}?startapp=vid_{video_id}"
            button_text = "🔴 WATCH THIS VIDEO ONLINE ⚡"
        else:
            # সাধারণ অ্যাপ হোমপেজ লিংক
            app_link = f"https://t.me/{BOT_USERNAME}/{APP_NAME}"
            button_text = "🔴 OPEN VIRAL ZONE APP ⚡"

        # লাল, হলুদ এবং নীল কালারফুল বাটন
        keyboard = [
            [InlineKeyboardButton(button_text, url=app_link)],
            [
                InlineKeyboardButton("🟡 MAIN CHANNEL", url=MAIN_CHANNEL_URL),
                InlineKeyboardButton("🔵 BACKUP CHANNEL", url=BACKUP_CHANNEL_URL)
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            # চ্যাটের পোস্টে সরাসরি বাটন যুক্ত করা
            await context.bot.edit_message_reply_markup(
                chat_id=channel_post.chat_id,
                message_id=channel_post.message_id,
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"Error adding buttons: {e}")

# Render-এর পোর্টের জন্য ডামি ওয়েব সার্ভার
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def log_message(self, format, *args):
        return

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

if __name__ == '__main__':
    if BOT_TOKEN:
        # ব্যাকগ্রাউন্ড পোর্টের জন্য থ্রেড চালু করা
        threading.Thread(target=run_dummy_server, daemon=True).start()
        
        # বট চালু
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        
        # প্রাইভেট বা পাবলিক যেকোনো চ্যানেল থেকে আসা পোস্ট ট্র্যাক করার জন্য আপডেট করা ফিল্টার
        app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, auto_add_buttons_to_channel))

        app.run_polling()
    else:
        print("BOT_TOKEN পাওয়া যায়নি!")
