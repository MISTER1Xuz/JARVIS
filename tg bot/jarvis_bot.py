# -*- coding: utf-8 -*-
"""
JARVIS TELEGRAM BOT
--------------------
SHAXSIY CHATDA:
- OWNER offline bo'lganda, botga yozgan odamlarga qiziqarli matn + emoji +
  (agar mavjud bo'lsa) stiker bilan javob beradi.
- Botga kim yozmasin, xabari OWNER'ga forward qilinadi.
- OWNER forward qilingan xabarga REPLY qilsa, javobi avtomatik
  o'sha yuboruvchiga yetkaziladi (ikki tomonlama chat kabi ishlaydi).
- OWNER botga stiker yuborsa, u stiker avtomatik "kutubxona"ga qo'shiladi.

GURUHDA:
- Bot guruhga qo'shilganda salomlashadi va o'zini guruhlar ro'yxatiga saqlaydi.
- Guruh xabarlariga tasodifiy foizda qiziqarli javob/stiker beradi (guruhni "jonlantiradi").
- Bot mention/reply qilinsa - doim javob beradi.
- Kimdir xabarida OWNER_NAME tilga olinsa (masalan "sarvar") - OWNER'ga xabar beriladi.
- OWNER /offline holatida bo'lsa, bot vaqti-vaqti bilan (job_queue orqali)
  guruhlarga o'zi qiziqarli xabar/stiker yuborib, guruhni faol tutadi.
- Har kuni ertalab va kechqurun avtomatik salom/tilak yuboradi.

Buyruqlar (faqat OWNER uchun, shaxsiy chatda):
  /online    - statusni "online" qilish
  /offline   - statusni "offline" qilish (auto-javoblar + guruh faolligi yoqiladi)
  /status    - joriy holatni ko'rish
  /stickers  - saqlangan stikerlar sonini ko'rish
  /guruhlar  - bot a'zo bo'lgan guruhlar ro'yxati
"""

import json
import logging
import random
import os
import datetime

from telegram import Update
from telegram.constants import ChatType
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    filters,
)

# ============== SOZLAMALAR ==============
BOT_TOKEN = "8582856691:AAE0M5kAui6SPduhBtSo52e0SXQRiJ8RCPA"   # BotFather bergan token
OWNER_ID = 7693531132                      # @userinfobot bergan sening ID'ing
OWNER_NAME = "sarvar"                     # guruhda shu so'z aytilsa, senga xabar beradi (kichik harf)
STORAGE_FILE = "storage.json"
GROUP_REPLY_CHANCE = 0.20                 # guruhda tasodifiy javob berish ehtimoli (0.20 = 20%)
GROUP_ACTIVITY_INTERVAL_SEC = 2 * 60 * 60 # har 2 soatda guruhni "jonlantirish" urinishi
GROUP_ACTIVITY_CHANCE = 0.5               # har urinishda har bir guruhga yuborish ehtimoli

# O'zbekiston vaqti (UTC+5)
TASHKENT_TZ = datetime.timezone(datetime.timedelta(hours=5))
MORNING_TIME = datetime.time(hour=7, minute=30, tzinfo=TASHKENT_TZ)   # ertalabki salom vaqti
EVENING_TIME = datetime.time(hour=22, minute=0, tzinfo=TASHKENT_TZ)   # kechqurungi tilak vaqti
# ==========================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("jarvis")

# Xabarni forward qilganda: {forward_qilingan_msg_id: yuboruvchi_chat_id}
reply_map = {}

FUNNY_REPLIES = [
    "Assalomu alaykum! 👋 Sarvar hozir bandroq, lekin men — Jarvis — shu yerdaman 🤖 Nima gap?",
    "Salom-salom! Xo'jayin hozir oflayn, lekin zerikmang, men bor-ku 😎🔥",
    "Sarvar hozir band, telefoniga qarab o'tiribdi shekilli 📵😂 Menga yozavering, hammasini yetkazaman!",
    "Bip-bip 🤖 Jarvis eshitmoqda... Sarvar tez orada javob beradi, hozircha men bilan gaplashamiz 😄",
    "Salom! Bu yerda sun'iy intellekt ishlayapti, lekin his-tuyg'ular original 😅 Nima bo'lyapti?",
    "Sarvar hozir yo'q, lekin xabaringiz to'g'ridan-to'g'ri unga yetadi 📩 Jarvis kafolat beradi!",
    "Hey! 👀 Bu yerda Jarvis navbatchilik qilyapti. Sarvar qaytganda albatta javob beradi!",
    "Xo'jayin oflayn rejimda 😴 lekin men doim aktivman. Yozavering, zerikmaysiz! 🎉",
    "Salom, do'stim! 🤝 Sarvar hozir band, lekin men bilan chatlashib turing, u ko'radi hammasini!",
    "Pling! 🔔 Yangi xabar qabul qilindi. Sarvar tez orada bog'lanadi, hozircha Jarvis xizmatingizda 😉",
]

