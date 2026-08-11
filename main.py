import os
import json
import re
from datetime import datetime, timedelta, timezone

from telegram import (
    Update,
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions,
    LabeledPrice,
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    ChatMemberHandler,
    ContextTypes,
    filters,
)


# =========================================================
# SOZLAMALAR
# =========================================================

TOKEN = "8940217521:AAFosKMDb9ErS-9KQIyzS20GvXOYNeXknTg"

OWNER_ID = 5940450585

DATA_FILE = "guard_bot_data.json"

PREMIUM_STARS = 5
PREMIUM_DAYS = 30

TRIAL_HOURS = 5

AUTO_MUTE_MINUTES = 5
MAX_MUTE_HOURS = 48
MAX_WARNINGS = 3


# =========================================================
# DATABASE
# =========================================================

def default_data():
    return {
        "groups": {},
        "users": {},
        "warnings": {},
        "payments": {},
        "trials": {},
        "mute_requests": {},
    }


def load_data():
    if not os.path.exists(DATA_FILE):
        data = default_data()

        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return data

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

    except Exception:
        data = default_data()

    defaults = default_data()

    for key in defaults:
        if key not in data:
            data[key] = defaults[key]

    return data


db = load_data()


def save_data():
    try:
        temp_file = DATA_FILE + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(
                db,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(temp_file, DATA_FILE)

    except Exception as e:
        print("DATABASE ERROR:", repr(e))


# =========================================================
# TIME
# =========================================================

def now():
    return datetime.now(timezone.utc)


def iso_now():
    return now().isoformat()


# =========================================================
# GROUP
# =========================================================

def get_group(chat_id):
    key = str(chat_id)

    if key not in db["groups"]:
        db["groups"][key] = {
            "title": "",
            "premium_until": None,
            "trial_used": False
        }

        save_data()

    return db["groups"][key]


# =========================================================
# PREMIUM
# =========================================================

def premium_until(chat_id):
    group = db["groups"].get(str(chat_id))

    if not group:
        return None

    value = group.get("premium_until")

    if not value:
        return None

    try:
        return datetime.fromisoformat(value)

    except Exception:
        return None


def premium_active(chat_id):
    expire = premium_until(chat_id)

    if not expire:
        return False

    return now() < expire


def activate_premium(chat_id, days=PREMIUM_DAYS):
    group = get_group(chat_id)

    start = now()
    old = premium_until(chat_id)

    if old and old > start:
        start = old

    expire = start + timedelta(days=days)

    group["premium_until"] = expire.isoformat()

    save_data()

    return expire


# =========================================================
# MEMBER
# =========================================================

async def get_member(bot, chat_id, user_id):
    try:
        return await bot.get_chat_member(
            chat_id,
            user_id
        )
    except Exception:
        return None


async def is_admin(bot, chat_id, user_id):
    member = await get_member(
        bot,
        chat_id,
        user_id
    )

    if not member:
        return False

    return member.status in (
        "administrator",
        "creator"
    )


async def is_owner(bot, chat_id, user_id):
    member = await get_member(
        bot,
        chat_id,
        user_id
    )

    if not member:
        return False

    return member.status == "creator"


async def bot_is_admin(bot, chat_id):
    try:
        me = await bot.get_me()

        member = await bot.get_chat_member(
            chat_id,
            me.id
        )

        return member.status in (
            "administrator",
            "creator"
        )

    except Exception:
        return False


# =========================================================
# COMMANDS
# =========================================================

async def setup_commands(application):

    private_commands = [
        BotCommand("start", "🤖 Botni ishga tushirish"),
        BotCommand("help", "❓ Yordam"),
        BotCommand("premium", "💎 Premium"),
        BotCommand("buy", "⭐ Premium / Trial"),
        BotCommand("status", "📊 Holat"),
        BotCommand("commands", "📋 Buyruqlar"),
    ]

    group_commands = [
        BotCommand("help", "❓ Yordam"),
        BotCommand("premium", "💎 Premium"),
        BotCommand("buy", "⭐ Premium / Trial"),
        BotCommand("status", "📊 Holat"),
        BotCommand("warnings", "⚠️ Warninglar"),
        BotCommand("commands", "📋 Buyruqlar"),
    ]

    await application.bot.set_my_commands(
        private_commands,
        scope=BotCommandScopeAllPrivateChats()
    )

    await application.bot.set_my_commands(
        group_commands,
        scope=BotCommandScopeAllGroupChats()
    )

    print("✅ / MENYU O'RNATILDI")


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if user:
        db["users"][str(user.id)] = {
            "name": user.first_name,
            "username": user.username,
            "last_seen": iso_now()
        }

        save_data()

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💎 Premium",
                callback_data="premium"
            ),
            InlineKeyboardButton(
                "🆓 Trial",
                callback_data="trial"
            )
        ],
        [
            InlineKeyboardButton(
                "🛡️ Himoya",
                callback_data="security"
            ),
            InlineKeyboardButton(
                "📋 Buyruqlar",
                callback_data="commands"
            )
        ],
        [
            InlineKeyboardButton(
                "❓ Yordam",
                callback_data="help"
            )
        ]
    ])

    await update.message.reply_text(
        "🛡️ GURUH QUTQARUVCHI BOT\n\n"
        "💎 Premium: 5 ⭐ / 30 kun\n"
        "🆓 Trial: 5 soat\n\n"
        "👋 Welcome oddiy guruhda ham ishlaydi.\n\n"
        "Botni guruhga qo‘shing va ADMIN qiling.\n\n"
        "👇 Tugmalardan foydalaning:",
        reply_markup=keyboard
    )


