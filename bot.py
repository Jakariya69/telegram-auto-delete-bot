import asyncio
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import firebase_admin
from firebase_admin import credentials, db

# পরিবেশের ভ্যারিয়েবল (Environment Variable) থেকে সিক্রেট তথ্য নেওয়া
FIREBASE_CREDS = os.getenv("FIREBASE_CREDENTIALS")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not firebase_admin._apps and FIREBASE_CREDS:
    cred_dict = json.loads(FIREBASE_CREDS)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://mini-app-link-default-rtdb.firebaseio.com'
    })

# ১ ঘণ্টা (৩৬০০ সেকেন্ড) পর মেসেজ স্বয়ংক্রিয়ভাবে মুছে ফেলার ফাংশন
async def delete_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 3600):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Delete failed: {e}")

# স্টার্ট কমান্ড হ্যান্ডলার
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    chat_id = update.effective_chat.id

    if args and args[0].startswith("vid_"):
        video_key = args[0].replace("vid_", "")
        
        ref = db.reference(f'tasks/{video_key}')
        video_data = ref.get()

        if video_data:
            title = video_data.get('title', 'Requested Video')
            video_url = video_data.get('url', '')

            caption_text = (
                f"🎬 **{title}**\n\n"
                f"⏳ **সতর্কতা:** এই ভিডিওটি আগামী **১ ঘণ্টা** পর্যন্ত থাকবে, এরপর স্বয়ংক্রিয়ভাবে মুছে যাবে (Vanished)!"
            )

            try:
                sent_msg = await context.bot.send_video(
                    chat_id=chat_id,
                    video=video_url,
                    caption=caption_text,
                    parse_mode="Markdown"
                )
            except Exception:
                msg_content = f"{caption_text}\n\n🔗 **লিংক:** {video_url}"
                sent_msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text=msg_content,
                    parse_mode="Markdown"
                )

            asyncio.create_task(delete_after_delay(context, chat_id, sent_msg.message_id, 3600))
        else:
            await update.message.reply_text("❌ ভিডিওটি পাওয়া যায়নি।")
    else:
        await update.message.reply_text("👋 স্বাগতম! ভিডিও আনলক করতে মিনি অ্যাপ ব্যবহার করুন।")

# Render-এর পোর্টের জন্য ডামি ওয়েব সার্ভার
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

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
        app.run_polling()
    else:
        print("BOT_TOKEN পাওয়া যায়নি!")
