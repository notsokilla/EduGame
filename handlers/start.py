# handlers/start.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
    filters
)
from database import get_user, save_user, set_promo_clicked
from telegram.error import BadRequest
from logger import log_user_action

NICKNAME, GAME_SELECTION, LEVEL_SELECTION, EDIT_PROFILE, EDIT_NICKNAME, EDIT_GAMES, EDIT_LEVEL = range(7)

GAMES = ["🎯 Standoff", "🚗 Black Russia", "🧱 Roblox", "🔫 PUBG", "⚽️ FIFA", "👑 Clash Royale", "⭐️ Brawl Stars"]
LEVELS = ["Новичок", "Средний", "Продвинутый", "Профи"]

def make_initial_game_keyboard():
    keyboard = []
    for i in range(0, len(GAMES), 3):
        row = []
        for j in range(i, min(i + 3, len(GAMES))):
            row.append(InlineKeyboardButton(f"   {GAMES[j]}   ", callback_data=f"game_{j}"))
        keyboard.append(row)
    return keyboard

def make_level_keyboard():
    keyboard = []
    for i in range(0, len(LEVELS), 2):
        row = []
        for j in range(i, min(i + 2, len(LEVELS))):
            row.append(InlineKeyboardButton(f"   {LEVELS[j]}   ", callback_data=f"level_{j}"))
        keyboard.append(row)
    return keyboard

# === ОСНОВНАЯ АНКЕТА ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    log_user_action(user_id, username, "Запустил бота (/start)")

    user = await get_user(user_id)
    if user and user["display_name"]:
        from .profile import show_profile
        await show_profile(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text("🎮 Добро пожаловать! Какой у тебя игровой ник?")
        return NICKNAME

async def nickname_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["display_name"] = update.message.text.strip()
    context.user_data["telegram_username"] = update.effective_user.username

    keyboard = make_initial_game_keyboard()
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("В какие игры ты играешь?", reply_markup=reply_markup)
    return GAME_SELECTION

async def game_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    game_index = int(query.data.split("_")[1])
    selected_game = GAMES[game_index]

    if "selected_games" not in context.user_data:
        context.user_data["selected_games"] = []
    if selected_game not in context.user_data["selected_games"]:
        context.user_data["selected_games"].append(selected_game)

    keyboard = []
    for i in range(0, len(GAMES), 3):
        row = []
        for j in range(i, min(i + 3, len(GAMES))):
            game = GAMES[j]
            if game not in context.user_data["selected_games"]:
                row.append(InlineKeyboardButton(f"   {game}   ", callback_data=f"game_{j}"))
        if row:
            keyboard.append(row)

    if context.user_data["selected_games"]:
        keyboard.append([InlineKeyboardButton("➡️ Далее (уровень)", callback_data="next_to_level")])

    text = f"Выбрано: {', '.join(context.user_data['selected_games'])}\n\nВыбрать ещё или перейти к уровню?"

    try:
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise

    return GAME_SELECTION

async def next_to_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = make_level_keyboard()
    await query.edit_message_text("Какой у тебя уровень?", reply_markup=InlineKeyboardMarkup(keyboard))
    return LEVEL_SELECTION

async def level_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    level_index = int(query.data.split("_")[1])
    level = LEVELS[level_index]
    user_id = update.effective_user.id
    telegram_username = update.effective_user.username
    data = {
        "display_name": context.user_data["display_name"],
        "telegram_username": telegram_username,
        "games": context.user_data["selected_games"],
        "level": level,
        "promo_clicked": False  # по умолчанию — не кликал
    }
    await save_user(user_id, data)

    # Логирование
    games_str = ", ".join(data["games"])
    log_user_action(
        user_id,
        telegram_username,
        f"Завершил анкету | Игры: {games_str} | Уровень: {level}"
    )

    # Промо-сообщение с кнопкой
    promo_message = (
        "🎯 <b>Исходя из всей предоставленной вами информации, вам предложена следующая акция!</b>\n\n"
        "Это бустер ваших навыков в выбранных играх и помощь в турнирах.\n\n"
        "Успейте воспользоваться! Предложение действует ограниченное время."
    )
    keyboard = [[InlineKeyboardButton("🎁 Получить акцию", callback_data="promo_click")]]
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=promo_message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

    from .profile import show_profile
    await show_profile(update, context)
    return ConversationHandler.END

# === ОБРАБОТКА КЛИКА ПО ПРОМО ===
async def handle_promo_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    username = update.effective_user.username

    from database import set_promo_clicked
    await set_promo_clicked(user_id)

    from logger import log_user_action
    log_user_action(user_id, username, "Нажал на промо-кнопку")

    # Меняем ТОЛЬКО кнопку, текст остаётся
    await query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Уже перешёл", callback_data="promo_done")]
        ])
    )

    # И сразу отправляем ссылку
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🔗 Ваша персональная ссылка:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Получить акцию", url="https://education-game.ru/")]
        ])
    )

