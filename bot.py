import logging
import re
import os
import httpx
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackQueryHandler
from telegram.constants import ParseMode
from dotenv import load_dotenv

load_dotenv()

# ==================== LOAD FROM .env ====================
TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("SMS_API_KEY")
# =======================================================

# ==================== CHANNELS & BOT ====================
UPDATE_CHANNEL = "@META_FIRE_UPDATE"
OTP_CHANNEL = "@META_FIRE_OTP"
BOT_USERNAME = "Meta_Fire_OTP_Bot"
# =======================================================

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

main_keyboard = ReplyKeyboardMarkup([
    [KeyboardButton("🔥 GET NUMBER 🔥")],
    [KeyboardButton("🔐 2FA CODE"), KeyboardButton("📡 LIVE OTP SECTION")]
], resize_keyboard=True, is_persistent=True)

COUNTRY_MAP = {
    "232": {"name": "Sierra Leone", "flag": "🇸🇱"},
    "224": {"name": "Guinea", "flag": "🇬🇳"},
    "225": {"name": "Ivory Coast", "flag": "🇨🇮"}
}

def get_country_details(number_str):
    clean_num = re.sub(r'\D', '', str(number_str))
    prefix = clean_num[:3]
    return COUNTRY_MAP.get(prefix, {"name": "Premium Server", "flag": "🌍"})

async def call_website_api_async(endpoint, method="POST", payload=None):
    try:
        url = f"https://2eee7.com/@Access/@Bot/2eee7/@public/api/{endpoint}"
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json", "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=8.0) as client:
            if method == "GET":
                r = await client.get(url, headers=headers)
            else:
                r = await client.post(url, json=payload, headers=headers)
          
            if r.status_code != 200:
                logging.warning(f"API {endpoint} failed: {r.status_code}")
                return None
            return r.json()
    except Exception as e:
        logging.error(f"API call error: {e}")
        return None

async def is_user_subscribed(context, user_id):
    try:
        m1 = await context.bot.get_chat_member(chat_id=UPDATE_CHANNEL, user_id=user_id)
        m2 = await context.bot.get_chat_member(chat_id=OTP_CHANNEL, user_id=user_id)
        return m1.status not in ['left', 'kicked'] and m2.status not in ['left', 'kicked']
    except:
        return False

async def check_otp(context, chat_id, number, username=None):
    full_number = re.sub(r'\D', '', str(number))
    logging.info(f"🔍 Monitoring OTP for +{full_number}")
  
    for attempt in range(900):
        await asyncio.sleep(2)
      
        try:
            res = await call_website_api_async("success-otp-info", method="GET")
          
            if res and "data" in res and "otps" in res.get("data", {}):
                for item in res["data"]["otps"]:
                    item_num = re.sub(r'\D', '', str(item.get("number", "")))
                    if item_num == full_number or item_num.endswith(full_number[-8:]):
                        otp = item.get("otp") or item.get("code") or item.get("sms")
                        if otp:
                            visible = full_number[:6] if len(full_number) > 6 else full_number
                            hidden_number = f"+{visible}{'*' * (len(full_number) - len(visible))}"
                            country = get_country_details(number)
                          
                            public_text = f"""
🌟 **META FIRE OTP** 🌟
🔥 **NEW OTP RECEIVED** 🔥
{country['flag']} **{country['name']}**
📱 **Number:** `{hidden_number}`
🔑 **OTP Code:** `{otp}`
⏱ **Time Taken:** {attempt*2} seconds
🕒 **Time:** {datetime.now().strftime('%I:%M:%S %p')}
                            """
                          
                            keyboard = InlineKeyboardMarkup([
                                [InlineKeyboardButton("🔄 OTP বটে নিয়ে আসুন", url=f"https://t.me/{BOT_USERNAME}")],
                                [InlineKeyboardButton("📢 আপডেট গ্রুপে যান", url=f"https://t.me/{UPDATE_CHANNEL.replace('@', '')}")]
                            ])
                          
                            await context.bot.send_message(
                                chat_id=OTP_CHANNEL,
                                text=public_text.strip(),
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=keyboard
                            )
                          
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"✅ **OTP RECEIVED SUCCESSFULLY!**\n\n📱 `+{number}`\n🔑 `{otp}`",
                                parse_mode=ParseMode.MARKDOWN
                            )
                            logging.info(f"✅ OTP Sent: {otp}")
                            return
        except Exception as e:
            logging.error(f"OTP check error: {e}")
            continue
  
    await context.bot.send_message(chat_id=chat_id, text=f"❌ **TIMEOUT!** No OTP received for `+{number}`")