# =========================================================
# HELP
# =========================================================

async def help_command(update, context):

    await update.message.reply_text(
        "❓ YORDAM\n\n"
        "1️⃣ Botni guruhga qo‘shing.\n"
        "2️⃣ Botni ADMIN qiling.\n"
        "3️⃣ Kerakli huquqlarni bering.\n\n"

        "👋 Welcome — Premiumsiz ishlaydi.\n"
        "🆓 Trial — 5 soat.\n"
        "💎 Premium — 5 ⭐ / 30 kun.\n\n"

        "🔇 Mute:\n"
        "Foydalanuvchi xabariga reply qiling:\n\n"
        ".mute 20m sabab\n"
        ".mute 1day sabab\n"
        ".mute 2day sabab\n\n"

        "⏱ Maksimum mute: 2 kun.\n"
        "⚠️ Auto mute: 5 daqiqa."
    )


# =========================================================
# COMMANDS
# =========================================================

async def commands_command(update, context):

    await update.message.reply_text(
        "📋 BUYRUQLAR\n\n"

        "/start — 🤖 Start\n"
        "/help — ❓ Yordam\n"
        "/premium — 💎 Premium\n"
        "/buy — ⭐ Premium / Trial\n"
        "/status — 📊 Holat\n"
        "/warnings — ⚠️ Warninglar\n"
        "/commands — 📋 Buyruqlar\n\n"

        "🔇 Reply qilib:\n"
        ".mute 20m sabab\n"
        ".mute 1day sabab\n"
        ".mute 2day sabab"
    )


# =========================================================
# PREMIUM
# =========================================================

async def premium_command(update, context):

    await update.message.reply_text(
        "💎 PREMIUM\n\n"

        "⭐ Narxi: 5 Stars\n"
        "⏱ Muddati: 30 kun\n"
        "🆓 Trial: 5 soat\n\n"

        "Premium funksiyalar:\n"
        "🛡️ Anti-link\n"
        "🤬 Anti-haqorat\n"
        "⚠️ Warning\n"
        "🔇 Auto mute\n"
        "🚫 Spam nazorat\n"
        "🔔 Mute request\n"
        "📊 Status\n"
        "💾 JSON database\n\n"

        "👋 Welcome Premiumsiz ham ishlaydi."
    )


# =========================================================
# STATUS
# =========================================================

