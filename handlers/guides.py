# handlers/guides.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from database import get_user  # ← для получения данных пользователя
from handlers.guides_db import get_guides_by_game_and_level  # ← только функции, не пути!
import aiosqlite

async def handle_guide_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or query.data != "menu_guides":
        return

    await query.answer()
    user = await get_user(update.effective_user.id)
    if not user or not user["games"]:
        await query.edit_message_text("Сначала пройди анкету через /start")
        return

    games = user["games"]
    keyboard = []
    for i in range(0, len(games), 3):
        row = []
        for j in range(i, min(i + 3, len(games))):
            row.append(InlineKeyboardButton(f"   {games[j]}   ", callback_data=f"guide_view_{j}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("   ⬅️ Назад   ", callback_data="back_to_menu")])

    await query.edit_message_text(
        "Выбери игру, по которой хочешь получить гайды:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_guides_for_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        game_index = int(query.data.split("_")[2])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ Ошибка выбора игры.")
        return

    user = await get_user(update.effective_user.id)
    if not user:
        await query.edit_message_text("Профиль не найден.")
        return

    if game_index >= len(user["games"]):
        await query.edit_message_text("❌ Игра не найдена.")
        return

    selected_game = user["games"][game_index]
    guides = await get_guides_by_game_and_level(selected_game, user["level"])

    if not guides:
        text = f"❌ Пока нет гайдов по игре «{selected_game}» для твоего уровня."
        keyboard = [[InlineKeyboardButton("   ⬅️ Назад к играм   ", callback_data="menu_guides")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    lines = []
    for idx, g in enumerate(guides):
        icon = "🖼️" if g["media_type"] == "photo" else "🎥" if g["media_type"] == "video" else "📄"
        lines.append(f"{idx+1}. {icon} <b>{g['title']}</b> ({g['level']})")

    text = f"📘 <b>Гайды по {selected_game}</b>\n\n" + "\n".join(lines)
    keyboard = []
    for g in guides:
        keyboard.append([InlineKeyboardButton(f"📖 {g['title']}", callback_data=f"read_guide_{g['id']}")])
    keyboard.append([InlineKeyboardButton("   ⬅️ Назад к играм   ", callback_data="menu_guides")])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def read_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        guide_id = int(query.data.split("_")[2])
    except (IndexError, ValueError):
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="❌ Ошибка загрузки гайда."
        )
        return

    # Получаем гайд через функцию из guides_db.py
    from handlers.guides_db import get_all_guides_with_details
    all_guides = await get_all_guides_with_details()
    guide = next((g for g in all_guides if g["id"] == guide_id), None)

    if not guide:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="❌ Гайд не найден."
        )
        return

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
        text="↩️ Вернуться к списку гайдов:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📘 К гайдам", callback_data="menu_guides")]
        ])
    )