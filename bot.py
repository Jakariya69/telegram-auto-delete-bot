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

# স্টার্ট কমান্ড হ্যান্ডলার (Updated)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    chat_id = update.effective_chat.id

    if args:
        post_id = args[0]
        
        # vid_ থাকলে সেটা সরিয়ে ফেলা
        if post_id.startswith("vid_"):
            post_id = post_id.replace("vid_", "")

        try:
            # যদি post_id একটি সংখ্যা হয় (যেমন: 2, 10, 15)
            if post_id.isdigit():
                msg_id = int(post_id)
            else:
                # যদি মিনি অ্যাপ থেকে ফায়ারবেসের কি বা আইডি পাঠানো হয়,
                # তবে সেখান থেকে শুধু সংখ্যা বের করার লজিক
                digits = ''.join(filter(str.isdigit, post_id))
                if digits:
                    msg_id = int(digits)
                else:
                    raise ValueError("No numeric message ID found in parameter")

            # প্রাইভেট চ্যানেল থেকে পোস্টটি ইউজারের ইনবক্সে কপি করে সেন্ড করা
            sent_msg = await context.bot.copy_message(
                chat_id=chat_id,
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=msg_id
            )
            
            # সতর্কতামূলক মেসেজ সেন্ড
            warning_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="⏳ **সতর্কতা:** এই ভিডিওটি আগামী **১ ঘণ্টা** পর্যন্ত থাকবে, এরপর অটোমেটিক মুছে যাবে!",
                parse_mode="Markdown"
            )

            # ১ ঘণ্টা (৩৬০০ সেকেন্ড) পর ভিডিও এবং সতর্কতামূলক মেসেজ ডিলিট
            asyncio.create_task(delete_after_delay(context, chat_id, sent_msg.message_id, 3600))
            asyncio.create_task(delete_after_delay(context, chat_id, warning_msg.message_id, 3600))

        except Exception as e:
            print(f"Error sending message: {e}")
            await update.message.reply_text(f"❌ ভিডিওটি পাওয়া যায়নি বা মুছে ফেলা হয়েছে। (Error Details: {e})")
    else:
        await update.message.reply_text("👋 স্বাগতম! ভিডিও দেখতে মিনি অ্যাপ ব্যবহার করুন।")

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