async def status_command(update, context):

    chat = update.effective_chat

    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text(
            "📊 Bu buyruq guruhda ishlaydi."
        )
        return

    group = get_group(chat.id)

    if premium_active(chat.id):

        expire = premium_until(chat.id)

        text = (
            "💎 PREMIUM FAOL\n\n"
            f"📅 Tugashi:\n"
            f"{expire.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            "🔗 Anti-link: ✅\n"
            "🤬 Anti-haqorat: ✅\n"
            "⚠️ Warning: ✅\n"
            "🔇 Auto mute: ✅\n"
            "🚫 Spam: ✅\n"
            "👋 Welcome: ✅"
        )

    else:

        trial = group.get(
            "trial_used",
            False
        )

        text = (
            "🆓 PREMIUM FAOL EMAS\n\n"
            f"Trial ishlatilgan: "
            f"{'Ha' if trial else 'Yo‘q'}\n\n"
            "⭐ Premium: 5 Stars / 30 kun\n"
            "👋 Welcome: ✅"
        )

    await update.message.reply_text(text)


# =========================================================
# BUY / TRIAL
# =========================================================

async def buy_command(update, context):

    chat = update.effective_chat

    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text(
            "❌ /buy ni guruhda ishlating."
        )
        return

    user_id = update.effective_user.id

    if not await is_admin(
        context.bot,
        chat.id,
        user_id
    ):
        await update.message.reply_text(
            "❌ Premiumni faqat guruh admini ulashi mumkin."
        )
        return

    if not await bot_is_admin(
        context.bot,
        chat.id
    ):
        await update.message.reply_text(
            "❌ Avval botni guruhda ADMIN qiling."
        )
        return

    group = get_group(chat.id)

    # TRIAL
    if not group.get("trial_used", False):

        group["trial_used"] = True

        expire = now() + timedelta(
            hours=TRIAL_HOURS
        )

        group["premium_until"] = expire.isoformat()

        db["trials"][str(chat.id)] = {
            "started": iso_now(),
            "expire": expire.isoformat()
        }

        save_data()

        await update.message.reply_text(
            "🎉 TRIAL YOQILDI!\n\n"
            "🆓 5 soat Premium.\n\n"
            "🛡️ Anti-link: ON\n"
            "🤬 Anti-haqorat: ON\n"
            "⚠️ Warning: ON\n"
            "🔇 Auto mute: ON\n"
            "🚫 Spam: ON"
        )

        return

    # PREMIUM ACTIVE
    if premium_active(chat.id):

        await update.message.reply_text(
            "💎 Premium hali faol."
        )
        return

    # STARS
    payload = f"premium:{chat.id}"

    prices = [
        LabeledPrice(
            "💎 Premium 30 kun",
            PREMIUM_STARS
        )
    ]

    await context.bot.send_invoice(
        chat_id=update.effective_user.id,
        title="💎 Guruh Qutqaruvchi Premium",
        description="Guruh himoyasi — 30 kun",
        payload=payload,
        currency="XTR",
        prices=prices,
        provider_token=""
    )


# =========================================================
# PAYMENT
# =========================================================

async def pre_checkout(update, context):

    await update.pre_checkout_query.answer(
        ok=True
    )


async def successful_payment(update, context):

    payment = update.message.successful_payment

    payload = payment.invoice_payload

    if not payload.startswith("premium:"):
        return

    chat_id = int(
        payload.split(":", 1)[1]
    )

    expire = activate_premium(chat_id)

    uid = str(
        update.effective_user.id
    )

    if uid not in db["payments"]:
        db["payments"][uid] = []

    db["payments"][uid].append({
        "chat_id": chat_id,
        "stars": PREMIUM_STARS,
        "date": iso_now(),
        "charge_id":
            payment.telegram_payment_charge_id
    })

    save_data()

    await update.message.reply_text(
        "🎉 TO‘LOV QABUL QILINDI!\n\n"
        "💎 Premium: AKTIV\n"
        "⭐ To‘lov: 5 Stars\n"
        "⏱ Muddat: 30 kun\n\n"
        f"📅 Tugashi:\n"
        f"{expire.strftime('%Y-%m-%d %H:%M UTC')}"
    )


