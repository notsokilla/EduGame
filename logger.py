import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("EdugameBot")

def log_user_action(user_id: int, username: str | None, action: str):
    """Логирует действия пользователя (админ/не админ — определяется по наличию пароля в логе)"""
    tag = f"@{username}" if username else f"user{user_id}"
    # Просто пишем как есть — админство теперь определяется по действию (например, "Вошёл в админку")
    logger.info(f"{tag} | {action}")