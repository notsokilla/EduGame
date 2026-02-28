# handlers/info.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "ℹ️ <b>О платформе</b>\n\n"
        "• Это игровая платформа для гайдов и турниров.\n"
        "• Участвуй в турнирах, повышай рейтинг.\n"
        "• Читай персонализированные гайды под твой уровень."
    )
    keyboard = [[InlineKeyboardButton("   ⬅️ Назад   ", callback_data="back_to_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")