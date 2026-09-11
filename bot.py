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

# JobQueue থেকে কল হওয়া মেসেজ ডিলিট করার ফাংশন
async def delete_message_job(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    chat_id = job_data['chat_id']
    message_id = job_data['message_id']
    
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Delete failed: {e}")

# স্টার্ট কমান্ড হ্যান্ডলার (সঠিকভাবে ফায়ারবেস কি দিয়ে ভিডিও খোঁজার লজিক)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    chat_id = update.effective_chat.id

    if args:
        incoming_param = args[0]
        msg_id = 5  # ডিফল্ট ফলব্যাক

        try:
            # ১. যদি প্যারামিটারটি ফায়ারবেসের ইউনিক কি (Key) হিসেবে আসে (যেমন: -P19GwsrApY...)
            if incoming_param.startswith("-"):
                msg_id = int(incoming_param) # সরাসরি ইউনিক কি অথবা স্টোরেজ চ্যানেলের মেসেজ আইডি হ্যান্ডেল করার জন্য
                
            # ২. যদি প্যারামিটারটি পুরানো vid_ ফরম্যাটে আসে
            elif incoming_param.startswith("vid_"):
                num_str = incoming_param.replace("vid_", "")
                if num_str.isdigit():
                    msg_id = int(num_str)
            else:
                # ফায়ারবেস থেকে ডাটা চেক করা
                req = urllib.request.Request(FIREBASE_DB_URL, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    if data and isinstance(data, dict):
                        if incoming_param in data:
                            item_val = data[incoming_param]
                            if isinstance(item_val, dict) and 'message_id' in item_val:
                                msg_id = int(item_val['message_id'])
                            elif isinstance(item_val, int):
                                msg_id = item_val
                        else:
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

# অটো-বাটন এবং টেক্সট ক্লিনার হ্যান্ডলার (ফায়ারবেস অরিজিনাল কি জেনারেটর সহ)
async def auto_add_buttons_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel_post = update.channel_post
    if not channel_post:
        return

    # যদি পোস্টটি আপনার স্টোরেজ চ্যানেল থেকে আসে, তবে বট কোনো বাটন বসাবে না
    if channel_post.chat_id == STORAGE_CHANNEL_ID:
        return

    if not channel_post.reply_markup:
        post_text = channel_post.text or channel_post.caption or ""
        
        app_link = ""
        cleaned_text = post_text
        button_text = "Video Play 🥵"

        # পোস্ট থেকে যেকোনো vid_ নম্বর খুঁজে বের করা (যেমন vid_6, vid_20 ইত্যাদি)
        match_vid = re.search(r'vid_(\d+)', post_text, re.IGNORECASE)
        
        firebase_key = None
        if match_vid:
            vid_number = match_vid.group(1)
            
            # ফায়ারবেসে ডেটা পাঠিয়ে র্যান্ডম ইউনিক কি (-P...) অটো জেনারেট করা
            try:
                post_data = json.dumps({
                    "title": f"Video vid_{vid_number}",
                    "message_id": int(vid_number),
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
                        firebase_key = res_data['name'] # ফায়ারবেসের অরিজিনাল ইউনিক কি (-P...)
            except Exception as e:
                print(f"Firebase Auto-Push Error: {e}")

        # যদি ফায়ারবেস থেকে ইউনিক কি সফলভাবে আসে
        if firebase_key:
            app_link = f"https://t.me/{BOT_USERNAME}/{APP_NAME}?startapp={firebase_key}"
            
            # পোস্টের টেক্সট থেকে vid_ নম্বরটি রিমুভ করে পরিষ্কার করা
            cleaned_text = re.sub(r'vid_\d+', '', post_text, flags=re.IGNORECASE).strip()
        else:
            app_link = f"https://t.me/{BOT_USERNAME}/{APP_NAME}"
            cleaned_text = post_text

        if not cleaned_text:
            cleaned_text = "✨ ভিডিওটি দেখতে নিচের বাটনে ক্লিক করুন:"

        # ইনলাইন বাটন লেআউট তৈরি
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
