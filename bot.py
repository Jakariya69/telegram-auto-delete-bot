import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import firebase_admin
from firebase_admin import credentials, db

# ১. ফায়ারবেস কনফিগারেশন
SERVICE_ACCOUNT_INFO = {
  "type": "service_account",
  "project_id": "mini-app-link",
  "private_key_id": "ca51af7f520e40c3fcda75f0ef680fef44723388",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC3IDyV86c1ek58\nY1G08C+nj414YR8PYxHJsu//r8a9s+IicTVbXmpN0EVUvyeAFMC9evPbHztzzO9V\netGbKTTtvEaHBhlnqFzQcXpiVddfppGbqBeQPpoo7XIo050eTOfP3KzKZUUpdy+e\nMMepCQdlqGTUJnhw92ocMUipqCGHOD8ksOVUWUrolGhxKZiflemLLX76pdo/ywb5\nJ8Wr0maD1BI2hsK6YyJbSmSNPAys97/facGb+kZT3k/KRoPbovDSrsiAmF/bK1Dz\nWIOjjKGUWLVnwZ5W1E6rwuKaKRrXdXN47Nr0xzseLqlQUA3VN3TC3L1h6Dkr/eDW\nrNhHuXinAgMBAAECggEAFhp1AEsi2+iW/+/jqn7x3DwOgQDar+UZqN/JP3Jm/voZ\ntGXiYSnkk4nXpHgCJjUwYm6BxT61fVpiFPjjGI2ruXo9L7UDwf2SCQgkE9R1T4fv\nu/sDr8HD97wD8yY/qQBIBqXbJql8j0Rh4f/UnvQxCWB+8xXFpH+oi3NDaFRGimcs\n/cVIfhYQV/kCZ17/6UB8ss4wn98SpoFyg8MqYTjIu28MVEiplFRLDRMQYWlK4JcG\nY/01hE1XwmnR3zZ+5WkB1+q9KRwnliF4fMqCEi5Xn6R3XUS3xqN3QFD/GdWAiqgl\ncuuNCrSnTJl+Gh+k9OBhuO4TgXbwG0999JuuJsVOCQKBgQDc+IvTYKw3YhYtaDIM\nw5xU01BdQKMETCSniloFApSlGSo4Gw/3g6jLK0edYu/qtRXxL11wP7a2+2zNs+db\nxcqqsYzum2SuFuBzW/FAH7S+YvNhgJE7kDrmrOPejQ0OG9IOOeY7324f+fPXlqRM\nqxk2nXGGcuDMBTofY9wnRVgDNQKBgQDUJ90x3D/AeHq5Jqx3aJ8K2rNTpkeUMYu8\n0yvAPRcouOQtYy4cjWkC8jzKJhcMaGDJ4D/KYWdBCRqEyIGALgMaa61XwkW4L9qA\n9feo8Ggqtw/QfJKdt+YTvam7txdrpdB2avl2OPe8uG+tX24k471k4pMgFDMN7qZf\nWpOWbMZL6wKBgDhM84Nl7DsoOLJVC/uIk3phZOZ9o4tiwywU6h7Aq5LtOH6XFphf\n6U/qtRJ6tNo+TVroUIxbD3jL0ssOfXI6kQqwtlHNMffRSFrcIDnQWkLv/0bmdRqS\nAw/nGSAJHDxuBjUtt2Wl5e8rxl81uKL4LTJnJxe0iWYyJr78uIkg9+3JAoGAdYUL\ni0YU7noOiSd6G78RcoLJGUoflmCHpnZXYuq0PHOGufmZnmlaxS4ILHZDCDV9f/Y/\nf8zK1ITFcs5apfVW9Li20ckks62WXR9jK+rX2OmE0hlfYgxvX3oNXpVCXPgB7Ma/\nHxTZbmnAOwqEydx5mjvEAd4OleYftOxImufwRDcCgYEAjGyZUOt1Jg297ImIi0zM\n0Upsq+oNRRDXYQUkUk6WB1xn2clm6nzJ+60vo0mmk7GAIHvlPp5hn66RU/iGkxRR\n0vBbXtOGURo0z3lFwbH81bPwqIHwszn7g19dnO9cnZKfYqq1d8JgNqmdYhKWeBK8\n5yVRU/VnYUHa0ervT15rFRg=\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-fbsvc@mini-app-link.iam.gserviceaccount.com",
  "client_id": "111092070377973257203",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40mini-app-link.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_INFO)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://mini-app-link-default-rtdb.firebaseio.com'
    })

BOT_TOKEN = "8530415777:AAGBpqEGfXitqcReJ4iPuWafhwBJnP6e2OM"

# ২. ১ ঘণ্টা (৩৬০০ সেকেন্ড) পর ডিলিট করার ফাংশন
async def delete_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 3600):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Delete failed: {e}")

# ৩. স্টার্ট CommandHandler
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

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
