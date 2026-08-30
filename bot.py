import asyncio
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# পরিবেশের ভ্যারিয়েবল থেকে বট টোকেন নেওয়া
BOT_TOKEN = os.getenv("BOT_TOKEN")

# আপনার প্রাইভেট চ্যানেলের Chat ID
STORAGE_CHANNEL_ID = -1004375264416

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

            # ১ ঘণ্টা পর ভিডিও এবং সতর্কতামূলক মেসেজ দুটোই ডিলিট করা
            asyncio.create_task(delete_after_delay(context, chat_id, sent_msg.message_id, 3600))
            asyncio.create_task(delete_after_delay(context, chat_id, warning_msg.message_id, 3600))

        except Exception as e:
            await update.message.reply_text("❌ ভিডিওটি পাওয়া যায়নি বা মুছে ফেলা হয়েছে।")
    else:
        await update.message.reply_text("👋 স্বাগতম! ভিডিও ডাউনলোড করতে মিনি অ্যাপ ব্যবহার করুন।")

# Render-এর পোর্টের জন্য ডামি ওয়েব সার্ভার
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

    # UptimeRobot-এর HEAD Request হ্যান্ডেল করার জন্য (501 error সমাধান করতে)
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    # ব্যাকগ্রাউন্ড অতিরিক্ত লগ বন্ধ রাখতে
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
        app.run_polling()
    else:
        print("BOT_TOKEN পাওয়া যায়নি!")