# =========================================================
# WARNING
# =========================================================

def warning_key(chat_id, user_id):
    return f"{chat_id}:{user_id}"


def get_warning(chat_id, user_id):

    return db["warnings"].get(
        warning_key(chat_id, user_id),
        0
    )


def add_warning(chat_id, user_id):

    key = warning_key(chat_id, user_id)

    db["warnings"][key] = (
        get_warning(chat_id, user_id) + 1
    )

    save_data()

    return db["warnings"][key]


def reset_warning(chat_id, user_id):

    db["warnings"].pop(
        warning_key(chat_id, user_id),
        None
    )

    save_data()


# =========================================================
# BAD WORDS
# =========================================================

BAD_WORDS = {
    "ahmoq",
    "tentak",
    "jalab",
    "pashol",
    "mol"
}


def contains_bad_word(text):

    words = re.findall(
        r"[A-Za-zА-Яа-яЁёЎўҒғҚқҲҳ0-9]+",
        text.lower()
    )

    return any(
        word in BAD_WORDS
        for word in words
    )


# =========================================================
# LINK
# =========================================================

def contains_link(text):

    return bool(
        re.search(
            r"(https?://|www\.|t\.me/|telegram\.me/)",
            text,
            re.IGNORECASE
        )
    )


# =========================================================
# MUTE PARSER
# =========================================================

def parse_mute(text):

    pattern = (
        r"^\.mute\s+"
        r"(\d+)"
        r"(m|min|h|hour|hours|d|day|days)"
        r"(?:\s+(.+))?$"
    )

    match = re.match(
        pattern,
        text.strip(),
        re.IGNORECASE
    )

    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2).lower()

    reason = (
        match.group(3)
        or "Sabab ko‘rsatilmagan"
    )

    if unit in ("m", "min"):
        minutes = amount

    elif unit in ("h", "hour", "hours"):
        minutes = amount * 60

    else:
        minutes = amount * 1440

    if minutes > MAX_MUTE_HOURS * 60:
        return "MAX"

    return minutes, reason


# =========================================================
# MUTE REQUEST
# =========================================================

async def mute_request(update, context):

    message = update.effective_message

    if message.chat.type not in (
        "group",
        "supergroup"
    ):
        return

    if not premium_active(message.chat.id):

        await message.reply_text(
            "💎 Mute funksiyasi Premium/Trialda ishlaydi."
        )
        return

    if not message.reply_to_message:

        await message.reply_text(
            "🔇 Avval foydalanuvchi xabariga reply qiling.\n\n"
            "Namuna:\n"
            ".mute 20m sabab\n"
            ".mute 1day jahlimga tegdi"
        )
        return

    parsed = parse_mute(message.text)

    if parsed == "MAX":

        await message.reply_text(
            "❌ Maksimum mute: 2 kun."
        )
        return

    if not parsed:
        return

    minutes, reason = parsed

    target = message.reply_to_message.from_user

    if not target:
        return

    # Guruh egasi yoki adminni mute qilmaslik
    if await is_admin(
        context.bot,
        message.chat.id,
        target.id
    ):

        await message.reply_text(
            "❌ Adminni mute qilish mumkin emas."
        )
        return

    request_id = (
        f"{message.chat.id}:"
        f"{target.id}:"
        f"{message.message_id}"
    )

    db["mute_requests"][request_id] = {
        "chat_id": message.chat.id,
        "target_id": target.id,
        "target_name": target.first_name,
        "requester": message.from_user.first_name,
        "minutes": minutes,
        "reason": reason
    }

    save_data()

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Tasdiqlash",
                callback_data="approve:" + request_id
            ),
            InlineKeyboardButton(
                "❌ Bekor qilish",
                callback_data="reject:" + request_id
            )
        ]
    ])

    await message.reply_text(
        "🔔 MUTE SO‘ROVI\n\n"
        f"👤 Kim: {target.first_name}\n"
        f"⏱ Muddati: {minutes} daqiqa\n"
        f"📝 Sabab: {reason}\n"
        f"👤 So‘rovchi: {message.from_user.first_name}\n\n"
        "👮 Admin tasdiqlashi kerak.",
        reply_markup=keyboard
    )


