from telegram import Update
from telegram.ext import ContextTypes
from database.db import get_session
from database.models import Event, Rating, User, EventStatus
from utils.decorators import registered_user
from utils.keyboards import get_rating_keyboard, get_events_to_rate_keyboard
import logging

logger = logging.getLogger(__name__)

@registered_user
async def start_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс оценки мероприятия"""
    with get_session() as session:
        telegram_id = update.effective_user.id
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        
        # Получаем закрытые мероприятия, которые пользователь еще не оценил
        closed_events = session.query(Event).filter_by(status=EventStatus.CLOSED).all()
        
        unrated_events = []
        for event in closed_events:
            existing_rating = session.query(Rating).filter_by(
                user_id=user.id,
                event_id=event.id
            ).first()
            
            if not existing_rating:
                unrated_events.append(event)
        
        if not unrated_events:
            await update.message.reply_text(
                "ℹ️ Нет завершенных мероприятий для оценки.\n\n"
                "Вы уже оценили все доступные мероприятия!"
            )
            return
        
        await update.message.reply_text(
            "⭐ Выберите мероприятие для оценки:",
            reply_markup=get_events_to_rate_keyboard(unrated_events)
        )

@registered_user
async def handle_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка оценки"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data.split("_")
    
    if callback_data[1] == "select":
        # Выбрано мероприятие для оценки
        event_id = int(callback_data[2])
        
        with get_session() as session:
            event = session.query(Event).filter_by(id=event_id).first()
            
            if not event:
                await query.edit_message_text("❌ Мероприятие не найдено.")
                return
        
        await query.edit_message_text(
            f"⭐ Оцените мероприятие:\n\n"
            f"📅 {event.name}\n\n"
            f"Выберите количество звезд:",
            reply_markup=get_rating_keyboard(event_id)
        )
    
    else:
        # Выбрана оценка
        event_id = int(callback_data[1])
        rating_value = int(callback_data[2])
        
        telegram_id = update.effective_user.id
        
        with get_session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            event = session.query(Event).filter_by(id=event_id).first()
            
            if not event:
                await query.edit_message_text("❌ Мероприятие не найдено.")
                return
            
            # Проверяем, не оставлена ли уже оценка
            existing_rating = session.query(Rating).filter_by(
                user_id=user.id,
                event_id=event.id
            ).first()
            
            if existing_rating:
                await query.edit_message_text("ℹ️ Вы уже оценили это мероприятие.")
                return
            
            # Сохраняем оценку
            rating = Rating(
                user_id=user.id,
                event_id=event.id,
                rating=rating_value
            )
            session.add(rating)
            session.commit()
            
            stars = "⭐" * rating_value
            
            await query.edit_message_text(
                f"✅ Спасибо за оценку!\n\n"
                f"📅 Мероприятие: {event.name}\n"
                f"⭐ Ваша оценка: {stars}\n\n"
                f"Хотите оставить комментарий? Напишите его следующим сообщением.\n"
                f"Или отправьте /skip чтобы пропустить."
            )
            
            # Сохраняем в контексте для добавления комментария
            context.user_data['pending_rating_id'] = rating.id
            
            logger.info(f"Пользователь {telegram_id} оценил мероприятие {event_id} на {rating_value}")

@registered_user
async def handle_rating_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка комментария к оценке"""
    if 'pending_rating_id' not in context.user_data:
        return
    
    rating_id = context.user_data['pending_rating_id']
    comment = update.message.text
    
    if comment == '/skip':
        await update.message.reply_text("✅ Оценка сохранена без комментария.")
        context.user_data.pop('pending_rating_id', None)
        return
    
    with get_session() as session:
        rating = session.query(Rating).filter_by(id=rating_id).first()
        
        if rating:
            rating.comment = comment
            session.commit()
            
            await update.message.reply_text(
                "✅ Спасибо! Ваша оценка и комментарий сохранены."
            )
            
            logger.info(f"Добавлен комментарий к оценке #{rating_id}")
        else:
            await update.message.reply_text("❌ Ошибка сохранения комментария.")
    
    context.user_data.pop('pending_rating_id', None)
