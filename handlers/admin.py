import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, MessageHandler,
    CommandHandler, CallbackQueryHandler, filters
)
from .guides_db import add_guide, get_all_guides_with_details, get_users_for_admin, GUIDES_DB, delete_guide_by_id
from handlers.start import GAMES, LEVELS
from logger import log_user_action
import aiosqlite

# Состояния FSM
(
    SELECT_GAME, TITLE, DESCRIPTION, SELECT_LEVEL,
    WAITING_PHOTO_OR_VIDEO, CONFIRM,
    AWAITING_PASSWORD
) = range(7)
load_dotenv()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
# === ВХОД ПО ПАРОЛЮ ===
async def cmd_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔒 Введите пароль для доступа к админке:")
    return AWAITING_PASSWORD

async def check_admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == ADMIN_PASSWORD:
        user_id = update.effective_user.id
        username = update.effective_user.username
        log_user_action(user_id, username, "Вошёл в админку по паролю")

        keyboard = [
            [InlineKeyboardButton("👥 Пользователи", callback_data="admin_list_users")],
            [InlineKeyboardButton("📚 Все гайды", callback_data="admin_list_guides")],
            [InlineKeyboardButton("➕ Добавить гайд", callback_data="admin_add_guide")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
        ]
        await update.message.reply_text("🛠 Админ-панель", reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Неверный пароль.")
        return ConversationHandler.END

# === ПОЛЬЗОВАТЕЛИ ===
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    username = update.effective_user.username
    log_user_action(user_id, username, "Просмотрел список пользователей")

    users = await get_users_for_admin()
    if not users:
        text = "Нет пользователей."
    else:
        lines = []
        for u in users:
            tg_un = u.get("telegram_username")
            tg_tag = f"@{tg_un}" if tg_un else "—"
            display = u.get("display_name", "—")
            promo_status = "Да" if u.get("promo_clicked") else "Нет"
            games_str = ", ".join(u["games"][:2]) + ("..." if len(u["games"]) > 2 else "")
            lines.append(f"• {tg_tag} | {display} | Переход: {promo_status} (ID: {u['user_id']}) — {games_str} | {u['level']}")
        text = "👥 <b>Пользователи:</b>\n\n" + "\n".join(lines)
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# === ГАЙДЫ ===
async def list_all_guides(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    guides = await get_all_guides_with_details()
    if not guides:
        text = "❌ Нет гайдов."
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    lines = []
    for g in guides:
        icon = "🖼️" if g["media_type"] == "photo" else "🎥" if g["media_type"] == "video" else "📄"
        lines.append(f"• {icon} <b>{g['title']}</b> ({g['game']} | {g['level']})")

    text = "📚 <b>Все гайды:</b>\n\n" + "\n".join(lines)
    keyboard = []
    for g in guides:
        row = [
            InlineKeyboardButton(f"📖 {g['title']}", callback_data=f"admin_read_guide_{g['id']}"),
            InlineKeyboardButton("🗑️", callback_data=f"admin_delete_guide_{g['id']}")
        ]
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def admin_read_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        guide_id = int(query.data.split("_")[3])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ Ошибка загрузки гайда.")
        return

    async with aiosqlite.connect(GUIDES_DB) as db:
        async with db.execute("SELECT * FROM guides WHERE id = ?", (guide_id,)) as cursor:
            row = await cursor.fetchone()

    if not row:
        await query.edit_message_text("❌ Гайд не найден.")
        return

    guide = {
        "id": row[0],
        "game": row[1],
        "title": row[2],
        "description": row[3] or "",
        "level": row[4],
        "media_type": row[5],
        "media_file_id": row[6]
    }

    caption = (
        f"📘 <b>{guide['title']}</b>\n"
        f"Игра: {guide['game']} | Уровень: {guide['level']}\n\n"
        f"{guide['description']}"
    )

    chat_id = query.message.chat_id

    if guide["media_type"] == "photo":
        await context.bot.send_photo(chat_id=chat_id, photo=guide["media_file_id"], caption=caption, parse_mode="HTML")
    elif guide["media_type"] == "video":
        await context.bot.send_video(chat_id=chat_id, video=guide["media_file_id"], caption=caption, parse_mode="HTML")
    else:
        await context.bot.send_message(chat_id=chat_id, text=caption, parse_mode="HTML")

    await context.bot.send_message(
        chat_id=chat_id,
        text="↩️ Вернуться к списку всех гайдов:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 Все гайды", callback_data="admin_list_guides")]
        ])
    )

async def confirm_delete_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        guide_id = int(query.data.split("_")[3])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ Ошибка удаления.")
        return

    await delete_guide_by_id(guide_id)

    user_id = update.effective_user.id
    username = update.effective_user.username
    log_user_action(user_id, username, f"Удалил гайд ID={guide_id}")

    # Возвращаемся в меню админки
    await query.edit_message_text(
        "🗑️ Гайд успешно удалён!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Вернуться в меню", callback_data="admin_back")]
        ])
    )

