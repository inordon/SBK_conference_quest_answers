from telegram import Update
from telegram.ext import ContextTypes
from database.db import get_session
from database.models import Feedback, User
from utils.decorators import manager_or_admin
from config import Config
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@manager_or_admin
async def handle_manager_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответа менеджера на вопрос пользователя"""
    if update.effective_chat.id != Config.WORK_GROUP_ID:
        return
    
    if not update.message.reply_to_message:
        return
    
    reply_to_message_id = update.message.reply_to_message.message_id
    manager_reply = update.message.text
    
    with get_session() as session:
        feedback = session.query(Feedback).filter_by(
            topic_message_id=reply_to_message_id
        ).first()
        
        if not feedback:
            return
        
        user = session.query(User).filter_by(id=feedback.user_id).first()
        manager = session.query(User).filter_by(
            telegram_id=update.effective_user.id
        ).first()
        
        if not user or not manager:
            return
        
        feedback.answered_by = manager.id
        feedback.answered_at = datetime.utcnow()
        session.commit()
        
        try:
            manager_name = manager.full_name or manager.username or "Менеджер"
            
            await context.bot.send_message(
                chat_id=user.telegram_id,
                text=f"💬 Ответ на ваш вопрос:\n"
                     f"👔 От: {manager_name}\n"
                     f"📅 Мероприятие: {feedback.event.name}\n\n"
                     f"{manager_reply}"
            )
            
            await update.message.reply_text("✅ Ответ отправлен пользователю")
            
            logger.info(f"Менеджер {manager.telegram_id} ответил на вопрос #{feedback.id}")
        
        except Exception as e:
            logger.error(f"Ошибка отправки ответа пользователю: {e}")
            await update.message.reply_text("❌ Ошибка отправки ответа")
