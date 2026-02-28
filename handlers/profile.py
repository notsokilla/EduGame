# handlers/profile.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from database import get_user

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    user = await get_user(update.effective_user.id)
    if not user:
        text = "Сначала пройди анкету через /start"
        keyboard = [[InlineKeyboardButton("   ⬅️ Назад   ", callback_data="back_to_menu")]]
    else:
        # ПОЛЬЗОВАТЕЛЬ ВИДИТ ТОЛЬКО СВОЙ ВВЕДЁННЫЙ НИК
        text = (
            f"👤 <b>Профиль</b>\n\n"
            f"Никнейм: {user['display_name']}\n"
            f"Игры: {', '.join(user['games'])}\n"
            f"Уровень: {user['level']}"
        )
        keyboard = [
            [InlineKeyboardButton("   ✏️ Редактировать   ", callback_data="edit_profile")],
            [InlineKeyboardButton("   ⬅️ Назад в меню   ", callback_data="back_to_menu")]
        ]
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def show_profile_from_edit(update: Update | None, context: ContextTypes.DEFAULT_TYPE, user, query=None, chat_id=None):
    if query is None and update is None and chat_id:
        text = (
            f"👤 <b>Профиль</b>\n\n"
            f"Никнейм: {user['display_name']}\n"
            f"Игры: {', '.join(user['games'])}\n"
            f"Уровень: {user['level']}"
        )
        keyboard = [
            [InlineKeyboardButton("   ✏️ Редактировать   ", callback_data="edit_profile")],
            [InlineKeyboardButton("   ⬅️ Назад в меню   ", callback_data="back_to_menu")]
        ]
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        if query is None:
            query = update.callback_query
        text = (
            f"👤 <b>Профиль</b>\n\n"
            f"Никнейм: {user['display_name']}\n"
            f"Игры: {', '.join(user['games'])}\n"
            f"Уровень: {user['level']}"
        )
        keyboard = [
            [InlineKeyboardButton("   ✏️ Редактировать   ", callback_data="edit_profile")],
            [InlineKeyboardButton("   ⬅️ Назад в меню   ", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")