import asyncio
import os
import json
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import firebase_admin
from firebase_admin import credentials, db

# পরিবেশের ভ্যারিয়েবল থেকে বট টোকেন নেওয়া
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ফায়ারবেস ডাটাবেজ ইনিশিয়ালাইজেশন (যদি আপনার রেন্ডারে JSON ফাইল বা এনভায়রনমেন্ট সেট করা থাকে)
# নোট: আপনার প্রজেক্টে যদি ইতিমধ্যে firebase_admin ইনিশিয়াল করা থাকে, তবে নিচের ব্লকটি আপনার আগের মতো রাখতে পারেন।
try:
    if not firebase_admin._apps:
        # রেন্ডার বা লোকাল এনভায়রনমেন্টের জন্য ডাটাবেজ ইউআরএল সেটআপ
        firebase_admin.initialize_app(options={
            'databaseURL': 'https://mini-app-link-default-rtdb.firebaseio.com/'
        })
except Exception as e:
    print(f"Firebase Init Error: {e}")

FIREBASE_DB_URL = "https://mini-app-link-default-rtdb.firebaseio.com/tasks.json"

# আপনার প্রাইভেট বোট স্টোরেজ চ্যানেল ID
STORAGE_CHANNEL_ID = -1004375264416

# আপনার ব্লগের লিংক এবং ব্যাকআপ চ্যানেল
BLOG_URL = "https://Bdnet24tv.blogspot.com"
BACKUP_CHANNEL_URL = "https://t.me/+VxzFPhQVKrViNjE1"

# বটের ইউজারনেম ও মিনি অ্যাপের নাম
BOT_USERNAME = "arohimimvirallinkjk_bot"
APP_NAME = "Master_King"

# JobQueue মেসেজ ডিলিট করার ফাংশন
async def delete_message_job(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    chat_id = job_data['chat_id']
    message_id = job_data['message_id']
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Delete failed: {e}")

# স্টার্ট কমান্ড হ্যান্ডলার
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    chat_id = update.effective_chat.id

    if args:
        incoming_param = args[0]
        msg_id = 5  # ডিফল্ট ফলব্যাক

        try:
            # যদি প্যারামিটারটি ফায়ারবেসের ইউনিক কি (-P...) হয়
            if incoming_param.startswith("-"):
                ref = db.reference(f'tasks/{incoming_param}')
                item_val = ref.get()
                if item_val and isinstance(item_val, dict) and 'message_id' in item_val:
                    msg_id = int(item_val['message_id'])
            
            # যদি পুরানো vid_ ফরম্যাট হয়
            elif incoming_param.startswith("vid_"):
                num_str = incoming_param.replace("vid_", "")
                if num_str.isdigit():
                    msg_id = int(num_str)
            else:
                ref = db.reference('tasks')
                data = ref.get()
                if data and isinstance(data, dict):
                    if incoming_param in data:
                        item_val = data[incoming_param]
                        if isinstance(item_val, dict) and 'message_id' in item_val:
                            msg_id = int(item_val['message_id'])
                    else:
                        keys_list = list(data.keys())
                        keys_list.reverse()
                        if incoming_param in keys_list:
                            msg_id = keys_list.index(incoming_param) + 1

            sent_msg = await context.bot.copy_message(
                chat_id=chat_id,
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=msg_id
            )
            
            warning_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="⏳ **সতর্কতা:** এই ভিডিওটি আগামী **১ ঘণ্টা** পর্যন্ত থাকবে, এরপর অটোমেটিক মুছে যাবে!",
                parse_mode="Markdown"
            )

            context.job_queue.run_once(delete_message_job, 3600, data={'chat_id': chat_id, 'message_id': sent_msg.message_id})
            context.job_queue.run_once(delete_message_job, 3600, data={'chat_id': chat_id, 'message_id': warning_msg.message_id})

        except Exception as e:
            print(f"Copy message error: {e}")
            await update.message.reply_text("❌ ভিডিওটি পাওয়া যায়নি বা লিংকটি মেয়াদোত্তীর্ণ।")
    else:
        await update.message.reply_text("👋 স্বাগতম! ভিডিও দেখতে মিনি অ্যাপ ব্যবহার করুন।")

# অটো-বাটন এবং ফায়ারবেস কি জেনারেটর হ্যান্ডলার
async def auto_add_buttons_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel_post = update.channel_post
    if not channel_post:
        return

    if channel_post.chat_id == STORAGE_CHANNEL_ID:
        return

    if not channel_post.reply_markup:
        post_text = channel_post.text or channel_post.caption or ""
        
        app_link = ""
        cleaned_text = post_text
        button_text = "Video Play 🥵"

        # পোস্ট থেকে vid_ নম্বর খুঁজে বের করা (যেমন: vid_21)
        match_vid = re.search(r'vid_(\d+)', post_text, re.IGNORECASE)
        
        firebase_key = None
        if match_vid:
            vid_number = match_vid.group(1)
            
            # firebase-admin ব্যবহার করে ফায়ারবেসে ডাটা পুশ করে র্যান্ডম ইউনিক কি (-P...) নেওয়া
            try:
                ref = db.reference('tasks')
                new_ref = ref.push({
                    "title": f"Video vid_{vid_number}",
                    "message_id": int(vid_number),
                    "createdAt": {".sv": "timestamp"},
                    "views": 0
                })
                firebase_key = new_ref.key # এটাই হলো ফায়ারবেসের আসল ইউনিক কি (-P...)
            except Exception as e:
                print(f"Firebase Admin Push Error: {e}")

        # যদি ফায়ারবেস থেকে সফলভাবে ইউনিক কি পাওয়া যায়
        if firebase_key:
            app_link = f"https://t.me/{BOT_USERNAME}/{APP_NAME}?startapp={firebase_key}"
            cleaned_text = re.sub(r'vid_\d+', '', post_text, flags=re.IGNORECASE).strip()
        else:
            app_link = f"https://t.me/{BOT_USERNAME}/{APP_NAME}"
            cleaned_text = post_text

        if not cleaned_text:
            cleaned_text = "✨ ভিডিওটি দেখতে নিচের বাটনে ক্লিক করুন:"

        keyboard = [
            [InlineKeyboardButton(button_text, url=app_link)],
            [InlineKeyboardButton("🌐 Visit Blog Site", url=BLOG_URL)],
            [InlineKeyboardButton("Backup channel", url=BACKUP_CHANNEL_URL)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            if channel_post.text:
                await context.bot.edit_message_text(
                    chat_id=channel_post.chat_id,
                    message_id=channel_post.message_id,
                    text=cleaned_text,
                    reply_markup=reply_markup
                )
            elif channel_post.caption:
                await context.bot.edit_message_caption(
                    chat_id=channel_post.chat_id,
                    message_id=channel_post.message_id,
                    caption=cleaned_text,
                    reply_markup=reply_markup
                )
        except Exception as e:
            print(f"Error editing message: {e}")

# রেন্ডার সার্ভার
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
        threading.Thread(target=run_dummy_server, daemon=True).start()
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, auto_add_buttons_to_channel))
        app.run_polling()
