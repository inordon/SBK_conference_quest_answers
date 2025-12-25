import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    WORK_GROUP_ID = int(os.getenv('WORK_GROUP_ID')) if os.getenv('WORK_GROUP_ID') else None
    INITIAL_ADMIN_ID = int(os.getenv('INITIAL_ADMIN_ID')) if os.getenv('INITIAL_ADMIN_ID') else None
    
    # Database
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT')
    DB_NAME = os.getenv('DB_NAME')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    
    # Формируем DATABASE_URL из компонентов
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Settings
    TIMEZONE = os.getenv('TIMEZONE', 'Europe/Moscow')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Rating settings
    RATING_MIN = 1
    RATING_MAX = 5
    
    # Validation
    @classmethod
    def validate(cls):
        required = [
            ('BOT_TOKEN', cls.BOT_TOKEN),
            ('WORK_GROUP_ID', cls.WORK_GROUP_ID),
            ('INITIAL_ADMIN_ID', cls.INITIAL_ADMIN_ID),
            ('DB_HOST', cls.DB_HOST),
            ('DB_PORT', cls.DB_PORT),
            ('DB_NAME', cls.DB_NAME),
            ('DB_USER', cls.DB_USER),
            ('DB_PASSWORD', cls.DB_PASSWORD)
        ]
        
        missing = [key for key, value in required if not value]
        
        if missing:
            raise ValueError(f"Missing required config: {', '.join(missing)}")
        
        # Проверяем формат WORK_GROUP_ID (должен быть отрицательным)
        if cls.WORK_GROUP_ID >= 0:
            raise ValueError("WORK_GROUP_ID должен быть отрицательным числом (ID супергруппы)")
