import telebot
from telebot import types
import json

bot = telebot.TeleBot('token', parse_mode='HTML')

CHANNEL_ID = channel_id
MESSAGES_FILE = 'messages.json'
BANNED_USERS_FILE = 'banned_users.json'
BOT_MESSAGES_FILE = 'bot_messages.json'
admin_id = id


@bot.message_handler(commands=['test'])
def test(message):
    bot.send_message (message.from_user.id, "Bot is working!")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id == admin_id:
        try:
            unique_id = message.text.split()[1]
            if len(unique_id) < 4:
                user_id = banned_users.get(unique_id)
                if user_id:
                    del banned_users[unique_id]
                    save_data(BANNED_USERS_FILE, banned_users)
                    bot.reply_to(message, f"The user was unbanned.")
                else:
                    bot.reply_to(message, "The user was not found in the banned users list.")
            else:
                user_id = unique_id
                for uid, tid in list(banned_users.items()):
                    if tid == user_id:
                        del banned_users[uid]
                        save_data(BANNED_USERS_FILE, banned_users)
                        bot.reply_to(message, f"The user was unbanned.")
                        break
                else:
                    bot.reply_to(message, "The user was not found in the banned users list.")
        except (IndexError, ValueError):
            bot.reply_to(message, 'Use this command in the "/unban {unique_id}" format')

def load_data(file):
    try:
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_data(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


def is_banned(user_id):
    return str(user_id) in banned_users.values()

messages = load_data(MESSAGES_FILE)
banned_users = load_data(BANNED_USERS_FILE)
bot_messages = load_data(BOT_MESSAGES_FILE)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.from_user.id != admin_id:
        bot.reply_to(message,
                     f'Hi, <b>{message.from_user.first_name}</b>, this is the personal anonymous questions bot for ...! Write your question below')
    else:
        bot.send_message(message.from_user.id,
                         f'Hello, <b>{message.from_user.first_name}</b>, this is your personal bot for anonymous questions!')


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if is_banned(message.from_user.id):
        bot.reply_to(message, "You were banned so you can't send messages.")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    reply_button = types.InlineKeyboardButton("Answer personally 💬", callback_data=f"reply_{message.from_user.id}")
    channel_button = types.InlineKeyboardButton("Send to the channel 📣", callback_data=f"channel_{message.message_id}")
    block_button = types.InlineKeyboardButton("Ban user ❌",
                                              callback_data=f"block_{message.from_user.id}")
    markup.add(reply_button, channel_button, block_button)
    sent_message = bot.send_message(admin_id, f'<b>New anonymous question!</b>\n\n"{message.text}"',
                                    reply_markup=markup)
    bot_messages[str(sent_message.message_id)] = {
        'original_message_id': message.message_id,
        'user_id': message.from_user.id,
        'message_text': message.text
    }
    save_data(BOT_MESSAGES_FILE, bot_messages)

    messages[str(message.message_id)] = {
        'user_id': message.from_user.id,
        'message': message.text
    }
    save_data(MESSAGES_FILE, messages)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    data = call.data.split('_')
    action = data[0]
    target_id = data[1]
    bot_message_id = call.message.message_id
    bot_message_data = bot_messages.get(str(bot_message_id), {})
    user_message_text = bot_message_data.get('message_text', "The original message is not found.")


    if action == "reply":
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=bot_message_id, text=f'<b>New anonymous question:</b>\n"{user_message_text}" \n\nYou have chosen to respond personally. Write your answer below:')
        def send_reply(msg):
            if str(msg.chat.id) == str(call.message.chat.id):
                user_id = int(target_id)
                bot.send_message(user_id, f'<b>The answer of admin:</b>\n\n"{msg.text}"', parse_mode='HTML')
                bot.reply_to(msg, "The answer was sent to the user!")
                bot.clear_step_handler_by_chat_id(chat_id=msg.chat.id)


        bot.register_next_step_handler(call.message, send_reply)

    elif action == "channel":
        original_message_id = None
        for msg_id, data in bot_messages.items():
            if data.get('original_message_id') == int(target_id):
                original_message_id = msg_id
                break

        if original_message_id:
            bot.forward_message(CHANNEL_ID, call.message.chat.id, int(original_message_id))
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=bot_message_id,
                text=f'<b>Anonymous question:</b>\n"{user_message_text}" \n\nThe message was sent to the channel!'
            )
        else:
            bot.reply_to(call.message, "The original message is not found.")

    elif action == "block":
        global next_unique_id
        unique_id = next_unique_id
        banned_users[str(unique_id)] = str(target_id)
        next_unique_id += 1
        save_data(BANNED_USERS_FILE, banned_users)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=bot_message_id,
            text=f'<b>Anonymous question:</b>\n"{user_message_text}" \n\nThe sender was banned. Unique ID for unban: {unique_id}. <i>*Use the command "/unban {unique_id}" to unban the sender.</i>'
        )


bot.infinity_polling(none_stop=True)
