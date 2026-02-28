# database.py
import aiosqlite
import json
import os

USERS_DB = "data/users.db"
os.makedirs("data", exist_ok=True)

async def init_db():
    async with aiosqlite.connect(USERS_DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                display_name TEXT,
                telegram_username TEXT,
                games TEXT,
                level TEXT,
                tournaments INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                rating INTEGER DEFAULT 1000,
                promo_clicked INTEGER DEFAULT 0  -- 0 = нет, 1 = да
            )
        """)
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(USERS_DB) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                raw_games = row[3]
                games = []
                if raw_games and raw_games.strip() != "":
                    try:
                        games = json.loads(raw_games)
                    except (json.JSONDecodeError, TypeError):
                        games = []

                return {
                    "user_id": row[0],
                    "display_name": row[1],
                    "telegram_username": row[2],
                    "games": games,
                    "level": row[4],
                    "tournaments": row[5],
                    "wins": row[6],
                    "rating": row[7],
                    "promo_clicked": bool(row[8])  # ← новое поле
                }
    return None

async def save_user(user_id: int,  data: dict):
    games_str = json.dumps(data.get("games", []))
    async with aiosqlite.connect(USERS_DB) as db:
        await db.execute("""
            INSERT OR REPLACE INTO users
            (user_id, display_name, telegram_username, games, level, tournaments, wins, rating, promo_clicked)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            data.get("display_name"),
            data.get("telegram_username"),
            games_str,
            data.get("level"),
            data.get("tournaments", 0),
            data.get("wins", 0),
            data.get("rating", 1000),
            int(data.get("promo_clicked", False))
        ))
        await db.commit()

async def set_promo_clicked(user_id: int):
    """Устанавливает флаг promo_clicked = 1"""
    async with aiosqlite.connect(USERS_DB) as db:
        await db.execute("UPDATE users SET promo_clicked = 1 WHERE user_id = ?", (user_id,))
        await db.commit()