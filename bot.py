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

async def call_website_api_async(endpoint, method="POST", payload=None):
    try:
        url = f"https://2eee7.com/@Access/@Bot/2eee7/@public/api/{endpoint}"
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=6.0) as client:
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

def get_country_details(number_str):
    clean_num = re.sub(r'\D', '', str(number_str))
    prefix = clean_num[:3]
    return COUNTRY_MAP.get(prefix, {"name": "Premium Server", "flag": "🌍"})

# ==================== 2FA ====================
async def twofa_start(update: Update, context):
    await update.message.reply_text("🔐 **2FA Secret Key** পাঠান:")
    return SECRET_KEY

async def twofa_generate(update: Update, context):
    secret = update.message.text.strip().upper().replace(" ", "")
    try:
        totp = pyotp.TOTP(secret)
        code = totp.now()
        remaining = 30 - (int(datetime.now().timestamp()) % 30)
        await update.message.reply_text(f"✅ **Code:** `{code}`\n⏱ {remaining} সেকেন্ড", parse_mode=ParseMode.MARKDOWN)
    except:
        await update.message.reply_text("❌ Invalid Secret Key!")
    return ConversationHandler.END

# ==================== OTP ====================
async def check_otp(context, chat_id, number):
    full_number = re.sub(r'\D', '', str(number))
    for _ in range(600):
        await asyncio.sleep(1.0)
        res = await call_website_api_async("success-otp-info", "GET")
        if res and "otps" in res.get("data", {}):
            for item in res["data"]["otps"]:
                if re.sub(r'\D', '', str(item.get("number", ""))).endswith(full_number[-8:]):
                    otp = item.get("otp") or item.get("code") or item.get("sms")
                    if otp:
                        country = get_country_details(number)
                        hidden = f"+{full_number[:6]}{'*'*(len(full_number)-6)}"
                        await context.bot.send_message(chat_id=chat_id, text=f"✅ **OTP RECEIVED**\n📱 `{hidden}`\n🔑 `{otp}`", parse_mode=ParseMode.MARKDOWN)
                        await context.bot.send_message(chat_id=OTP_CHANNEL, text=f"🌟 **NEW OTP**\n{country['flag']} {country['name']}\n📱 `{hidden}`\n🔑 `{otp}`", parse_mode=ParseMode.MARKDOWN)
                        return
    await context.bot.send_message(chat_id=chat_id, text="❌ Timeout!")

# ==================== SERVICES ====================
async def show_services(msg):
    kb = [
        [InlineKeyboardButton("🔷 FACEBOOK 🔷", callback_data="service_facebook")],
        [InlineKeyboardButton("📸 INSTAGRAM 📸", callback_data="service_instagram")]
    ]
    await msg.reply_text("**প্ল্যাটফর্ম সিলেক্ট করুন:**", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def show_ranges(msg, service):
    await msg.edit_text("🔄 দেশ লোড হচ্ছে...")
    res = await call_website_api_async("liveaccess", "GET")
    kb = []
    seen = set()
    target = service.lower()
    
    if res and "services" in res:
        for s in res["services"]:
            sid = s.get("sid", "").lower()
            if target in sid or (target == "instagram" and ("ig" in sid or "inst" in sid)):
                for r in s.get("ranges", []):
                    p = re.sub(r'\D', '', str(r))[:3]
                    if p in COUNTRY_MAP and p not in seen:
                        seen.add(p)
                        kb.append([InlineKeyboardButton(f"{COUNTRY_MAP[p]['flag']} {COUNTRY_MAP[p]['name']}", callback_data=f"range_{service}_{r}")])
    
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_services")])
    if kb:
        await msg.edit_text("**দেশ সিলেক্ট করুন:**", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    else:
        await msg.edit_text("❌ কোন দেশ পাওয়া যায়নি।")

# ==================== CALLBACK ====================
async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()
    global active_otp_tasks

    if query.data == "verify":
        if await is_user_subscribed(context, query.from_user.id):
            await query.message.delete()
            await context.bot.send_message(query.message.chat_id, "✅ ভেরিফাইড!", reply_markup=main_keyboard)

    elif query.data.startswith("service_"):
        await show_ranges(query.message, query.data.split("_")[1])

    elif query.data.startswith("range_") or query.data.startswith("chgnum_"):
        parts = query.data.split("_")
        if query.message.chat_id in active_otp_tasks:
            active_otp_tasks[query.message.chat_id].cancel()
        
        await query.message.edit_text("⚡ নাম্বার অ্যালোকেট হচ্ছে...")
        
        res = await call_website_api_async("getnum", "POST", {"range": parts[2]})
        if res and res.get("meta", {}).get("status") == "ok":
            num = res["data"].get("full_number") or res["data"].get("number")
            c = get_country_details(num)
            btn = [[InlineKeyboardButton("🔄 Change Number", callback_data=f"chgnum_{parts[1]}_{parts[2]}")]]
            
            await query.message.edit_text(
                f"🚀 **NUMBER ALLOCATED**\n\n{c['flag']} **{c['name']}**\n📱 `+{re.sub(r'\D', '', str(num))}`\n⏳ OTP-এর জন্য অপেক্ষা...",
                reply_markup=InlineKeyboardMarkup(btn),
                parse_mode=ParseMode.MARKDOWN
            )
            active_otp_tasks[query.message.chat_id] = asyncio.create_task(check_otp(context, query.message.chat_id, num))
        else:
            await query.message.edit_text("❌ Server Busy!")

    elif query.data == "back_to_services":
        await query.message.delete()
        await show_services(query.message)

# ==================== TEXT HANDLER ====================
async def text_handler(update, context):
    if not await is_user_subscribed(context, update.effective_user.id):
        return await start(update, context)
    
    text = update.message.text
    if "GET NUMBER" in text:
        await show_services(update.message)
    elif "2FA CODE" in text:
        return await twofa_start(update, context)
    elif "LIVE OTP" in text:
        await update.message.reply_text("📡 LIVE OTP SECTION", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("View Live", url=f"https://t.me/{OTP_CHANNEL.replace('@', '')}")]]))

# ==================== START ====================
async def start(update, context):
    if not await is_user_subscribed(context, update.effective_user.id):
        kb = [[InlineKeyboardButton("Join Update", url=f"https://t.me/{UPDATE_CHANNEL.replace('@', '')}")],
              [InlineKeyboardButton("Join OTP", url=f"https://t.me/{OTP_CHANNEL.replace('@', '')}")],
              [InlineKeyboardButton("✅ Verify", callback_data="verify")]]
        await update.message.reply_text("চ্যানেলে জয়েন করে Verify করুন।", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text("✅ স্বাগতম!", reply_markup=main_keyboard)

# ==================== RUN ====================
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