GROUP_REPLIES = [
    "Nimalar bo'lyapti bu yerda? 👀🔥",
    "Guruh jonlanyapti-ku, zo'r! 😄🎉",
    "Jarvis kuzatib turibdi... hammasi nazoratda 🤖✨",
    "Qiziq gap ketyapti-a? Davom eting! 😂",
    "Mana bu gap! 👏 Kim yana nima deydi?",
    "Sukunat yomon, gaplashish yaxshi 😎🗣️",
    "Bugun kayfiyat zo'r ko'rinadi! 🚀😄",
    "Jarvis roziligini bildiradi 🤖👍",
]

GROUP_ACTIVITY_MESSAGES = [
    "Guruh judayam jim qoldi-ku 👀 Kim nima gap, aytinglar-chi! 🎉",
    "Hey hammaga salom! 👋 Bugun kayfiyatlar qanday? 😄",
    "Zerikish taqiqlanadi bu guruhda! 🚫😴 Kim qiziq voqea aytadi?",
    "Jarvis faollik nazoratchisi sifatida: gaplashish vaqti keldi! 🔥🗣️",
    "Salom, jamoa! 🤖 Bugun eng kulgili voqeani kim aytadi? 😂",
]

MORNING_MESSAGES = [
    "Assalomu alaykum, hurmatli jamoa! ☀️ Yangi kun boshlandi, kayfiyatlar zo'r bo'lsin! 🌅💪",
    "Xayrli tong! 🌞 Bugun ham ajoyib kun bo'lsin, barchaga omad va yaxshi kayfiyat! ☕😄",
    "Tong yorishdi! 🌄 Barchaga baraka va yaxshi kunlar tilaymiz! 🙌✨",
    "Salom, quyoshli jamoa! ☀️ Yangi kun - yangi imkoniyatlar. Omad hammaga! 🚀😊",
    "Xayrli tong! 🌅 Choy-qahvangiz shirin, kuningiz baraka bilan to'lsin! ☕🎉",
]

EVENING_MESSAGES = [
    "Hayrli kech, hurmatli jamoa! 🌙 Bugungi kun uchun rahmat, yaxshi dam oling! 😴✨",
    "Kech kirdi 🌆 Bugun ham zo'r kun bo'ldi, ertaga yana ko'rishguncha! 👋🌟",
    "Hayrli kech! 🌃 Charchagan bo'lsangiz, endi dam olish vaqti keldi 😌💤",
    "Kun tugadi, xayrli kech hammaga! 🌙 Tinch tunlar tilaymiz 🌌😊",
    "Hayrli kech! 🌆 Ertangi kun yanada yaxshiroq bo'lsin, hozircha dam oling 😴🌙",
]

EMOJIS = ["🤖", "🔥", "😄", "🎉", "👋", "😎", "✨", "🚀", "😂", "👀", "💬", "📩"]


def load_storage():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
    data.setdefault("status", "offline")
    data.setdefault("stickers", [])
    data.setdefault("groups", [])
    return data


def save_storage(data):
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


storage = load_storage()


