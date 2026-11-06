import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
from flask import Flask
import threading

TOKEN = '9252854683:AAEHi3fTz5YvObtmdjxpXYEKtujosD7upio'
bot = telebot.TeleBot(TOKEN)
user_states = {}

# Render Web Service အတွက် Web Server
app = Flask('')

@app.route('/')
def home():
    return "Bot is running live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_states[chat_id] = {'step': 'waiting_for_movie'}
    bot.send_message(
        chat_id, 
        "🎬 မင်္ဂလာပါ! ကျွန်ုပ်တို့၏ ဗီဒီယို ဒေါင်းလုဒ် Bot မှ ကြိုဆိုပါတယ်ခင်ဗျာ။\n\nကျေးဇူးပြု၍ ဒေါင်းလုဒ်လုပ်လိုသော **ဇာတ်ကားအမည် သို့မဟုတ် Link** ကို ပို့ပေးပါ။"
    )

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
        f"🔍 သင်ပေးပို့ထားသော အချက်: *{movie_name}*\n\nဤဇာတ်ကားသည် အပိုင်းတွဲ (Series) လား၊ သို့မဟုတ် ကားတစ်ကားတည်း (Single) လား?",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    data = call.data
    movie_input = user_states.get(chat_id, {}).get('movie', '')
    
    if data == "type_single":
        bot.answer_callback_query(call.id, "Single Movie ကို ရွေးချယ်ပြီးပါပြီ။")
        bot.send_message(chat_id, f"⏳ ဗီဒီယိုကို ဒေါင်းလုဒ်လုပ်နေပါပြီ၊ ခဏစောင့်ပါ...")
        download_and_send(chat_id, movie_input, is_playlist=False)
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
        bot.send_message(chat_id, f"⏳ ပလေးလစ်/အပိုင်းအားလုံး ကို ဒေါင်းလုဒ်လုပ်နေပါပြီ...")
        download_and_send(chat_id, movie_input, is_playlist=True)
        user_states[chat_id] = {}
        
    elif data == "ep_specific":
        bot.answer_callback_query(call.id, "သီးသန့်အပိုင်းကို ရွေးချယ်ပါ။")
        user_states[chat_id]['step'] = 'waiting_for_ep_number'
        bot.send_message(chat_id, "🔢 ကျေးဇူးပြု၍ လိုချင်သည့် **အပိုင်းနံပါတ်** ကို ရိုက်ထည့်ပေးပါ (ဥပမာ - 1)")

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get('step') == 'waiting_for_ep_number')
def handle_episode_number(message):
    chat_id = message.chat.id
    ep_number = message.text
    movie_input = user_states.get(chat_id, {}).get('movie', '')
    bot.send_message(chat_id, f"⏳ အပိုင်း ({ep_number}) ကို ဒေါင်းလုဒ်လုပ်နေပါပြီ၊ ခဏစောင့်ပါ...")
    download_and_send(chat_id, movie_input, episode=ep_number)
    user_states[chat_id] = {}

def download_and_send(chat_id, query_or_url, is_playlist=False, episode=None):
    try:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': 'downloaded_video.%(ext)s',
            'noplaylist': not is_playlist,
        }
        
        if episode:
            ydl_opts['noplaylist'] = False
            ydl_opts['playlist_items'] = str(episode)

        target = query_or_url
        if not query_or_url.startswith('http'):
            target = f"ytsearch1:{query_or_url}"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target, download=True)
            if 'entries' in info:
                # Playlist ဖြစ်နေရင် ပထမဆုံးဗီဒီယို (သို့မဟုတ် အခြားဖိုင်) ကို ရှာရန်
                filename = ydl.prepare_filename(info['entries'][0])
            else:
                filename = ydl.prepare_filename(info)

        if os.path.exists(filename):
            bot.send_message(chat_id, "📤 ဒေါင်းလုဒ်ပြီးပါပြီ၊ သင့်ဆီသို့ ပို့ဆောင်နေပါပြီ...")
            with open(filename, 'rb') as video:
                bot.send_video(chat_id, video)
            os.remove(filename)  # ဖိုင်ပို့ပြီးရင် Server ပေါ်ကနေ ဖျက်မည်
        else:
            bot.send_message(chat_id, "❌ ဒေါင်းလုဒ်လုပ်၍မရပါ။ ဖိုင်မတွေ့ပါ။")
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ အမှားအယွင်း ဖြစ်ပေါ်သွားပါသည်: {str(e)}")

if __name__ == '__main__':
    t = threading.Thread(target=run_flask)
    t.start()
    bot.infinity_polling()
