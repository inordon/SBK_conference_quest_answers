from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from config import Config
from database.models import Base
import logging

logger = logging.getLogger(__name__)

engine = create_engine(Config.DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Инициализация базы данных"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        raise

@contextmanager
def get_session() -> Session:
    """Контекстный менеджер для работы с сессией"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка в сессии БД: {e}")
        raise
    finally:
        session.close()

def get_db():
    """Получить сессию БД (для dependency injection)"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()