# =========================================================
# BUTTONS
# =========================================================

async def callback_handler(update, context):

    query = update.callback_query
    data = query.data

    # -----------------------------------------------------
    # UNMUTE
    # -----------------------------------------------------

    if data.startswith("unmute:"):

        _, chat_id, user_id = data.split(":")

        chat_id = int(chat_id)
        user_id = int(user_id)

        if not await is_owner(
            context.bot,
            chat_id,
            query.from_user.id
        ):

            await query.answer(
                "❌ Bu tugma faqat guruh egasi uchun.",
                show_alert=True
            )
            return

        try:

            await context.bot.restrict_chat_member(
                chat_id,
                user_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_audios=True,
                    can_send_documents=True,
                    can_send_photos=True,
                    can_send_videos=True,
                    can_send_video_notes=True,
                    can_send_voice_notes=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                    can_invite_users=True
                )
            )

            await query.message.edit_text(
                "🔊 MUTE OLIB TASHLANDI!\n\n"
                "👑 Guruh egasi tomonidan."
            )

            await query.answer(
                "✅ Unmute qilindi!"
            )

        except Exception as e:

            print(
                "UNMUTE ERROR:",
                repr(e)
            )

            await query.answer(
                "❌ Xatolik.",
                show_alert=True
            )

        return

    # -----------------------------------------------------
    # APPROVE
    # -----------------------------------------------------

    if data.startswith("approve:"):

        request_id = data.split(":", 1)[1]

        request = db["mute_requests"].get(
            request_id
        )

        if not request:

            await query.answer(
                "❌ So‘rov topilmadi.",
                show_alert=True
            )
            return

        if not await is_admin(
            context.bot,
            request["chat_id"],
            query.from_user.id
        ):

            await query.answer(
                "❌ Faqat admin tasdiqlaydi.",
                show_alert=True
            )
            return

        try:

            minutes = min(
                request["minutes"],
                MAX_MUTE_HOURS * 60
            )

            until = now() + timedelta(
                minutes=minutes
            )

            await context.bot.restrict_chat_member(
                request["chat_id"],
                request["target_id"],
                permissions=ChatPermissions(
                    can_send_messages=False
                ),
                until_date=until
            )

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔓 Mute'dan chiqarish",
                        callback_data=(
                            f"unmute:"
                            f"{request['chat_id']}:"
                            f"{request['target_id']}"
                        )
                    )
                ]
            ])

            await query.message.edit_text(
                "🔇 MUTE QILINDI\n\n"
                f"👤 {request['target_name']}\n"
                f"⏱ {minutes} daqiqa\n"
                f"📝 Sabab: {request['reason']}\n\n"
                f"👮 Tasdiqladi: "
                f"{query.from_user.first_name}",
                reply_markup=keyboard
            )

            del db["mute_requests"][request_id]

            save_data()

            await query.answer(
                "✅ Mute qilindi!"
            )

        except Exception as e:

            print(
                "MUTE ERROR:",
                repr(e)
            )

            await query.answer(
                "❌ Mute qilishda xatolik.",
                show_alert=True
            )

        return

    # -----------------------------------------------------
    # REJECT
    # -----------------------------------------------------

    if data.startswith("reject:"):

        request_id = data.split(":", 1)[1]

        request = db["mute_requests"].get(
            request_id
        )

        if not request:

            await query.answer(
                "❌ So‘rov topilmadi.",
                show_alert=True
            )
            return

        if not await is_admin(
            context.bot,
            request["chat_id"],
            query.from_user.id
        ):

            await query.answer(
                "❌ Faqat admin bekor qiladi.",
                show_alert=True
            )
            return

        await query.message.edit_text(
            "❌ MUTE SO‘ROVI BEKOR QILINDI."
        )

        del db["mute_requests"][request_id]

        save_data()

        await query.answer(
            "Bekor qilindi."
        )

        return

    # -----------------------------------------------------
    # INFO BUTTONS
    # -----------------------------------------------------

    await query.answer()

    if data == "premium":

        text = (
            "💎 PREMIUM\n\n"
            "⭐ 5 Stars\n"
            "⏱ 30 kun\n\n"
            "🛡️ Anti-link\n"
            "🤬 Anti-haqorat\n"
            "⚠️ Warning\n"
            "🔇 Auto mute\n"
            "🚫 Anti-spam\n"
            "🔔 Mute request\n"
            "📊 Status\n"
            "💾 JSON database"
        )

    elif data == "trial":

        text = (
            "🆓 TRIAL\n\n"
            "Har bir guruh uchun bir marta.\n"
            "⏱ 5 soat.\n\n"
            "Trial tugagach:\n"
            "⭐ Premium — 5 Stars / 30 kun"
        )

    elif data == "security":

        text = (
            "🛡️ HIMOYA\n\n"
            "🔗 Link → o‘chiriladi\n"
            "🤬 Haqorat → Warning\n"
            "⚠️ 3 Warning → 5 min mute\n"
            "🚫 Spam → nazorat\n"
            "🔇 Mute → admin tasdig‘i\n"
            "👋 Welcome → Premiumsiz"
        )

    elif data == "commands":

        text = (
            "📋 BUYRUQLAR\n\n"
            "/help\n"
            "/premium\n"
            "/buy\n"
            "/status\n"
            "/warnings\n"
            "/commands\n\n"
            "🔇 Reply:\n"
            ".mute 20m sabab\n"
            ".mute 1day sabab\n"
            ".mute 2day sabab"
        )

    elif data == "help":

        text = (
            "❓ YORDAM\n\n"
            "Botni guruhga qo‘shing.\n"
            "Botni ADMIN qiling.\n\n"
            "🆓 Trial: 5 soat\n"
            "💎 Premium: 5 ⭐ / 30 kun\n\n"
            "👋 Welcome Premiumsiz ishlaydi.\n"
            "🔇 Mute uchun xabarga reply qiling."
        )

    else:

        text = "❓ Noma'lum."

    await query.message.reply_text(text)


