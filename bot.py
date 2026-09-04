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

# আপনার প্রাইভেট বোট স্টোরেজ চ্যানেল ID (এই চ্যানেলে কোনো অটো-বাটন আসবে না)
STORAGE_CHANNEL_ID = -1004375264416

# আপনার ব্লগের লিংক (দ্বিতীয় বাটনের জন্য)
BLOG_URL = "https://Bdnet24tv.blogspot.com"

# আপনার ব্যাকআপ চ্যানেলের ইনভাইট লিংক
BACKUP_CHANNEL_URL = "https://t.me/+VxzFPhQVKrViNjE1"

# বটের ইউজারনেম ও মিনি অ্যাপের নাম
BOT_USERNAME = "arohimimvirallinkjk_bot"
APP_NAME = "Master_King"

# ফায়ারবেস থেকে সিরিয়াল অনুযায়ী আসল ইউনিক কি (Key) বের করার ফাংশন (.reverse সহ)
def get_firebase_key_by_index(index_num):
    try:
        req = urllib.request.Request(FIREBASE_DB_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data and isinstance(data, dict):
                keys_list = list(data.keys())
                # মিনি অ্যাপের ক্রমের সাথে মিল রাখার জন্য রিভার্স করা হলো
                keys_list.reverse()
                
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

# স্টার্ট কমান্ড হ্যান্ডলার (সঠিকভাবে ভিডিও পাঠানোর লজিক সহ)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    chat_id = update.effective_chat.id

    if args:
        incoming_param = args[0]
        msg_id = 5  # ডিফল্ট ফলব্যাক

        try:
            # ১. যদি প্যারামিটারটি vid_ ফরম্যাটে আসে (যেমন: vid_6)
            if incoming_param.startswith("vid_"):
                num_str = incoming_param.replace("vid_", "")
                if num_str.isdigit():
                    vid_num = int(num_str)
                    # সরাসরি চ্যানেলের মেসেজ আইডি হিসেবে ইনডেক্স নম্বরটি ব্যবহার করা
                    msg_id = vid_num

            # ২. যদি প্যারামিটারটি সরাসরি ফায়ারবেসের ইউনিক কি (Key) হিসেবে আসে
            else:
                # ফায়ারবেস থেকে ডাটা চেক করে দেখা যে এই কি-এর বিপরীতে কোনো মেসেজ আইডি আছে কি না
                req = urllib.request.Request(FIREBASE_DB_URL, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    if data and isinstance(data, dict) and incoming_param in data:
                        item_val = data[incoming_param]
                        # যদি ডাটার ভেতর সরাসরি মেসেজ আইডি সেভ করা থাকে
                        if isinstance(item_val, dict) and 'message_id' in item_val:
                            msg_id = int(item_val['message_id'])
                        elif isinstance(item_val, int):
                            msg_id = item_val
                        else:
                            # যদি কি দিয়ে সরাসরি না মেলে, তবে কি-এর পজিশন বা ইনডেক্স বের করে হিসাব করা
                            keys_list = list(data.keys())
                            keys_list.reverse()
                            if incoming_param in keys_list:
                                msg_id = keys_list.index(incoming_param) + 1

            # স্টোরেজ চ্যানেল থেকে নির্দিষ্ট মেসেজটি কপি করে ইউজারের কাছে পাঠানো
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

    # যদি পোস্টটি আপনার ভিডিও জমানোর প্রাইভেট চ্যানেল বা স্টোরেজ চ্যানেল থেকে আসে, তবে বট কোনো বাটন বসাবে না
    if channel_post.chat_id == STORAGE_CHANNEL_ID:
        return

    if not channel_post.reply_markup:
        post_text = channel_post.text or channel_post.caption or ""
        
        app_link = ""
        cleaned_text = post_text
        button_text = "Video Play 🥵"

        # ১. পোস্ট থেকে vid_ ফরম্যাট খোঁজা (যেমন vid_5)
        match_vid = re.search(r'vid_(\d+)', post_text, re.IGNORECASE)
        # ২. অথবা ফায়ারবেসের ইউনিক কি ফরম্যাট খোঁজা (যেমন -P0QrDkLvG2NeYnM8WxT)
        match_fb_key = re.search(r'(-[a-zA-Z0-9_-]{10,})', post_text)

        if match_vid:
            vid_number = int(match_vid.group(1))
            app_link = f"https://t.me/{BOT_USERNAME}/{APP_NAME}?startapp=vid_{vid_number}"
            cleaned_text = re.sub(r'vid_\d+', '', post_text, flags=re.IGNORECASE).strip()
            
        elif match_fb_key:
            firebase_key = match_fb_key.group(1)
            app_link = f"https://t.me/{BOT_USERNAME}/{APP_NAME}?startapp={firebase_key}"
            # ফায়ারবেসের আসল কি-টি টেক্সট থেকে সম্পূর্ণ রিমুভ করে ফেলা
            cleaned_text = post_text.replace(firebase_key, "").strip()
            
        else:
            app_link = f"https://t.me/{BOT_USERNAME}/{APP_NAME}"
            cleaned_text = post_text

        if not cleaned_text:
            cleaned_text = "✨ ভিডিওটি দেখতে নিচের বাটনে ক্লিক করুন:"

        # বাটন লেআউট: দ্বিতীয় বাটনে আপনার ব্লগ সাইটের লিংক বসানো হয়েছে
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
            print(f"Error: {e}")

# ডামি সার্ভার রেন্ডার পোর্টের জন্য
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
