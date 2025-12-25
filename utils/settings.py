from database.db import get_session
from database.models import BotSetting
from datetime import datetime

def get_setting(key: str, default: str = None) -> str:
    """Получить настройку по ключу"""
    with get_session() as session:
        setting = session.query(BotSetting).filter_by(key=key).first()
        return setting.value if setting else default

def set_setting(key: str, value: str, user_id: int = None) -> None:
    """Установить настройку"""
    with get_session() as session:
        setting = session.query(BotSetting).filter_by(key=key).first()
        
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
            setting.updated_by = user_id
        else:
            setting = BotSetting(
                key=key,
                value=value,
                updated_by=user_id
            )
            session.add(setting)
        
        session.commit()

# Дефолтные сообщения
DEFAULT_NO_EVENTS_MESSAGE = """ℹ️ В данный момент нет активных мероприятий для обратной связи.

Следите за объявлениями о новых мероприятиях!"""

DEFAULT_WELCOME_MESSAGE = """👋 Добро пожаловать в систему обратной связи!

Здесь вы можете:
📝 Оставлять отзывы о мероприятиях
⭐ Оценивать завершенные события
💬 Получать ответы от нашей команды"""