# =========================================================
# AUTO MODERATION
# =========================================================

async def moderation(update, context):

    message = update.effective_message

    if not message:
        return

    if message.chat.type not in (
        "group",
        "supergroup"
    ):
        return

    if not message.text:
        return

    if not premium_active(message.chat.id):
        return

    user = message.from_user

    if not user:
        return

    if await is_admin(
        context.bot,
        message.chat.id,
        user.id
    ):
        return

    text = message.text

    bad = contains_bad_word(text)
    link = contains_link(text)

    if not bad and not link:
        return

    try:
        await message.delete()
    except Exception:
        pass

    reason = (
        "🔗 Havola"
        if link
        else
        "🤬 Haqorat"
    )

    warning = add_warning(
        message.chat.id,
        user.id
    )

    if warning < MAX_WARNINGS:

        await context.bot.send_message(
            message.chat.id,
            f"⚠️ {user.first_name}\n\n"
            f"Sabab: {reason}\n"
            f"Warning: {warning}/{MAX_WARNINGS}"
        )

    else:

        try:

            until = now() + timedelta(
                minutes=AUTO_MUTE_MINUTES
            )

            await context.bot.restrict_chat_member(
                message.chat.id,
                user.id,
                permissions=ChatPermissions(
                    can_send_messages=False
                ),
                until_date=until
            )

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔓 Mute'dan chiqarish",
                        callback_data=(
                            f"unmute:"
                            f"{message.chat.id}:"
                            f"{user.id}"
                        )
                    )
                ]
            ])

            await context.bot.send_message(
                message.chat.id,
                f"🔇 {user.first_name} mute qilindi.\n\n"
                f"⏱ {AUTO_MUTE_MINUTES} daqiqa\n"
                "📝 Sabab: 3 ta Warning",
                reply_markup=keyboard
            )

            reset_warning(
                message.chat.id,
                user.id
            )

        except Exception as e:

            print(
                "AUTO MUTE ERROR:",
                repr(e)
            )


