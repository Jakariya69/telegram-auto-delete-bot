import asyncio
import os
import json
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import urllib.request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# পরিবেশের ভ্যারিয়েবল থেকে বট টোকেন নেওয়া
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ফায়ারবেস ডাটাবেজের ইউআরএল
FIREBASE_DB_URL = "https://mini-app-link-default-rtdb.firebaseio.com/tasks.json"

# আপনার প্রাইভেট বোট স্টোরেজ চ্যানেল ID
STORAGE_CHANNEL_ID = -1004375264416

# আপনার প্রদান করা মূল ও ব্যাকআপ চ্যানেলের ইনভাইট লিংক
MAIN_CHANNEL_URL = "https://t.me/+2cFW7aJB6_pkODc1"
BACKUP_CHANNEL_URL = "https://t.me/+VxzFPhQVKrViNjE1"

# বটের ইউজারনেম ও মিনি অ্যাপের নাম
BOT_USERNAME = "arohimimvirallinkjk_bot"
APP_NAME = "Master_King"

# ফায়ারবেস থেকে ডাটা ফেচ করে সিরিয়াল অনুযায়ী আসল কি বের করার ফাংশন
def get_firebase_key_by_index(index_num):
    try:
        req = urllib.request.Request(FIREBASE_DB_URL)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if data and isinstance(data, dict):
                keys_list = list(data.keys())
                target_index = index_num - 1
                if 0 <= target_index < len(keys_list):
                    return keys_list[target_index]
    except Exception as e:
        print(f"Firebase fetch error: {e}")
    return None

# JobQueue থেকে কল হওয়া মেসেজ ডিলিট করার ফাংশন
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
        video_key = args[0]
        
        # যদি vid_ ফরম্যাটে আসে (যেমন vid_1)
        if video_key.startswith("vid_"):
            num_str = video_key.replace("vid_", "")
            if num_str.isdigit():
                real_firebase_key = get_firebase_key_by_index(int(num_str))
                if real_firebase_key:
                    video_key = real_firebase_key

        try:
            # যদি ফায়ারবেস কি সরাসরি মেসেজ আইডি না হয়ে থাকে, তবে আপনার স্টোরেজ চ্যানেলের নির্দিষ্ট কোনো ডিফল্ট মেসেজ আইডি (যেমন: 5) সেট করে দিতে পারেন 
            # অথবা আপনার প্রয়োজনমতো এখানে মেসেজ আইডি হ্যান্ডেল করতে পারেন।
            msg_id = int(video_key) if video_key.isdigit() else 5 
            
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

# অটো-বাটন এবং টেক্সট ক্লিনার হ্যান্ডলার
async def auto_add_buttons_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel_post = update.channel_post
    if not channel_post:
        return

    if not channel_post.reply_markup:
        post_text = channel_post.text or channel_post.caption or ""
        
        # পোস্ট থেকে vid_1 বা শুধু নাম্বার ট্র্যাক করার লজিক
        match = re.search(r'vid_(\d+)', post_text, re.IGNORECASE)
        
        if match:
            vid_number = match.group(1)
            app_link = f"https://t.me/{BOT_USERNAME}/{APP_NAME}?startapp=vid_{vid_number}"
            button_text = "🔴 WATCH THIS VIDEO ONLINE ⚡"
            
            cleaned_text = re.sub(r'vid_\d+', '', post_text).strip()
            if not cleaned_text:
                cleaned_text = "✨ ভিডিওটি দেখতে নিচের বাটনে ক্লিক করুন:"
        else:
            app_link = f"https://t.me/{BOT_USERNAME}/{APP_NAME}"
            button_text = "🔴 OPEN VIRAL ZONE APP ⚡"
            cleaned_text = post_text

        # একদম গোছালো এবং বক্স স্টাইল বাটন লেআউট
        keyboard = [
            [InlineKeyboardButton(button_text, url=app_link)],
            [
                InlineKeyboardButton("🟡 MAIN CHANNEL", url=MAIN_CHANNEL_URL),
                InlineKeyboardButton("🔵 BACKUP CHANNEL", url=BACKUP_CHANNEL_URL)
            ]
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
            print(f"Error: {e}")

# ডামি সার্ভার রেন্ডার পোর্টের জন্য
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")
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
