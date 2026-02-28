# handlers/guides_db.py
import aiosqlite
import json
import os

GUIDES_DB = "data/guides.db"
from database import USERS_DB  # ← импортируем путь к users.db

os.makedirs("data", exist_ok=True)

async def init_guides_db():
    async with aiosqlite.connect(GUIDES_DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                level TEXT NOT NULL,
                media_type TEXT,
                media_file_id TEXT
            )
        """)
        await db.commit()

async def add_guide(game, title, description, level, media_type=None, media_file_id=None):
    async with aiosqlite.connect(GUIDES_DB) as db:
        await db.execute("""
            INSERT INTO guides (game, title, description, level, media_type, media_file_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (game, title, description, level, media_type, media_file_id))
        await db.commit()

async def get_all_guides_with_details():
    async with aiosqlite.connect(GUIDES_DB) as db:
        async with db.execute("SELECT * FROM guides ORDER BY game, level") as cursor:
            rows = await cursor.fetchall()
    return [
        {
            "id": r[0],
            "game": r[1],
            "title": r[2],
            "description": r[3] or "",
            "level": r[4],
            "media_type": r[5],
            "media_file_id": r[6]
        }
        for r in rows
    ]

async def get_guides_by_game_and_level(game: str, user_level: str):
    level_order = {"Новичок": 0, "Средний": 1, "Продвинутый": 2, "Профи": 3}
    user_rank = level_order.get(user_level, 0)

    async with aiosqlite.connect(GUIDES_DB) as db:
        async with db.execute("SELECT * FROM guides WHERE game = ?", (game,)) as cursor:
            rows = await cursor.fetchall()

    filtered = []
    for r in rows:
        guide_level = r[4]
        if level_order.get(guide_level, -1) <= user_rank:
            filtered.append({
                "id": r[0],
                "game": r[1],
                "title": r[2],
                "description": r[3],
                "level": r[4],
                "media_type": r[5],
                "media_file_id": r[6]
            })
    return filtered

# === ОБНОВЛЁННАЯ ФУНКЦИЯ: получить пользователей с promo_clicked ===
async def get_users_for_admin():
    async with aiosqlite.connect(USERS_DB) as db:
        async with db.execute("""
            SELECT user_id, display_name, telegram_username, games, level, promo_clicked
            FROM users
        """) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "user_id": r[0],
                    "display_name": r[1],
                    "telegram_username": r[2],
                    "games": json.loads(r[3]) if r[3] and r[3].strip() != "" else [],
                    "level": r[4],
                    "promo_clicked": bool(r[5])  # ← теперь есть!
                }
                for r in rows
            ]

# В handlers/guides_db.py
async def delete_guide_by_id(guide_id: int):
    async with aiosqlite.connect(GUIDES_DB) as db:
        await db.execute("DELETE FROM guides WHERE id = ?", (guide_id,))
        await db.commit()