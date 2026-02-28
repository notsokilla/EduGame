# handlers/stats.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from database import get_user

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = await get_user(update.effective_user.id)
    if not user:
        text = "Сначала пройди анкету через /start"
    else:
        text = (
            f"📊 <b>Моя статистика</b>\n\n"
            f"Никнейм: {user['display_name']}\n"
            f"Игры: {', '.join(user['games'])}\n"
            f"Уровень: {user['level']}\n"
            #f"Турниров: {user.get('tournaments', 0)}\n"
            #f"Побед: {user.get('wins', 0)}\n"
            #f"Рейтинг: {user.get('rating', 1000)}\n\n"
            #"Продолжай играть и повышай рейтинг 💪"
        )
    keyboard = [[InlineKeyboardButton("   ⬅️ Назад   ", callback_data="back_to_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")