async def start(update, context):
    user_id = update.effective_user.id
    if not await is_user_subscribed(context, user_id):
        kb = [[InlineKeyboardButton("📢 Join Update Channel", url=f"https://t.me/{UPDATE_CHANNEL.replace('@', '')}")],
              [InlineKeyboardButton("📢 Join OTP Channel", url=f"https://t.me/{OTP_CHANNEL.replace('@', '')}")],
              [InlineKeyboardButton("✅ ভেরিফাই", callback_data="verify")]]
        await update.message.reply_text("বটটি ব্যবহার করতে প্রথমে আমাদের গ্রুপগুলোতে জয়েন করুন এবং নিচে ভেরিফাই বাটনে ক্লিক করুন।", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text("আপনি ভেরিফাইড ইউজার। নিচে থেকে সার্ভিস সিলেক্ট করুন।", reply_markup=main_keyboard)

async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()
  
    if query.data == "verify":
        if await is_user_subscribed(context, query.from_user.id):
            await query.message.delete()
            await context.bot.send_message(chat_id=query.message.chat_id, text="স্বাগতম! আপনি এখন সকল সুবিধা ব্যবহার করতে পারবেন।", reply_markup=main_keyboard)
        else:
            await query.answer("আপনি এখনও জয়েন করেননি!", show_alert=True)
  
    elif query.data.startswith("range_") or query.data.startswith("chgnum_"):
        parts = query.data.split("_")
        if query.message.chat_id in active_otp_tasks:  # Note: active_otp_tasks needs to be defined globally
            active_otp_tasks[query.message.chat_id].cancel()
      
        status_msg = await query.message.edit_text("⚡ _Allocating number..._")
        res = await call_website_api_async("getnum", method="POST", payload={"range": parts[2]})
        if res and res.get("meta", {}).get("status") == "ok":
            num = res["data"].get("full_number", res["data"].get("number"))
            c = get_country_details(num)
            btn = [[InlineKeyboardButton("🔄 Change Number", callback_data=f"chgnum_{parts[1]}_{parts[2]}")]]
            await status_msg.edit_text(f"🚀 **NUMBER ALLOCATED**\n\n📍 COUNTRY: {c['flag']} {c['name']}\n📱 PHONE: `+{re.sub(r'\D', '', str(num))}`\n⏳ STATUS: Waiting for OTP...", reply_markup=InlineKeyboardMarkup(btn), parse_mode=ParseMode.MARKDOWN)
            active_otp_tasks[query.message.chat_id] = asyncio.create_task(
                check_otp(context, query.message.chat_id, num, query.from_user.username)
            )
        else:
            await status_msg.edit_text("❌ Server Busy!")

    elif query.data == "back_to_services":
        await query.message.delete()
        await show_services(query.message)
    elif query.data.startswith("service_"):
        await query.message.delete()
        await show_ranges(query.message, query.data.split("_")[1])

async def show_services(msg):
    kb = [[InlineKeyboardButton("🔷 FACEBOOK 🔷", callback_data="service_facebook")],
          [InlineKeyboardButton("📸 INSTAGRAM 📸", callback_data="service_instagram")]]
    await msg.reply_text("Select platform:", reply_markup=InlineKeyboardMarkup(kb))

async def show_ranges(msg, service):
    res = await call_website_api_async("liveaccess", method="GET")
    kb = []
    seen = set()
    target_service = service.lower()
    for s in res.get("services", []):
        if target_service in s["sid"].lower() or (target_service == "instagram" and "ig" in s["sid"].lower()):
            for r in s.get("ranges", []):
                p = re.sub(r'\D', '', str(r))[:3]
                if p in COUNTRY_MAP and p not in seen:
                    seen.add(p)
                    kb.append([InlineKeyboardButton(f"{COUNTRY_MAP[p]['flag']} {COUNTRY_MAP[p]['name']}", callback_data=f"range_{service}_{r}")])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_services")])
    await msg.reply_text("Select Country:", reply_markup=InlineKeyboardMarkup(kb))

async def text_handler(update, context):
    if await is_user_subscribed(context, update.effective_user.id):
        text = update.message.text
        if "GET NUMBER" in text:
            await show_services(update.message)
        elif "2FA" in text:
            await update.message.reply_text("Maintenance Mode.")
        elif "LIVE OTP" in text:
            await update.message.reply_text("Join Channel:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📡 View Live", url=f"https://t.me/{OTP_CHANNEL.replace('@', '')}")]]))
    else:
        await start(update, context)

# Global variable for active tasks
active_otp_tasks = {}

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(MessageHandler(filters.TEXT, text_handler))

if __name__ == "__main__":
    logging.info("🤖 META FIRE OTP Bot Started Successfully!")
    app.run_polling() 
