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

# ফায়ারবেস ডাটাবেজের রিয়েলটাইম ইউআরএল
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

# স্টার্ট কমান্ড হ্যান্ডলার (সঠিক ভিডিও আইডি খোঁজার নির্ভুল লজিক)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    chat_id = update.effective_chat.id

    if args:
        incoming_param = args[0]
        msg_id = None

        try:
            # ফায়ারবেস থেকে ডাটা ফেচ করা
            req = urllib.request.Request(FIREBASE_DB_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                if data and isinstance(data, dict):
                    # ১. যদি সরাসরি ইউনিক কি (-P...) মিলে যায়
                    if incoming_param in data:
                        item_val = data[incoming_param]
                        if isinstance(item_val, dict):
                            if 'message_id' in item_val:
                                msg_id = int(item_val['message_id'])
                            elif 'url' in item_val:
                                match_url = re.search(r'/(\d+)$', str(item_val['url']))
                                if match_url:
                                    msg_id = int(match_url.group(1))

            if msg_id:
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
            else:
                await update.message.reply_text("❌ ভিডিওটি পাওয়া যায়নি বা লিংকটি মেয়াদোত্তীর্ণ।")

        except Exception as e:
            print(f"Copy message error: {e}")
            await update.message.reply_text("❌ ভিডিওটি লোড করতে সমস্যা হয়েছে।")
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

        # টেক্সট থেকে শুধু নির্দিষ্ট vid_ নম্বরটি ট্র্যাক করা (যেমন: vid_21 থেকে 21 বের করা)
        match_vid = re.search(r'vid_(\d+)', post_text, re.IGNORECASE)
        match_link = re.search(r'https?://t\.me/c/(\d+)/(\d+)', post_text)
        
        vid_number = None
        target_url = ""

        if match_vid:
            vid_number = int(match_vid.group(1))
            target_url = f"https://t.me/c/4375264416/{vid_number}"
        elif match_link:
            vid_number = int(match_link.group(2))
            target_url = match_link.group(0)
        else:
            return # যদি vid_ বা লিংক কিছুই না থাকে, তবে বট ফায়ারবেসে কোনো ফালতু এন্ট্রি করবে না

        # ফায়ারবেসে সঠিক ডেটা পাঠানো
        firebase_key = None
        try:
            post_data = json.dumps({
                "url": target_url,
                "message_id": vid_number,
                "createdAt": {".sv": "timestamp"},
                "views": 0
            }).encode('utf-8')

            req = urllib.request.Request(
                FIREBASE_DB_URL, 
                data=post_data, 
                headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                res_data = json.loads(response.read().decode())
                if res_data and 'name' in res_data:
                    firebase_key = res_data['name']
        except Exception as e:
            print(f"Firebase HTTP POST Error: {e}")

        # মিনি অ্যাপের লিংকে ইউনিক কি বসানো
        if firebase_key:
            app_link = f"https://t.me/{BOT_USERNAME}/{APP_NAME}?startapp={firebase_key}"
            cleaned_text = re.sub(r'vid_\d+', '', post_text, flags=re.IGNORECASE).strip()
            cleaned_text = re.sub(r'https?://t\.me/c/\d+/\d+', '', cleaned_text).strip()
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
