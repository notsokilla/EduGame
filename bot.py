import asyncio
import warnings
from dotenv import load_dotenv
from telegram.warnings import PTBUserWarning
warnings.filterwarnings("ignore", category=PTBUserWarning, message=r".*CallbackQueryHandler.*")

import logging
logging.getLogger("httpx").setLevel(logging.WARNING)

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

# Импорты обработчиков
from handlers.start import conv_handler, show_main_menu, handle_promo_click
from handlers.guides import handle_guide_menu, show_guides_for_game, read_guide
from handlers.stats import show_stats
from handlers.info import show_info
from handlers.profile import show_profile
from handlers.admin import (
    password_handler,
    add_guide_handler,
    list_users,
    list_all_guides,
    admin_read_guide,
    confirm_delete_guide,
    admin_back
)
import os
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан! Укажите через переменную окружения.")

# Импорты БД
from database import init_db
from handlers.guides_db import init_guides_db

async def initialize_databases():
    await init_db()
    await init_guides_db()

async def handle_callback(update: Update, context):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data

    # Обработка только тех callback'ов, которые НЕ относятся к FSM
    if data == "menu_guides":
        await handle_guide_menu(update, context)
    elif data == "menu_stats":
        await show_stats(update, context)
    elif data == "menu_info":
        await show_info(update, context)
    elif data == "menu_profile":
        await show_profile(update, context)
    elif data == "back_to_menu":
        await show_main_menu(update, context)
    elif data == "admin_list_users":
        await list_users(update, context)
    elif data == "admin_list_guides":
        await list_all_guides(update, context)
    elif data.startswith("admin_read_guide_"):
        await admin_read_guide(update, context)
    elif data.startswith("admin_delete_guide_"):
        await confirm_delete_guide(update, context)
    elif data.startswith("guide_view_"):
        await show_guides_for_game(update, context)
    elif data.startswith("read_guide_"):
        await read_guide(update, context)
    elif data == "admin_back":
        await admin_back(update, context)
    elif data == "promo_click":
        await handle_promo_click(update, context)

def main():
    asyncio.run(initialize_databases())

    app = Application.builder().token(BOT_TOKEN).build()

    # Регистрация FSM-обработчиков ПЕРВЫМИ
    app.add_handler(conv_handler)
    app.add_handler(password_handler)      # /admin → пароль
    app.add_handler(add_guide_handler)     # добавление гайда

    # Общий обработчик — ПОСЛЕДНИМ
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("✅ Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()