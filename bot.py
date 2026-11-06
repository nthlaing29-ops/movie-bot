import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# သင့်ရဲ့ Bot Token ထည့်သွင်းပြီးပါပြီ
TOKEN = '9252854683:AAEHi3fTz5YvObtmdjxpXYEKtujosD7upio'
bot = telebot.TeleBot(TOKEN)

# အသုံးပြုသူ တစ်ဦးချင်းစီရဲ့ အခြေအနေ (State) ကို မှတ်သားရန်
user_states = {}

# ၁။ /start နှိပ်လိုက်လျှင် ကြိုဆိုစကားပြောပြီး ဇာတ်ကားအမည် မေးမည်
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_states[chat_id] = {'step': 'waiting_for_movie'}
    
    bot.send_message(
        chat_id, 
        "🎬 မင်္ဂလာပါ! ကျွန်ုပ်တို့၏ ဗီဒီယို ဒေါင်းလုဒ် Bot မှ ကြိုဆိုပါတယ်ခင်ဗျာ။\n\nကျေးဇူးပြု၍ ဒေါင်းလုဒ်လုပ်လိုသော **ဇာတ်ကားအမည် သို့မဟုတ် Link** ကို ပို့ပေးပါ။"
    )

# ၂။ ဇာတ်ကားအမည် လက်ခံရရှိပြီး အပိုင်းတွဲ/ကားတစ်ကားတည်း ဟုတ်မဟုတ် မေးမည်
@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get('step') == 'waiting_for_movie')
def ask_movie_type(message):
    chat_id = message.chat.id
    movie_name = message.text
    
    user_states[chat_id]['movie'] = movie_name
    user_states[chat_id]['step'] = 'waiting_for_series_choice'
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🎬 ကားတစ်ကားတည်း (Single Movie)", callback_data="type_single"),
        InlineKeyboardButton("📺 အပိုင်းတွဲ (Series)", callback_data="type_series")
    )
    
    bot.send_message(
        chat_id, 
        f"🔍 သင်ရှာထားသော ဇာတ်ကား: *{movie_name}*\n\nဤဇာတ်ကားသည် အပိုင်းတွဲ (Series) လား၊ သို့မဟုတ် ကားတစ်ကားတည်း (Single) လား?",
        parse_mode="Markdown",
        reply_markup=markup
    )

# ၃။ ခလုတ်နှိပ်မှုများ (Inline Callbacks) ကို စစ်ဆေးခြင်း
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    data = call.data
    
    if data == "type_single":
        bot.answer_callback_query(call.id, "Single Movie ကို ရွေးချယ်ပြီးပါပြီ။")
        movie_name = user_states.get(chat_id, {}).get('movie', '')
        bot.send_message(chat_id, f"⏳ *{movie_name}* (Single Movie) ကို ဒေါင်းလုဒ်လုပ်နေပါပြီ၊ ခဏစောင့်ပါ...")
        
        # ဤနေရာတွင် yt-dlp ဖြင့် Single Link ကို ဒေါင်းလုပ်ဆွဲသည့် ကုဒ်ထည့်နိုင်ပါသည်
        user_states[chat_id] = {}
        
    elif data == "type_series":
        bot.answer_callback_query(call.id, "Series ကို ရွေးချယ်ပြီးပါပြီ။")
        user_states[chat_id]['step'] = 'waiting_for_episode_choice'
        
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("📥 အပိုင်းအားလုံး (All Episodes)", callback_data="ep_all"),
            InlineKeyboardButton("🔢 သီးသန့်အပိုင်းရွေးမည် (Specific Episode)", callback_data="ep_specific")
        )
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="📁 ဤအပိုင်းတွဲအတွက် အပိုင်းအားလုံး Download လုပ်မှာလား၊ သို့မဟုတ် သီးသန့်အပိုင်းကို ရွေးချယ်မှာလား?",
            reply_markup=markup
        )
        
    elif data == "ep_all":
        bot.answer_callback_query(call.id, "အပိုင်းအားလုံးကို ရွေးချယ်ပြီးပါပြီ။")
        movie_name = user_states.get(chat_id, {}).get('movie', '')
        bot.send_message(chat_id, f"⏳ *{movie_name}* ၏ **အပိုင်းအားလုံး** ကို ဒေါင်းလုဒ်လုပ်နေပါပြီ...")
        user_states[chat_id] = {}
        
    elif data == "ep_specific":
        bot.answer_callback_query(call.id, "သီးသန့်အပိုင်းကို ရွေးချယ်ပါ။")
        user_states[chat_id]['step'] = 'waiting_for_ep_number'
        bot.send_message(chat_id, "🔢 ကျေးဇူးပြု၍ လိုချင်သည့် **အပိုင်းနံပါတ်** ကို ရိုက်ထည့်ပေးပါ (ဥပမာ - ၅ သို့မဟုတ် 5)")

# ၄။ သီးသန့်အပိုင်းနံပါတ် ရိုက်ထည့်လာသည့်အခါ လက်ခံခြင်း
@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get('step') == 'waiting_for_ep_number')
def handle_episode_number(message):
    chat_id = message.chat.id
    ep_number = message.text
    movie_name = user_states.get(chat_id, {}).get('movie', '')
    
    bot.send_message(chat_id, f"⏳ *{movie_name}* ၏ **အပိုင်း ({ep_number})** ကို ဒေါင်းလုဒ်လုပ်နေပါပြီ၊ ခဏစောင့်ပါ...")
    
    user_states[chat_id] = {}

# Bot ကို စတင်အလုပ်လုပ်စေခြင်း
bot.infinity_polling()
