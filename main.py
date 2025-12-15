import telebot
from telebot import types
import os
import random
import threading
import time
import requests
from datetime import datetime

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [7750512181]
FILE_PATH = "files/signed.dll"
SCREENSHOT_FOLDER = "files/screens"
SUPPORT_LINK = "https://t.me/givi_hu"
TRON_ADDRESS = "TL6aNoYs3GN95NGdnJo8b32e5xo2d5sLpU"
TRC20_USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
EXPECTED_USDT = 5.0
CHECK_INTERVAL = 30
LOG_FILE = "log.txt"

bot = telebot.TeleBot(BOT_TOKEN)
EMOJIS = ["😎","🔥","💎","⚡","🚀","🤖","✨","🎯","🛠"]

# ================= КЛЮЧИ =================
KEYS = {
    "TEST123": {"used": False, "multi": False},
}

# ================= СПИСОК ЖДУЩИХ ОПЛАТ =================
waiting_users = {}

# ================= ФУНКЦИИ =================
def log(user, action, key=""):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} | @{user.username if user else 'unknown'} | {user.id if user else 'unknown'} | {action} | {key}\n")

def is_admin(uid):
    return uid in ADMIN_IDS

# ================= START =================
@bot.message_handler(commands=["start"])
def start(message):
    emoji = random.choice(EMOJIS)
    text = f"{emoji} *Приветствую вас, дорогой клиент в mycheat.*\n\nВыберите ниже, что вам нужно 👇"
    
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🔑 Использовать ключ", callback_data="use_key"),
        types.InlineKeyboardButton("💰 Оплатить и получить файл", callback_data="pay"),
        types.InlineKeyboardButton("🖼 Скриншоты", callback_data="screens"),
        types.InlineKeyboardButton("📞 Поддержка", url=SUPPORT_LINK),
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=kb)

# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    cid = call.message.chat.id
    if call.data == "use_key":
        bot.send_message(cid, "🔑 Введите ключ командой:\n/key ВАШ_КЛЮЧ", parse_mode="Markdown")
        log(call.from_user, "CLICK_USE_KEY")
    elif call.data == "pay":
        bot.send_message(cid,
            f"💰 *Оплата*\n\nОтправьте **{EXPECTED_USDT} USDT (TRC20)** на адрес:\n`{TRON_ADDRESS}`\n\nПосле оплаты бот отправит файл автоматически.",
            parse_mode="Markdown"
        )
        waiting_users[cid] = {"notified": False}
        log(call.from_user, "CLICK_PAY_MAIN")
    elif call.data == "screens":
        log(call.from_user, "CLICK_SCREENS")
        if not os.path.exists(SCREENSHOT_FOLDER):
            bot.send_message(cid, "❌ Папка со скриншотами не найдена")
            return
        files = os.listdir(SCREENSHOT_FOLDER)
        if not files:
            bot.send_message(cid, "😢 Скриншоты пока отсутствуют")
            return
        for img in files:
            try:
                with open(os.path.join(SCREENSHOT_FOLDER, img), "rb") as f:
                    bot.send_photo(cid, f)
            except:
                pass

# ================= КЛЮЧ =================
@bot.message_handler(commands=["key"])
def use_key(message):
    try:
        key = message.text.split(" ",1)[1]
    except:
        bot.send_message(message.chat.id, "❌ Используй:\n/key ВАШ_КЛЮЧ")
        return

    if key not in KEYS:
        bot.send_message(message.chat.id, "❌ Неверный ключ")
        return
    if KEYS[key]["used"] and not KEYS[key]["multi"]:
        bot.send_message(message.chat.id, "⚠️ Этот ключ уже использован")
        return

    try:
        with open(FILE_PATH, "rb") as f:
            bot.send_document(message.chat.id, f)
        bot.send_message(message.chat.id, "✅ Файл успешно получен!")
        KEYS[key]["used"] = True
        log(message.from_user, "USED_KEY", key)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

# ================= ПРОВЕРКА ОПЛАТ =================
def check_payments():
    while True:
        try:
            for user_id in list(waiting_users.keys()):
                resp = requests.get(
                    "https://apilist.tronscan.org/api/token_trc20/transfers",
                    params={"address": TRON_ADDRESS, "limit":50}
                ).json()
                for tx in resp.get("data", []):
                    if tx.get("contract_address") == TRC20_USDT_CONTRACT and \
                       tx.get("to_address") == TRON_ADDRESS:
                        amount = int(tx.get("value",0))/1_000_000
                        from_addr = tx.get("from_address")
                        if amount >= EXPECTED_USDT:
                            try:
                                with open(FILE_PATH,"rb") as f:
                                    bot.send_document(user_id,f)
                                bot.send_message(user_id,f"✅ Оплата получена ({amount} USDT) от {from_addr}. Файл отправлен!")
                                log(bot.get_chat(user_id), "PAID_FILE", from_addr)
                                waiting_users.pop(user_id)
                            except:
                                pass
        except Exception as e:
            print("Ошибка проверки платежей:", e)
        time.sleep(CHECK_INTERVAL)

threading.Thread(target=check_payments, daemon=True).start()

# ================= ЗАПУСК =================
bot.infinity_polling()