def is_owner(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == OWNER_ID


# ============== BUYRUQLAR (shaxsiy chat) ==============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != ChatType.PRIVATE:
        return
    if is_owner(update):
        await update.message.reply_text(
            "Salom, xo'jayin! 🤖 Men Jarvisman.\n\n"
            "/online - onlayn qilib qo'yish\n"
            "/offline - oflayn qilib qo'yish (auto-javoblar + guruh faolligi yoqiladi)\n"
            "/status - holatni ko'rish\n"
            "/stickers - saqlangan stikerlar sonini ko'rish\n"
            "/guruhlar - a'zo bo'lgan guruhlar ro'yxati\n\n"
            "Menga stiker yuborsang, avtomatik kutubxonamga qo'shib olaman 😉"
        )
    else:
        await update.message.reply_text(random.choice(FUNNY_REPLIES))


async def set_online(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update) or update.effective_chat.type != ChatType.PRIVATE:
        return
    storage["status"] = "online"
    save_storage(storage)
    await update.message.reply_text("✅ Holat: ONLINE. Auto-javoblar va guruh faolligi o'chirildi.")


async def set_offline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update) or update.effective_chat.type != ChatType.PRIVATE:
        return
    storage["status"] = "offline"
    save_storage(storage)
    await update.message.reply_text("✅ Holat: OFFLINE. Endi odamlarga va guruhlarga faollik ko'rsataman 😎")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update) or update.effective_chat.type != ChatType.PRIVATE:
        return
    await update.message.reply_text(f"Joriy holat: {storage['status'].upper()}")


async def stickers_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update) or update.effective_chat.type != ChatType.PRIVATE:
        return
    await update.message.reply_text(f"Kutubxonada {len(storage['stickers'])} ta stiker bor 🎨")


async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update) or update.effective_chat.type != ChatType.PRIVATE:
        return
    if not storage["groups"]:
        await update.message.reply_text("Hali hech qanday guruhga qo'shilmaganman.")
        return
    lines = []
    for gid in storage["groups"]:
        try:
            chat = await context.bot.get_chat(gid)
            lines.append(f"• {chat.title} ({gid})")
        except Exception:
            lines.append(f"• {gid}")
    await update.message.reply_text("Guruhlar:\n" + "\n".join(lines))


# ============== SHAXSIY CHAT LOGIKASI ==============

async def handle_owner_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.sticker.file_id
    if file_id not in storage["stickers"]:
        storage["stickers"].append(file_id)
        save_storage(storage)
    await update.message.reply_text(
        f"✅ Stiker kutubxonaga qo'shildi! Jami: {len(storage['stickers'])} ta"
    )


async def handle_owner_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    replied_msg_id = update.message.reply_to_message.message_id
    target_chat_id = reply_map.get(replied_msg_id)

    if target_chat_id is None:
        await update.message.reply_text(
            "⚠️ Bu xabar kimga tegishli ekanini topa olmadim (eski bo'lishi mumkin)."
        )
        return

    if update.message.text:
        await context.bot.send_message(chat_id=target_chat_id, text=update.message.text)
    elif update.message.sticker:
        await context.bot.send_sticker(chat_id=target_chat_id, sticker=update.message.sticker.file_id)
    elif update.message.photo:
        await context.bot.send_photo(chat_id=target_chat_id, photo=update.message.photo[-1].file_id,
                                      caption=update.message.caption or "")
    else:
        await context.bot.copy_message(
            chat_id=target_chat_id,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
        )

    await update.message.reply_text("✅ Yuborildi!")


async def handle_private_incoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    info_text = f"📩 Yangi xabar!\n👤 {user.full_name} (@{user.username or 'yoq'}, id: {user.id})"
    await context.bot.send_message(chat_id=OWNER_ID, text=info_text)
    forwarded = await context.bot.forward_message(
        chat_id=OWNER_ID,
        from_chat_id=update.effective_chat.id,
        message_id=update.message.message_id,
    )
    reply_map[forwarded.message_id] = update.effective_chat.id

    if storage["status"] == "offline":
        reply = random.choice(FUNNY_REPLIES) + " " + random.choice(EMOJIS)
        await update.message.reply_text(reply)
        if storage["stickers"] and random.random() < 0.3:
            sticker = random.choice(storage["stickers"])
            await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=sticker)


# ============== GURUH LOGIKASI ==============

