from telegram import Update
from telegram.ext import ContextTypes
from database.db import get_session
from database.models import Event, EventStatus, Feedback, FeedbackStatus, User
from utils.decorators import registered_user
from utils.keyboards import get_events_keyboard
from utils.settings import get_setting, DEFAULT_NO_EVENTS_MESSAGE
from config import Config
import logging

logger = logging.getLogger(__name__)

@registered_user
async def start_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс задавания вопроса"""
    with get_session() as session:
        active_events = session.query(Event).filter_by(status=EventStatus.ACTIVE).all()
        
        if not active_events:
            no_events_msg = get_setting('no_events_message', DEFAULT_NO_EVENTS_MESSAGE)
            await update.message.reply_text(no_events_msg)
            return
        
        await update.message.reply_text(
            "📅 Выберите мероприятие, по которому хотите задать вопрос:",
            reply_markup=get_events_keyboard(active_events)
        )

async def handle_event_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора мероприятия"""
    query = update.callback_query
    
    event_id = int(query.data.split("_")[1])
    
    with get_session() as session:
        event = session.query(Event).filter_by(id=event_id).first()
        
        if not event:
            await query.edit_message_text("❌ Мероприятие не найдено.")
            return
        
        if event.status != EventStatus.ACTIVE:
            await query.edit_message_text("❌ Это мероприятие уже завершено.")
            return
        
        context.user_data['selected_event_id'] = event_id
        
        await query.edit_message_text(
            f"❓ Вы выбрали мероприятие: {event.name}\n\n"
            f"Напишите ваш вопрос или отправьте фото с вопросом.\n"
            f"Вы можете отправить только текст или текст с фото.\n\n"
            f"Отмена: /cancel"
        )

async def handle_question_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового вопроса"""
    if 'selected_event_id' not in context.user_data:
        return
    
    event_id = context.user_data['selected_event_id']
    text = update.message.text
    
    await save_question(update, context, event_id, text, photo_file_id=None)

async def handle_question_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка вопроса с фото"""
    if 'selected_event_id' not in context.user_data:
        return
    
    event_id = context.user_data['selected_event_id']
    text = update.message.caption or "Вопрос с фото"
    photo_file_id = update.message.photo[-1].file_id
    
    await save_question(update, context, event_id, text, photo_file_id)

async def save_question(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                       event_id: int, text: str, photo_file_id: str = None):
    """Сохранение вопроса в БД и отправка в рабочую группу"""
    telegram_id = update.effective_user.id
    
    with get_session() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        event = session.query(Event).filter_by(id=event_id).first()
        
        if not event or event.status != EventStatus.ACTIVE:
            await update.message.reply_text("❌ Мероприятие более недоступно.")
            context.user_data.pop('selected_event_id', None)
            return
        
        feedback = Feedback(
            user_id=user.id,
            event_id=event.id,
            message_text=text,
            photo_file_id=photo_file_id,
            status=FeedbackStatus.NEW
        )
        session.add(feedback)
        session.flush()
        
        try:
            user_info = f"👤 {user.full_name or user.username or 'Пользователь'}"
            if user.username:
                user_info += f" (@{user.username})"
            
            message_text = (
                f"❓ Новый вопрос #{feedback.id}\n\n"
                f"{user_info}\n"
                f"📅 Мероприятие: {event.name}\n\n"
                f"💬 Вопрос:\n{text}"
            )
            
            if photo_file_id:
                sent_message = await context.bot.send_photo(
                    chat_id=Config.WORK_GROUP_ID,
                    message_thread_id=event.topic_id,
                    photo=photo_file_id,
                    caption=message_text
                )
            else:
                sent_message = await context.bot.send_message(
                    chat_id=Config.WORK_GROUP_ID,
                    message_thread_id=event.topic_id,
                    text=message_text
                )
            
            feedback.topic_message_id = sent_message.message_id
            feedback.status = FeedbackStatus.IN_PROGRESS
            session.commit()
            
            await update.message.reply_text(
                "✅ Спасибо за ваш вопрос!\n\n"
                "Ваш вопрос передан организаторам. "
                "Вы получите ответ в этом чате."
            )
            
            context.user_data.pop('selected_event_id', None)
            
            logger.info(f"Создан вопрос #{feedback.id} от пользователя {telegram_id}")
        
        except Exception as e:
            logger.error(f"Ошибка отправки в рабочую группу: {e}")
            session.rollback()
            await update.message.reply_text(
                "❌ Ошибка отправки вопроса. Попробуйте позже."
            )