# === ДОБАВЛЕНИЕ ГАЙДА ===
async def start_add_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = []
    for i in range(0, len(GAMES), 3):
        row = []
        for j in range(i, min(i + 3, len(GAMES))):
            row.append(InlineKeyboardButton(f"   {GAMES[j]}   ", callback_data=f"guide_game_{j}"))
        keyboard.append(row)
    await query.edit_message_text("Выберите игру для гайда:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_GAME

async def select_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    game_index = int(query.data.split("_")[2])
    context.user_data["admin_guide"] = {"game": GAMES[game_index]}
    await query.edit_message_text("Введите заголовок гайда:")
    return TITLE

async def enter_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_guide"]["title"] = update.message.text.strip()
    await update.message.reply_text("Введите описание гайда (можно оставить пустым):")
    return DESCRIPTION

async def enter_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip() if update.message.text else ""
    context.user_data["admin_guide"]["description"] = desc
    keyboard = []
    for i in range(0, len(LEVELS), 2):
        row = []
        for j in range(i, min(i + 2, len(LEVELS))):
            row.append(InlineKeyboardButton(f"   {LEVELS[j]}   ", callback_data=f"guide_level_{j}"))
        keyboard.append(row)
    await update.message.reply_text("Выберите уровень сложности:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_LEVEL

async def select_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    level_index = int(query.data.split("_")[2])
    context.user_data["admin_guide"]["level"] = LEVELS[level_index]
    await query.edit_message_text("Теперь отправьте фото или видео (или /skip, чтобы пропустить):")
    return WAITING_PHOTO_OR_VIDEO

async def receive_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guide = context.user_data["admin_guide"]
    if update.message.photo:
        guide["media_type"] = "photo"
        guide["media_file_id"] = update.message.photo[-1].file_id
    elif update.message.video:
        guide["media_type"] = "video"
        guide["media_file_id"] = update.message.video.file_id
    else:
        guide["media_type"] = None
        guide["media_file_id"] = None

    text = (
        f"✅ <b>Гайд готов к сохранению:</b>\n\n"
        f"Игра: {guide['game']}\n"
        f"Заголовок: {guide['title']}\n"
        f"Уровень: {guide['level']}\n"
        f"Медиа: {'Да' if guide['media_type'] else 'Нет'}\n\n"
        f"Подтвердить?"
    )
    keyboard = [
        [InlineKeyboardButton("✅ Сохранить", callback_data="admin_confirm_save")],
        [InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return CONFIRM

async def skip_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guide = context.user_data["admin_guide"]
    guide["media_type"] = None
    guide["media_file_id"] = None
    text = (
        f"✅ <b>Гайд готов к сохранению:</b>\n\n"
        f"Игра: {guide['game']}\n"
        f"Заголовок: {guide['title']}\n"
        f"Уровень: {guide['level']}\n"
        f"Медиа: Нет\n\n"
        f"Подтвердить?"
    )
    keyboard = [
        [InlineKeyboardButton("✅ Сохранить", callback_data="admin_confirm_save")],
        [InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return CONFIRM

async def confirm_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    guide = context.user_data["admin_guide"]
    await add_guide(
        game=guide["game"],
        title=guide["title"],
        description=guide["description"],
        level=guide["level"],
        media_type=guide.get("media_type"),
        media_file_id=guide.get("media_file_id")
    )
    user_id = update.effective_user.id
    username = update.effective_user.username
    log_user_action(user_id, username, f"Добавил гайд: {guide['title']}")
    await query.edit_message_text("✅ Гайд успешно добавлен!")
    return ConversationHandler.END

async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Действие отменено.")
    else:
        await update.message.reply_text("❌ Действие отменено.")
    return ConversationHandler.END

async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("👥 Пользователи", callback_data="admin_list_users")],
        [InlineKeyboardButton("📚 Все гайды", callback_data="admin_list_guides")],
        [InlineKeyboardButton("➕ Добавить гайд", callback_data="admin_add_guide")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    await query.edit_message_text("🛠 Админ-панель", reply_markup=InlineKeyboardMarkup(keyboard))

# === ОТДЕЛЬНЫЕ CONVERSATION HANDLERS ===

# 1. Авторизация по паролю
password_handler = ConversationHandler(
    entry_points=[CommandHandler("admin", cmd_admin_menu)],
    states={
        AWAITING_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_admin_password)]
    },
    fallbacks=[]
)

# 2. Добавление гайда
add_guide_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_add_guide, pattern="^admin_add_guide$")],
    states={
        SELECT_GAME: [CallbackQueryHandler(select_game, pattern=r"^guide_game_\d+$")],
        TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_title)],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_description)],
        SELECT_LEVEL: [CallbackQueryHandler(select_level, pattern=r"^guide_level_\d+$")],
        WAITING_PHOTO_OR_VIDEO: [
            MessageHandler(filters.PHOTO | filters.VIDEO, receive_media),
            CommandHandler("skip", skip_media)
        ],
        CONFIRM: [
            CallbackQueryHandler(confirm_save, pattern="^admin_confirm_save$"),
            CallbackQueryHandler(cancel_admin, pattern="^admin_cancel$")
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_admin)]
)