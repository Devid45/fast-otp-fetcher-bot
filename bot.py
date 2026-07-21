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

SECRET_KEY = range(1)
active_otp_tasks = {}

COUNTRY_MAP = {
    "232": {"name": "Sierra Leone", "flag": "🇸🇱"},
    "224": {"name": "Guinea", "flag": "🇬🇳"},
    "225": {"name": "Ivory Coast", "flag": "🇨🇮"}
}

# ==================== FAST API ====================
async def call_website_api_async(endpoint, method="POST", payload=None):
    try:
        url = f"https://2eee7.com/@Access/@Bot/2eee7/@public/api/{endpoint}"
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=5.0) as client:   # আরও কম টাইমআউট
            if method == "GET":
                r = await client.get(url, headers=headers)
            else:
                r = await client.post(url, json=payload, headers=headers)
            return r.json() if r.status_code == 200 else None
    except:
        return None

async def is_user_subscribed(context, user_id):
    try:
        m1 = await context.bot.get_chat_member(chat_id=UPDATE_CHANNEL, user_id=user_id)
        m2 = await context.bot.get_chat_member(chat_id=OTP_CHANNEL, user_id=user_id)
        return m1.status not in ['left', 'kicked'] and m2.status not in ['left', 'kicked']
    except:
        return False

# ==================== 2FA FAST ====================
async def twofa_start(update: Update, context):
    await update.message.reply_text("🔐 **Secret Key** পাঠান:")
    return SECRET_KEY

async def twofa_generate(update: Update, context):
    secret = update.message.text.strip().upper().replace(" ", "")
    try:
        totp = pyotp.TOTP(secret)
        code = totp.now()
        remaining = 30 - (int(datetime.now().timestamp()) % 30)
        await update.message.reply_text(f"✅ **Code:** `{code}`\n⏱ {remaining} সেকেন্ড", parse_mode=ParseMode.MARKDOWN)
    except:
        await update.message.reply_text("❌ Invalid Key!")
    return ConversationHandler.END

# ==================== OTP ====================
async def check_otp(context, chat_id, number):
    full_number = re.sub(r'\D', '', str(number))
    for _ in range(400):
        await asyncio.sleep(1.2)
        res = await call_website_api_async("success-otp-info", "GET")
        if res and "otps" in res.get("data", {}):
            for item in res["data"]["otps"]:
                if re.sub(r'\D', '', str(item.get("number", ""))).endswith(full_number[-8:]):
                    otp = item.get("otp") or item.get("code")
                    if otp:
                        await context.bot.send_message(chat_id=chat_id, text=f"✅ **OTP:** `{otp}`", parse_mode=ParseMode.MARKDOWN)
                        return
    await context.bot.send_message(chat_id=chat_id, text="❌ Timeout")

# ==================== MAIN HANDLERS (FAST RESPONSE) ====================
async def start(update, context):
    if not await is_user_subscribed(context, update.effective_user.id):
        kb = [[InlineKeyboardButton("Join Channels", url="https://t.me/META_FIRE_UPDATE")]]
        await update.message.reply_text("চ্যানেলে জয়েন করুন", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text("✅ রেডি!", reply_markup=main_keyboard)

async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()   # তাৎক্ষণিক ফিডব্যাক

    if query.data == "verify":
        if await is_user_subscribed(context, query.from_user.id):
            await query.message.delete()
            await context.bot.send_message(query.message.chat_id, "✅ ভেরিফাইড!", reply_markup=main_keyboard)

    elif query.data.startswith("service_"):
        await query.message.edit_text("🔄 Ranges লোড হচ্ছে...")
        await asyncio.sleep(0.3)  # ছোট ডিলে দিয়ে স্মুথ ফিল
        await show_ranges(query.message, query.data.split("_")[1])

    elif query.data.startswith("range_"):
        parts = query.data.split("_")
        await query.message.edit_text("⚡ নাম্বার অ্যালোকেট করা হচ্ছে...")
        
        res = await call_website_api_async("getnum", "POST", {"range": parts[2]})
        if res and res.get("meta", {}).get("status") == "ok":
            num = res["data"].get("full_number") or res["data"].get("number")
            c = get_country_details(num)
            btn = [[InlineKeyboardButton("🔄 Change", callback_data=f"chgnum_{parts[1]}_{parts[2]}")]]
            
            await query.message.edit_text(
                f"🚀 **SUCCESS**\n{c['flag']} {c['name']}\n📱 `+{re.sub(r'\D','',str(num))}`",
                reply_markup=InlineKeyboardMarkup(btn),
                parse_mode=ParseMode.MARKDOWN
            )
            asyncio.create_task(check_otp(context, query.message.chat_id, num))
        else:
            await query.message.edit_text("❌ Server busy, আবার চেষ্টা করুন।")

async def show_services(msg):
    kb = [[InlineKeyboardButton("🔷 FACEBOOK", callback_data="service_facebook")],
          [InlineKeyboardButton("📸 INSTAGRAM", callback_data="service_instagram")]]
    await msg.reply_text("প্ল্যাটফর্ম সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(kb))

async def show_ranges(msg, service):
    res = await call_website_api_async("liveaccess", "GET")
    kb = []
    seen = set()
    for s in res.get("services", []) if res else []:
        if service.lower() in s.get("sid", "").lower():
            for r in s.get("ranges", []):
                p = re.sub(r'\D', '', str(r))[:3]
                if p in COUNTRY_MAP and p not in seen:
                    seen.add(p)
                    kb.append([InlineKeyboardButton(f"{COUNTRY_MAP[p]['flag']} {COUNTRY_MAP[p]['name']}", callback_data=f"range_{service}_{r}")])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
    await msg.reply_text("দেশ সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(kb))

async def text_handler(update, context):
    if not await is_user_subscribed(context, update.effective_user.id):
        return await start(update, context)
    
    text = update.message.text
    if "GET NUMBER" in text:
        await show_services(update.message)
    elif "2FA CODE" in text:
        return await twofa_start(update, context)
    elif "LIVE OTP" in text:
        await update.message.reply_text("📡 LIVE OTP", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("View", url=f"https://t.me/{OTP_CHANNEL.replace('@', '')}")]]))

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
    logging.info("🤖 META FIRE OTP Bot Started!")
    app.run_polling()