async def on_bot_added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot guruhga qo'shilganda yoki guruhdan chiqarilganda ishlaydi."""
    result = update.my_chat_member
    chat_id = result.chat.id
    new_status = result.new_chat_member.status

    if new_status in ("member", "administrator"):
        if chat_id not in storage["groups"]:
            storage["groups"].append(chat_id)
            save_storage(storage)
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Salom hammaga! 🤖 Men Jarvisman — Sarvarning yordamchisiman.\n"
                     "Bu yerda faollikni ushlab turaman, gaplashaveringlar! 🎉\n\n"
                     "⚠️ Eslatma: guruh xabarlarini to'liq ko'rishim uchun @BotFather'da "
                     "Group Privacy o'chirilgan bo'lishi kerak.",
            )
        except Exception as e:
            logger.warning("Guruhga salom yuborib bo'lmadi: %s", e)

    elif new_status in ("left", "kicked"):
        if chat_id in storage["groups"]:
            storage["groups"].remove(chat_id)
            save_storage(storage)


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    text_lower = msg.text.lower()
    bot_username = (context.bot.username or "").lower()

    is_mentioned = (
        (msg.reply_to_message and msg.reply_to_message.from_user
         and msg.reply_to_message.from_user.id == context.bot.id)
        or (bot_username and f"@{bot_username}" in text_lower)
    )

    # Agar OWNER nomi tilga olinsa - OWNER'ga xabar beramiz
    if OWNER_NAME in text_lower:
        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"🔔 Sizni guruhda tilga olishdi!\n"
                     f"Guruh: {update.effective_chat.title}\n"
                     f"Kimdan: {msg.from_user.full_name}\n"
                     f"Xabar: {msg.text}",
            )
        except Exception as e:
            logger.warning("Owner'ga xabar yuborib bo'lmadi: %s", e)

    should_reply = is_mentioned or (
        storage["status"] == "offline" and random.random() < GROUP_REPLY_CHANCE
    )

    if should_reply:
        reply = random.choice(GROUP_REPLIES) + " " + random.choice(EMOJIS)
        await msg.reply_text(reply)
        if storage["stickers"] and random.random() < 0.2:
            sticker = random.choice(storage["stickers"])
            await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=sticker)


async def morning_greeting_job(context: ContextTypes.DEFAULT_TYPE):
    """Har kuni ertalab barcha guruhlarga salom yuboradi."""
    text = random.choice(MORNING_MESSAGES)
    for chat_id in storage["groups"]:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
            if storage["stickers"]:
                await context.bot.send_sticker(chat_id=chat_id, sticker=random.choice(storage["stickers"]))
        except Exception as e:
            logger.warning("Ertalabki salomni yuborib bo'lmadi (%s): %s", chat_id, e)


async def evening_greeting_job(context: ContextTypes.DEFAULT_TYPE):
    """Har kuni kechqurun barcha guruhlarga hayrli kech tilaydi."""
    text = random.choice(EVENING_MESSAGES)
    for chat_id in storage["groups"]:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
            if storage["stickers"]:
                await context.bot.send_sticker(chat_id=chat_id, sticker=random.choice(storage["stickers"]))
        except Exception as e:
            logger.warning("Kechqurungi tilakni yuborib bo'lmadi (%s): %s", chat_id, e)


async def group_activity_job(context: ContextTypes.DEFAULT_TYPE):
    """Vaqti-vaqti bilan guruhlarni 'jonlantirish' uchun ishga tushadi."""
    if storage["status"] != "offline":
        return
    for chat_id in storage["groups"]:
        if random.random() < GROUP_ACTIVITY_CHANCE:
            try:
                await context.bot.send_message(chat_id=chat_id, text=random.choice(GROUP_ACTIVITY_MESSAGES))
                if storage["stickers"] and random.random() < 0.3:
                    await context.bot.send_sticker(chat_id=chat_id, sticker=random.choice(storage["stickers"]))
            except Exception as e:
                logger.warning("Guruhga faollik xabari yuborib bo'lmadi (%s): %s", chat_id, e)


# ============== ROUTER ==============

async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type

    if chat_type == ChatType.PRIVATE:
        if is_owner(update):
            if update.message.sticker:
                await handle_owner_sticker(update, context)
            elif update.message.reply_to_message:
                await handle_owner_reply(update, context)
        else:
            await handle_private_incoming(update, context)
    else:
        await handle_group_message(update, context)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("online", set_online))
    app.add_handler(CommandHandler("offline", set_offline))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("stickers", stickers_count))
    app.add_handler(CommandHandler("guruhlar", list_groups))

    app.add_handler(ChatMemberHandler(on_bot_added_to_group, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, router))

    # Guruhlarni vaqti-vaqti bilan "jonlantirish" uchun
    app.job_queue.run_repeating(group_activity_job, interval=GROUP_ACTIVITY_INTERVAL_SEC, first=120)

    # Har kuni ertalab va kechqurun avtomatik salom/tilak
    app.job_queue.run_daily(morning_greeting_job, time=MORNING_TIME)
    app.job_queue.run_daily(evening_greeting_job, time=EVENING_TIME)

    logger.info("Jarvis ishga tushdi 🤖")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
