import logging
import re
import os
import httpx
import asyncio
import pyotp
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackQueryHandler, ConversationHandler
from telegram.constants import ParseMode
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("SMS_API_KEY")

UPDATE_CHANNEL = "@META_FIRE_UPDATE"
OTP_CHANNEL = "@META_FIRE_OTP"
BOT_USERNAME = "Meta_Fire_OTP_Bot"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

main_keyboard = ReplyKeyboardMarkup([
    [KeyboardButton("🔥 GET NUMBER 🔥")],
    [KeyboardButton("🔐 2FA CODE"), KeyboardButton("📡 LIVE OTP SECTION")]
], resize_keyboard=True, is_persistent=True)

# 2FA State
SECRET_KEY = range(1)

COUNTRY_MAP = {
    "232": {"name": "Sierra Leone", "flag": "🇸🇱"},
    "224": {"name": "Guinea", "flag": "🇬🇳"},
    "225": {"name": "Ivory Coast", "flag": "🇨🇮"}
}

async def is_user_subscribed(context, user_id):
    try:
        m1 = await context.bot.get_chat_member(chat_id=UPDATE_CHANNEL, user_id=user_id)
        m2 = await context.bot.get_chat_member(chat_id=OTP_CHANNEL, user_id=user_id)
        return m1.status not in ['left', 'kicked'] and m2.status not in ['left', 'kicked']
    except:
        return False

# ==================== 2FA ====================
async def twofa_start(update: Update, context):
    await update.message.reply_text("🔐 **2FA Code Generator**\n\nআপনার **2FA Secret Key** পাঠান (2fa-auth.com থেকে):")
    return SECRET_KEY

async def twofa_generate(update: Update, context):
    secret = update.message.text.strip().upper().replace(" ", "")
    try:
        totp = pyotp.TOTP(secret)
        code = totp.now()
        remaining = totp.interval - (int(datetime.now().timestamp()) % totp.interval)
        
        await update.message.reply_text(f"✅ **2FA Code:** `{code}`\nValid for {remaining} seconds", parse_mode=ParseMode.MARKDOWN)
        
        await context.bot.send_message(
            chat_id=OTP_CHANNEL,
            text=f"🌟 **2FA Code:** `{code}` | Expires in {remaining}s",
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        await update.message.reply_text("❌ Invalid Secret Key! আবার চেষ্টা করুন।")
    return ConversationHandler.END

# ==================== OTP FUNCTIONS ====================
active_otp_tasks = {}

async def check_otp(...):  # আপনার আগের check_otp ফাংশন রাখুন (সংক্ষেপে রাখছি)
    pass  # পুরো ফাংশন আগের কোড থেকে নিন

async def start(update, context):
    # আগের start ফাংশন
    pass

async def handle_callback(update, context):
    # আগের handle_callback ফাংশন
    pass

async def show_services(msg):
    kb = [[InlineKeyboardButton("🔷 FACEBOOK 🔷", callback_data="service_facebook")],
          [InlineKeyboardButton("📸 INSTAGRAM 📸", callback_data="service_instagram")]]
    await msg.reply_text("Select platform:", reply_markup=InlineKeyboardMarkup(kb))

async def text_handler(update, context):
    if not await is_user_subscribed(context, update.effective_user.id):
        return await start(update, context)
    text = update.message.text
    if "GET NUMBER" in text:
        await show_services(update.message)
    elif "2FA CODE" in text:
        return await twofa_start(update, context)
    elif "LIVE OTP" in text:
        await update.message.reply_text("Join Channel:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📡 View Live", url=f"https://t.me/{OTP_CHANNEL.replace('@', '')}")]]))
    else:
        await update.message.reply_text("মেনু থেকে সিলেক্ট করুন।")

# ==================== APP ====================
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('2FA CODE'), twofa_start)],
    states={SECRET_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, twofa_generate)]},
    fallbacks=[]
))
app.add_handler(MessageHandler(filters.TEXT, text_handler))

if __name__ == "__main__":
    logging.info("🤖 META FIRE OTP Bot Started Successfully!")
    app.run_polling()