# =========================================================
# WELCOME
# PREMIUMGA BOG'LANMAGAN
# =========================================================

async def welcome(update, context):

    member = update.chat_member

    if not member:
        return

    old_status = member.old_chat_member.status
    new_status = member.new_chat_member.status

    left_statuses = (
        "left",
        "kicked"
    )

    joined_statuses = (
        "member",
        "administrator",
        "creator",
        "restricted"
    )

    # Faqat yangi kirgan / qayta kirgan odam
    if (
        old_status in left_statuses
        and new_status in joined_statuses
    ):

        user = member.new_chat_member.user

        try:

            await context.bot.send_message(
                chat_id=member.chat.id,
                text=(
                    f"👋 Salom, {user.first_name}!\n\n"
                    "🎉 Guruhimizga xush kelibsiz!\n"
                    "🛡️ Qoidalarni hurmat qiling."
                )
            )

            print(
                f"👋 WELCOME: "
                f"{user.id} -> {member.chat.id}"
            )

        except Exception as e:

            print(
                "WELCOME ERROR:",
                repr(e)
            )


# =========================================================
# WARNINGS
# =========================================================

async def warnings_command(update, context):

    if update.effective_chat.type not in (
        "group",
        "supergroup"
    ):
        return

    user = update.effective_user

    count = get_warning(
        update.effective_chat.id,
        user.id
    )

    await update.message.reply_text(
        f"⚠️ Sizning Warninglaringiz: "
        f"{count}/{MAX_WARNINGS}"
    )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(update, context):

    print(
        "BOT ERROR:",
        repr(context.error)
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 35)
    print("🛡️ GURUH QUTQARUVCHI BOT")
    print("=" * 35)

    print(
        f"💎 Premium: {PREMIUM_STARS} Stars / "
        f"{PREMIUM_DAYS} kun"
    )

    print(
        f"🆓 Trial: {TRIAL_HOURS} soat"
    )

    print(
        f"🔇 Auto mute: {AUTO_MUTE_MINUTES} min"
    )

    print(
        f"⏱ Max mute: {MAX_MUTE_HOURS} soat"
    )

    print(
        f"📁 Database: {DATA_FILE}"
    )

    application = (
        Application.builder()
        .token(TOKEN)
        .post_init(setup_commands)
        .build()
    )

    # =====================================================
    # PRIVATE / GROUP COMMANDS
    # =====================================================

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    application.add_handler(
        CommandHandler("premium", premium_command)
    )

    application.add_handler(
        CommandHandler("buy", buy_command)
    )

    application.add_handler(
        CommandHandler("status", status_command)
    )

    application.add_handler(
        CommandHandler("commands", commands_command)
    )

    application.add_handler(
        CommandHandler("warnings", warnings_command)
    )

    # =====================================================
    # PAYMENT
    # =====================================================

    application.add_handler(
        PreCheckoutQueryHandler(pre_checkout)
    )

    application.add_handler(
        MessageHandler(
            filters.SUCCESSFUL_PAYMENT,
            successful_payment
        )
    )

    # =====================================================
    # BUTTONS
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(callback_handler)
    )

    # =====================================================
    # WELCOME
    # ENG MUHIM QISM
    # =====================================================

    application.add_handler(
        ChatMemberHandler(
            welcome,
            ChatMemberHandler.CHAT_MEMBER
        )
    )

    # =====================================================
    # MUTE REQUEST
    # =====================================================

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & filters.Regex(r"^\.mute\s+"),
            mute_request
        ),
        group=1
    )

    # =====================================================
    # MODERATION
    # =====================================================

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            moderation
        ),
        group=2
    )

    # =====================================================
    # ERROR
    # =====================================================

    application.add_error_handler(
        error_handler
    )

    print("✅ BOT ISHGA TUSHDI!")
    print("✅ / MENYU YOQILDI!")
    print("✅ WELCOME PREMIUMGA BOG'LANMAGAN!")
    print("✅ guard_bot_data.json AKTIV!")

    application.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    main()
