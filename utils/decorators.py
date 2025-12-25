from functools import wraps
from telegram import Update
from database.db import get_session
from database.models import User, UserRole
import logging

logger = logging.getLogger(__name__)

def admin_only(func):
    """Декоратор для проверки прав администратора"""
    @wraps(func)
    async def wrapper(update: Update, context, *args, **kwargs):
        telegram_id = update.effective_user.id
        
        with get_session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            
            if not user or user.role != UserRole.ADMIN:
                if update.message:
                    await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
                elif update.callback_query:
                    await update.callback_query.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
                return
        
        return await func(update, context, *args, **kwargs)
    return wrapper

def manager_or_admin(func):
    """Декоратор для проверки прав менеджера или администратора"""
    @wraps(func)
    async def wrapper(update: Update, context, *args, **kwargs):
        telegram_id = update.effective_user.id
        
        with get_session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            
            # АДМИН АВТОМАТИЧЕСКИ МОЖЕТ ВСЁ ЧТО И МЕНЕДЖЕР
            if not user or user.role not in [UserRole.MANAGER, UserRole.ADMIN]:
                if update.message:
                    await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
                elif update.callback_query:
                    await update.callback_query.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
                return
        
        return await func(update, context, *args, **kwargs)
    return wrapper

def registered_user(func):
    """Декоратор для проверки регистрации пользователя"""
    @wraps(func)
    async def wrapper(update: Update, context, *args, **kwargs):
        telegram_id = update.effective_user.id
        
        with get_session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            
            if not user:
                # Создаем пользователя автоматически
                user = User(
                    telegram_id=telegram_id,
                    username=update.effective_user.username,
                    full_name=update.effective_user.full_name,
                    role=UserRole.USER
                )
                session.add(user)
                session.commit()
                logger.info(f"Создан новый пользователь: {telegram_id}")
        
        return await func(update, context, *args, **kwargs)
    return wrapper