# === РЕДАКТИРОВАНИЕ (без изменений, но для полноты) ===
async def edit_profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "Выбери, что хочешь изменить:"
    keyboard = [
        [InlineKeyboardButton("   📝 Поменять ник   ", callback_data="edit_nickname")],
        [InlineKeyboardButton("   🎮 Поменять игры   ", callback_data="edit_games")],
        [InlineKeyboardButton("   📊 Поменять уровень   ", callback_data="edit_level")],
        [InlineKeyboardButton("   ⬅️ Назад в профиль   ", callback_data="back_to_profile")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return EDIT_PROFILE

async def start_edit_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Введите новый игровой ник:")
    return EDIT_NICKNAME

async def save_new_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_nick = update.message.text.strip()
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Ошибка: профиль не найден.")
        return ConversationHandler.END
    user["display_name"] = new_nick
    await save_user(user_id, user)
    await update.message.reply_text("✅ Никнейм обновлён!")
    from .profile import show_profile_from_edit
    await show_profile_from_edit(None, context, user, chat_id=update.effective_chat.id)
    return ConversationHandler.END

async def start_edit_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["selected_games"] = []
    keyboard = make_initial_game_keyboard()
    await query.edit_message_text("Выберите новые игры:", reply_markup=InlineKeyboardMarkup(keyboard))
    return EDIT_GAMES

async def edit_game_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    game_index = int(query.data.split("_")[1])
    selected_game = GAMES[game_index]

    if "selected_games" not in context.user_data:
        context.user_data["selected_games"] = []
    if selected_game not in context.user_data["selected_games"]:
        context.user_data["selected_games"].append(selected_game)

    keyboard = []
    for i in range(0, len(GAMES), 3):
        row = []
        for j in range(i, min(i + 3, len(GAMES))):
            game = GAMES[j]
            if game not in context.user_data["selected_games"]:
                row.append(InlineKeyboardButton(f"   {game}   ", callback_data=f"game_{j}"))
        if row:
            keyboard.append(row)

    if context.user_data["selected_games"]:
        keyboard.append([InlineKeyboardButton("➡️ Далее (уровень)", callback_data="next_to_level")])

    text = f"Выбрано: {', '.join(context.user_data['selected_games'])}\n\nВыбрать ещё или завершить?"
    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise
    return EDIT_GAMES

async def finish_edit_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("Ошибка: профиль не найден.")
        return ConversationHandler.END
    user["games"] = context.user_data.get("selected_games", [])
    await save_user(user_id, user)
    await query.edit_message_text("✅ Игры обновлены!")
    from .profile import show_profile_from_edit
    await show_profile_from_edit(None, context, user, query=query)
    return ConversationHandler.END

async def start_edit_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = make_level_keyboard()
    await query.edit_message_text("Выберите новый уровень:", reply_markup=InlineKeyboardMarkup(keyboard))
    return EDIT_LEVEL

async def save_new_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    level_index = int(query.data.split("_")[1])
    level = LEVELS[level_index]
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("Ошибка: профиль не найден.")
        return ConversationHandler.END
    user["level"] = level
    await save_user(user_id, user)
    await query.edit_message_text("✅ Уровень обновлён!")
    from .profile import show_profile_from_edit
    await show_profile_from_edit(None, context, user, query=query)
    return ConversationHandler.END

async def back_to_profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = await get_user(update.effective_user.id)
    if user:
        from .profile import show_profile_from_edit
        await show_profile_from_edit(None, context, user, query=query)
    else:
        await query.edit_message_text("Ошибка профиля.")
    return ConversationHandler.END

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = "📘 Главное меню"
    keyboard = [
        [InlineKeyboardButton("   📘 Гайды   ", callback_data="menu_guides")],
        [InlineKeyboardButton("   📊 Моя статистика   ", callback_data="menu_stats")],
        [InlineKeyboardButton("   ℹ️ О платформе   ", callback_data="menu_info")],
        [InlineKeyboardButton("   🌐 Перейти на сайт   ", url="https://education-game.ru/")],
        [InlineKeyboardButton("   👤 Профиль   ", callback_data="menu_profile")]
    ]
    if query:
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("start", start),
        CallbackQueryHandler(edit_profile_menu, pattern="^edit_profile$")
    ],
    states={
        NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, nickname_input)],
        GAME_SELECTION: [
            CallbackQueryHandler(game_selected, pattern=r"^game_\d+$"),
            CallbackQueryHandler(next_to_level, pattern=r"^next_to_level$")
        ],
        LEVEL_SELECTION: [CallbackQueryHandler(level_selected, pattern=r"^level_\d+$")],
        EDIT_PROFILE: [
            CallbackQueryHandler(start_edit_nickname, pattern="^edit_nickname$"),
            CallbackQueryHandler(start_edit_games, pattern="^edit_games$"),
            CallbackQueryHandler(start_edit_level, pattern="^edit_level$"),
            CallbackQueryHandler(back_to_profile_handler, pattern="^back_to_profile$")
        ],
        EDIT_NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_nickname)],
        EDIT_GAMES: [
            CallbackQueryHandler(edit_game_selected, pattern=r"^game_\d+$"),
            CallbackQueryHandler(finish_edit_games, pattern=r"^next_to_level$")
        ],
        EDIT_LEVEL: [CallbackQueryHandler(save_new_level, pattern=r"^level_\d+$")],
    },
    fallbacks=[CommandHandler("start", start)]
)