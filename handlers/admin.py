from telegram import Update
from telegram.ext import ContextTypes
from database.db import get_session
from database.models import User, Event, EventStatus, UserRole, Feedback, Rating
from utils.decorators import admin_only
from utils.keyboards import (
    get_events_management_menu, get_users_management_menu, 
    get_stats_menu, get_settings_menu, get_back_button,
    get_events_to_close_keyboard, get_events_for_report_keyboard,
    get_confirm_keyboard
)
from config import Config
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

# ============ МЕНЮ ============

@admin_only
async def show_events_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню управления мероприятиями"""
    await update.message.reply_text(
        "📅 <b>Управление мероприятиями</b>\n\nВыберите действие:",
        parse_mode='HTML',
        reply_markup=get_events_management_menu()
    )

@admin_only
async def show_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню управления пользователями"""
    await update.message.reply_text(
        "👥 <b>Управление пользователями</b>\n\nВыберите действие:",
        parse_mode='HTML',
        reply_markup=get_users_management_menu()
    )

@admin_only
async def show_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню статистики"""
    await update.message.reply_text(
        "📊 <b>Статистика и отчеты</b>\n\nВыберите действие:",
        parse_mode='HTML',
        reply_markup=get_stats_menu()
    )

@admin_only
async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню настроек"""
    await update.message.reply_text(
        "⚙️ <b>Настройки бота</b>\n\nВыберите действие:",
        parse_mode='HTML',
        reply_markup=get_settings_menu()
    )


async def handle_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Центральный обработчик всех callback запросов"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    telegram_id = update.effective_user.id
    
    from handlers import user, rating
    
    # ВОПРОСЫ И ОЦЕНКИ
    if data.startswith("event_"):
        await user.handle_event_selection(update, context)
        return
    
    if data.startswith("rate_"):
        await rating.handle_rating(update, context)
        return
    
    if data == "cancel":
        context.user_data.clear()
        try:
            await query.edit_message_text("❌ Действие отменено.")
        except Exception:
            pass
        return
    
    if data == "main_menu":
        await query.edit_message_text("👋 Главное меню\n\nИспользуйте кнопки ниже для навигации.")
        return
    
    # Проверка прав
    with get_session() as session:
        db_user = session.query(User).filter_by(telegram_id=telegram_id).first()
        is_admin = db_user and db_user.role == UserRole.ADMIN
    
    # ====== МЕРОПРИЯТИЯ ======
    if data == "events_menu":
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        await query.edit_message_text(
            "📅 <b>Управление мероприятиями</b>\n\nВыберите действие:",
            parse_mode='HTML', reply_markup=get_events_management_menu())
    
    elif data == "events_create":
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        await create_event_start(update, context)
    
    elif data == "events_list":
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        await list_events_callback(update, context)
    
    elif data == "events_close":
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        await close_event_select(update, context)
    
    elif data.startswith("close_event_"):
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        event_id = int(data.split("_")[2])
        await close_event_confirm(update, context, event_id)
    
    elif data.startswith("confirm_close_") and not data.startswith("confirm_close_all"):
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        event_id = int(data.split("_")[2])
        await close_event_execute(update, context, event_id)
    
    elif data.startswith("cancel_close_") and not data.startswith("cancel_close_all"):
        await query.edit_message_text("❌ Закрытие отменено.", reply_markup=get_back_button("events_menu"))
    
    elif data == "events_close_all":
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        await close_all_events_confirm(update, context)
    
    elif data.startswith("confirm_close_all"):
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        await close_all_events_execute(update, context)
    
    elif data.startswith("cancel_close_all"):
        await query.edit_message_text("❌ Отменено.", reply_markup=get_back_button("events_menu"))
    
    # ====== ПОЛЬЗОВАТЕЛИ ======
    elif data == "users_menu":
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        await query.edit_message_text(
            "👥 <b>Управление пользователями</b>\n\nВыберите действие:",
            parse_mode='HTML', reply_markup=get_users_management_menu())
    
    elif data == "users_list":
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        await list_users_callback(update, context)
    
    elif data == "users_add_admin":
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        await add_admin_start(update, context)
    
    elif data == "users_add_manager":
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        await add_manager_start(update, context)
    
    elif data == "users_remove_role":
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        await remove_role_start(update, context)
    
    # ====== СТАТИСТИКА ======
    elif data == "stats_menu":
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        await query.edit_message_text(
            "📊 <b>Статистика и отчеты</b>\n\nВыберите действие:",
            parse_mode='HTML', reply_markup=get_stats_menu())
    
    elif data == "stats_general":
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        await show_stats_callback(update, context)
    
    elif data == "stats_export_all":
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        await export_report_all(update, context)
    
    elif data == "stats_export_event":
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        await export_report_select_event(update, context)
    
    elif data.startswith("report_event_"):
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        event_id = int(data.split("_")[2])
        await export_report_event(update, context, event_id)
    
    # ====== НАСТРОЙКИ ======
    elif data == "settings_menu":
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        await query.edit_message_text(
            "⚙️ <b>Настройки бота</b>\n\nВыберите действие:",
            parse_mode='HTML', reply_markup=get_settings_menu())
    
    elif data == "settings_no_events":
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        await edit_no_events_message_start(update, context)
    
    elif data == "settings_view":
        if not is_admin:
            await query.answer("❌ У вас нет прав", show_alert=True)
            return
        await view_settings_callback(update, context)


# ============ МЕРОПРИЯТИЯ ============

async def create_event_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['creating_event'] = True
    await query.edit_message_text(
        "📝 <b>Создание нового мероприятия</b>\n\n"
        "Введите название мероприятия:\n\n"
        "<i>Например: Конференция по DevOps 2025</i>\n\nОтмена: /cancel",
        parse_mode='HTML')


async def handle_event_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'creating_event' not in context.user_data:
        return
    
    event_name = update.message.text.strip()
    if not event_name:
        await update.message.reply_text("❌ Название не может быть пустым. Попробуйте еще раз:")
        return
    
    if len(event_name) > 128:
        await update.message.reply_text(
            f"❌ Название слишком длинное ({len(event_name)} символов).\n"
            f"Максимум 128 символов. Попробуйте еще раз:")
        return
    
    context.user_data.pop('creating_event', None)
    await create_event_execute(update, context, event_name)


async def create_event_execute(update: Update, context: ContextTypes.DEFAULT_TYPE, event_name: str):
    try:
        topic = await context.bot.create_forum_topic(chat_id=Config.WORK_GROUP_ID, name=event_name[:128])
        
        with get_session() as session:
            telegram_id = update.effective_user.id
            admin_user = session.query(User).filter_by(telegram_id=telegram_id).first()
            
            event = Event(
                name=event_name,
                topic_id=topic.message_thread_id,
                created_by=admin_user.id if admin_user else None,
                status=EventStatus.ACTIVE
            )
            session.add(event)
            session.commit()
            
            await update.message.reply_text(
                f"✅ Мероприятие создано!\n\n📅 Название: {event_name}\n🆔 ID: {event.id}\n"
                f"📝 Топик создан в рабочей группе\n\nПользователи могут начать задавать вопросы.",
                reply_markup=get_back_button("events_menu"))
            
            await context.bot.send_message(
                chat_id=Config.WORK_GROUP_ID,
                message_thread_id=topic.message_thread_id,
                text=f"🎉 Начат сбор вопросов по мероприятию:\n\n📅 {event_name}\n🆔 ID мероприятия: {event.id}\n\n"
                     f"Менеджеры, отвечайте на вопросы пользователей через Reply.")
            
            logger.info(f"Создано мероприятие {event.id}: {event_name}")
    
    except Exception as e:
        logger.error(f"Ошибка создания мероприятия: {e}")
        await update.message.reply_text(
            f"❌ Ошибка создания мероприятия: {str(e)}\n\nУбедитесь, что:\n"
            f"1. Бот является администратором рабочей группы\n"
            f"2. В группе включены топики (Topics)\n3. У бота есть права на управление топиками")


async def list_events_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    with get_session() as session:
        events = session.query(Event).order_by(Event.created_at.desc()).all()
        
        if not events:
            await query.edit_message_text("📋 Мероприятий пока нет.", reply_markup=get_back_button("events_menu"))
            return
        
        message = "📋 <b>Список мероприятий:</b>\n\n"
        for event in events:
            status_emoji = "✅" if event.status == EventStatus.ACTIVE else "🔒"
            feedback_count = len(event.feedbacks)
            rating_count = len(event.ratings)
            avg_rating = "—"
            if rating_count > 0:
                avg = sum(r.rating for r in event.ratings) / rating_count
                avg_rating = f"{avg:.1f}⭐"
            
            message += f"{status_emoji} <b>#{event.id}</b> {event.name}\n"
            message += f"   💬 Вопросов: {feedback_count} | ⭐ Оценок: {rating_count} ({avg_rating})\n"
            message += f"   📅 Создано: {event.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            if event.status == EventStatus.CLOSED and event.closed_at:
                message += f"   🔒 Закрыто: {event.closed_at.strftime('%d.%m.%Y %H:%M')}\n"
            message += "\n"
        
        await query.edit_message_text(message, parse_mode='HTML', reply_markup=get_back_button("events_menu"))


async def close_event_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    with get_session() as session:
        active_events = session.query(Event).filter_by(status=EventStatus.ACTIVE).all()
        
        if not active_events:
            await query.edit_message_text("ℹ️ Нет активных мероприятий для закрытия.",
                                          reply_markup=get_back_button("events_menu"))
            return
        
        await query.edit_message_text("🔒 Выберите мероприятие для закрытия:",
                                      reply_markup=get_events_to_close_keyboard(active_events))


async def close_event_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id: int):
    query = update.callback_query
    
    with get_session() as session:
        event = session.query(Event).filter_by(id=event_id).first()
        
        if not event:
            await query.edit_message_text("❌ Мероприятие не найдено.",
                                          reply_markup=get_back_button("events_menu"))
            return
        
        await query.edit_message_text(
            f"🔒 Закрыть мероприятие?\n\n📅 {event.name}\n🆔 ID: {event.id}\n\n"
            f"После закрытия пользователям будет предложено оценить мероприятие.",
            reply_markup=get_confirm_keyboard("close", event_id))


async def close_event_execute(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id: int):
    query = update.callback_query
    
    with get_session() as session:
        event = session.query(Event).filter_by(id=event_id).first()
        
        if not event:
            await query.edit_message_text("❌ Мероприятие не найдено.",
                                          reply_markup=get_back_button("events_menu"))
            return
        
        event.status = EventStatus.CLOSED
        event.closed_at = datetime.utcnow()
        event_name = event.name
        topic_id = event.topic_id
        feedbacks_count = len(event.feedbacks)
        user_ids = set(f.user_id for f in event.feedbacks)
        session.commit()
        
        if topic_id:
            try:
                await context.bot.send_message(
                    chat_id=Config.WORK_GROUP_ID,
                    message_thread_id=topic_id,
                    text=f"🔒 Сбор вопросов завершен!\n\n📊 Всего вопросов: {feedbacks_count}")
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление: {e}")
        
        await request_ratings_for_event(context, event_id, event_name, user_ids)
        
        await query.edit_message_text(
            f"✅ Мероприятие закрыто!\n\n📅 {event_name}\n💬 Вопросов: {feedbacks_count}\n\n"
            f"Пользователям отправлены запросы на оценку.",
            reply_markup=get_back_button("events_menu"))
        
        logger.info(f"Закрыто мероприятие {event_id}")


async def close_all_events_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    with get_session() as session:
        active_count = session.query(Event).filter_by(status=EventStatus.ACTIVE).count()
        
        if active_count == 0:
            await query.edit_message_text("ℹ️ Нет активных мероприятий.",
                                          reply_markup=get_back_button("events_menu"))
            return
        
        await query.edit_message_text(
            f"⚠️ <b>Закрыть все мероприятия?</b>\n\nАктивных мероприятий: {active_count}\n\n"
            f"Всем пользователям будет предложено оценить мероприятия.",
            parse_mode='HTML', reply_markup=get_confirm_keyboard("close_all"))


async def close_all_events_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    with get_session() as session:
        active_events = session.query(Event).filter_by(status=EventStatus.ACTIVE).all()
        count = len(active_events)
        events_data = []
        
        for event in active_events:
            event.status = EventStatus.CLOSED
            event.closed_at = datetime.utcnow()
            events_data.append({
                'id': event.id, 'name': event.name, 'topic_id': event.topic_id,
                'feedbacks_count': len(event.feedbacks),
                'user_ids': set(f.user_id for f in event.feedbacks)
            })
        session.commit()
        
        for event_data in events_data:
            if event_data['topic_id']:
                try:
                    await context.bot.send_message(
                        chat_id=Config.WORK_GROUP_ID,
                        message_thread_id=event_data['topic_id'],
                        text=f"🔒 Сбор вопросов завершен!\n\n📊 Всего вопросов: {event_data['feedbacks_count']}")
                except Exception as e:
                    logger.warning(f"Не удалось отправить уведомление в топик: {e}")
            
            await request_ratings_for_event(context, event_data['id'], event_data['name'], event_data['user_ids'])
        
        await query.edit_message_text(
            f"✅ Закрыто мероприятий: {count}\n\nПользователям отправлены запросы на оценку.",
            reply_markup=get_back_button("events_menu"))
        
        logger.info(f"Закрыто всех активных мероприятий: {count}")


async def request_ratings_for_event(context: ContextTypes.DEFAULT_TYPE, event_id: int,
                                    event_name: str, user_ids: set):
    from utils.keyboards import get_rating_keyboard
    
    with get_session() as session:
        for user_id in user_ids:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                continue
            
            existing_rating = session.query(Rating).filter_by(user_id=user_id, event_id=event_id).first()
            if existing_rating:
                continue
            
            try:
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"📊 Мероприятие \"{event_name}\" завершено!\n\nПожалуйста, оцените его:",
                    reply_markup=get_rating_keyboard(event_id))
            except Exception as e:
                logger.warning(f"Не удалось отправить запрос оценки пользователю {user.telegram_id}: {e}")


# ============ ПОЛЬЗОВАТЕЛИ ============

async def list_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    with get_session() as session:
        admins = session.query(User).filter_by(role=UserRole.ADMIN).all()
        managers = session.query(User).filter_by(role=UserRole.MANAGER).all()
        users = session.query(User).filter_by(role=UserRole.USER).limit(50).all()
        
        message = "👥 <b>Список пользователей:</b>\n\n👑 <b>Администраторы:</b>\n"
        if admins:
            for admin in admins:
                name = admin.full_name or admin.username or f"ID{admin.telegram_id}"
                username = f"@{admin.username}" if admin.username else ""
                message += f"  • {name} {username} (ID: <code>{admin.telegram_id}</code>)\n"
        else:
            message += "  Нет администраторов\n"
        
        message += "\n👔 <b>Менеджеры:</b>\n"
        if managers:
            for manager in managers:
                name = manager.full_name or manager.username or f"ID{manager.telegram_id}"
                username = f"@{manager.username}" if manager.username else ""
                message += f"  • {name} {username} (ID: <code>{manager.telegram_id}</code>)\n"
        else:
            message += "  Нет менеджеров\n"
        
        total_users = session.query(User).filter_by(role=UserRole.USER).count()
        message += f"\n👤 <b>Обычные пользователи:</b> {total_users} чел.\n"
        if users:
            for user in users[:10]:
                name = user.full_name or user.username or f"ID{user.telegram_id}"
                username = f"@{user.username}" if user.username else ""
                message += f"  • {name} {username}\n"
            if total_users > 10:
                message += f"  ... и еще {total_users - 10} пользователей\n"
        
        await query.edit_message_text(message, parse_mode='HTML', reply_markup=get_back_button("users_menu"))


async def add_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['adding_admin'] = True
    await query.edit_message_text(
        "👑 <b>Добавление администратора</b>\n\nВведите Telegram ID или username пользователя:\n\n"
        "<i>Например: @username или 123456789</i>\n\nОтмена: /cancel",
        parse_mode='HTML')


async def handle_add_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'adding_admin' not in context.user_data:
        return
    identifier = update.message.text.strip()
    context.user_data.pop('adding_admin', None)
    await add_admin_execute(update, context, identifier)


async def add_admin_execute(update: Update, context: ContextTypes.DEFAULT_TYPE, identifier: str):
    with get_session() as session:
        user = None
        
        if identifier.startswith('@'):
            username = identifier[1:]
            user = session.query(User).filter_by(username=username).first()
            if not user:
                await update.message.reply_text(
                    f"❌ Пользователь @{username} не найден.\n\nПользователь должен сначала написать боту /start",
                    reply_markup=get_back_button("users_menu"))
                return
        else:
            try:
                new_admin_id = int(identifier)
            except ValueError:
                await update.message.reply_text("❌ ID должен быть числом.",
                                                reply_markup=get_back_button("users_menu"))
                return
            
            user = session.query(User).filter_by(telegram_id=new_admin_id).first()
            if not user:
                user = User(telegram_id=new_admin_id, role=UserRole.ADMIN)
                session.add(user)
                session.flush()
        
        old_role = user.role.value
        user.role = UserRole.ADMIN
        user_telegram_id = user.telegram_id
        user_display = user.full_name or user.username or f"ID{user.telegram_id}"
        session.commit()
        
        await update.message.reply_text(
            f"✅ Пользователь {user_display} назначен администратором.\nПредыдущая роль: {old_role}\n\n"
            f"ℹ️ Администратор автоматически имеет все права менеджера.",
            reply_markup=get_back_button("users_menu"))
        
        try:
            await context.bot.send_message(
                chat_id=user_telegram_id,
                text="👑 Вам назначена роль администратора!\n\nТеперь у вас есть доступ ко всем командам управления.\n"
                     "Используйте /start для просмотра доступных функций.")
        except Exception as e:
            logger.warning(f"Не удалось уведомить админа: {e}")
        
        logger.info(f"Добавлен администратор: {user_telegram_id}")


async def add_manager_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['adding_manager'] = True
    await query.edit_message_text(
        "👔 <b>Добавление менеджера</b>\n\nВведите Telegram ID или username пользователя:\n\n"
        "<i>Например: @username или 123456789</i>\n\nОтмена: /cancel",
        parse_mode='HTML')


async def handle_add_manager_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'adding_manager' not in context.user_data:
        return
    identifier = update.message.text.strip()
    context.user_data.pop('adding_manager', None)
    await add_manager_execute(update, context, identifier)


async def add_manager_execute(update: Update, context: ContextTypes.DEFAULT_TYPE, identifier: str):
    with get_session() as session:
        user = None
        
        if identifier.startswith('@'):
            username = identifier[1:]
            user = session.query(User).filter_by(username=username).first()
            if not user:
                await update.message.reply_text(
                    f"❌ Пользователь @{username} не найден.\n\nПользователь должен сначала написать боту /start",
                    reply_markup=get_back_button("users_menu"))
                return
        else:
            try:
                new_manager_id = int(identifier)
            except ValueError:
                await update.message.reply_text("❌ ID должен быть числом.",
                                                reply_markup=get_back_button("users_menu"))
                return
            
            user = session.query(User).filter_by(telegram_id=new_manager_id).first()
            if not user:
                user = User(telegram_id=new_manager_id, role=UserRole.MANAGER)
                session.add(user)
                session.flush()
        
        if user.role == UserRole.ADMIN:
            user_display = user.full_name or user.username or f"ID{user.telegram_id}"
            await update.message.reply_text(
                f"⚠️ Пользователь {user_display} уже является администратором.\n\n"
                f"Администратор автоматически имеет все права менеджера.",
                reply_markup=get_back_button("users_menu"))
            return
        
        old_role = user.role.value
        user.role = UserRole.MANAGER
        user_telegram_id = user.telegram_id
        user_display = user.full_name or user.username or f"ID{user.telegram_id}"
        session.commit()
        
        await update.message.reply_text(
            f"✅ Пользователь {user_display} назначен менеджером.\nПредыдущая роль: {old_role}",
            reply_markup=get_back_button("users_menu"))
        
        try:
            await context.bot.send_message(
                chat_id=user_telegram_id,
                text="👔 Вам назначена роль менеджера!\n\nТеперь вы можете отвечать на вопросы пользователей "
                     "в рабочей группе.\n\nПросто отвечайте (Reply) на сообщения в топиках мероприятий.")
        except Exception as e:
            logger.warning(f"Не удалось уведомить менеджера: {e}")
        
        logger.info(f"Добавлен менеджер: {user_telegram_id}")


async def remove_role_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['removing_role'] = True
    await query.edit_message_text(
        "➖ <b>Снятие роли</b>\n\nВведите Telegram ID или username пользователя:\n\n"
        "<i>Например: @username или 123456789</i>\n\nОтмена: /cancel",
        parse_mode='HTML')


async def handle_remove_role_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'removing_role' not in context.user_data:
        return
    identifier = update.message.text.strip()
    context.user_data.pop('removing_role', None)
    await remove_role_execute(update, context, identifier)


async def remove_role_execute(update: Update, context: ContextTypes.DEFAULT_TYPE, identifier: str):
    with get_session() as session:
        user = None
        
        if identifier.startswith('@'):
            username = identifier[1:]
            user = session.query(User).filter_by(username=username).first()
        else:
            try:
                user_id = int(identifier)
                user = session.query(User).filter_by(telegram_id=user_id).first()
            except ValueError:
                await update.message.reply_text("❌ ID должен быть числом.",
                                                reply_markup=get_back_button("users_menu"))
                return
        
        if not user:
            await update.message.reply_text("❌ Пользователь не найден.",
                                            reply_markup=get_back_button("users_menu"))
            return
        
        if user.telegram_id == update.effective_user.id:
            await update.message.reply_text(
                "❌ Вы не можете снять роль с самого себя.\nПопросите другого администратора сделать это.",
                reply_markup=get_back_button("users_menu"))
            return
        
        old_role = user.role.value
        user.role = UserRole.USER
        user_telegram_id = user.telegram_id
        user_display = user.full_name or user.username or f"ID{user.telegram_id}"
        session.commit()
        
        await update.message.reply_text(
            f"✅ С пользователя {user_display} снята роль.\nПредыдущая роль: {old_role}\n"
            f"Текущая роль: обычный пользователь",
            reply_markup=get_back_button("users_menu"))
        
        try:
            await context.bot.send_message(
                chat_id=user_telegram_id,
                text=f"ℹ️ С вас снята роль {old_role}.\nТеперь у вас права обычного пользователя.")
        except Exception:
            pass
        
        logger.info(f"Снята роль с пользователя: {user_telegram_id}")


@admin_only
async def promote_from_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != Config.WORK_GROUP_ID:
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя, которого хотите назначить менеджером.")
        return
    
    target_user = update.message.reply_to_message.from_user
    if target_user.is_bot:
        await update.message.reply_text("❌ Нельзя назначить бота менеджером.")
        return
    
    with get_session() as session:
        user = session.query(User).filter_by(telegram_id=target_user.id).first()
        
        if not user:
            user = User(telegram_id=target_user.id, username=target_user.username,
                       full_name=target_user.full_name, role=UserRole.MANAGER)
            session.add(user)
        else:
            if user.role == UserRole.MANAGER:
                await update.message.reply_text(f"ℹ️ {user.full_name or user.username} уже является менеджером.")
                return
            if user.role == UserRole.ADMIN:
                await update.message.reply_text(
                    f"ℹ️ {user.full_name or user.username} является администратором.\n"
                    f"Администратор автоматически имеет все права менеджера.")
                return
            user.role = UserRole.MANAGER
        
        user_telegram_id = user.telegram_id
        user_display = user.full_name or user.username or f"ID{user.telegram_id}"
        session.commit()
        
        await update.message.reply_text(f"✅ {user_display} назначен менеджером!")
        
        try:
            await context.bot.send_message(
                chat_id=user_telegram_id,
                text="👔 Вам назначена роль менеджера!\n\nТеперь вы можете отвечать на вопросы пользователей в рабочей группе.")
        except Exception:
            pass
        
        logger.info(f"Менеджер назначен через группу: {user_telegram_id}")


# ============ СТАТИСТИКА ============

async def show_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    from services.analytics import get_general_stats
    
    with get_session() as session:
        stats = get_general_stats(session)
        
        message = "📊 <b>Общая статистика:</b>\n\n"
        message += f"📅 Всего мероприятий: {stats['total_events']}\n"
        message += f"✅ Активных: {stats['active_events']}\n"
        message += f"🔒 Завершенных: {stats['closed_events']}\n\n"
        message += f"💬 Всего вопросов: {stats['total_feedbacks']}\n"
        message += f"⭐ Всего оценок: {stats['total_ratings']}\n"
        message += f"📊 Средняя оценка: {stats['avg_rating']}\n\n"
        message += f"👥 Всего пользователей: {stats['total_users']}\n"
        message += f"👔 Менеджеров: {stats['total_managers']}\n"
        message += f"👑 Администраторов: {stats['total_admins']}\n\n"
        
        if stats['top_events']:
            message += "🏆 <b>Топ-3 мероприятия по оценкам:</b>\n"
            for i, event in enumerate(stats['top_events'], 1):
                message += f"{i}. {event['name']} — {event['avg_rating']}⭐ ({event['count']} оценок)\n"
        
        await query.edit_message_text(message, parse_mode='HTML', reply_markup=get_back_button("stats_menu"))


async def export_report_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("⏳ Генерирую общий отчет, пожалуйста подождите...")
    
    try:
        from services.pdf_report import generate_pdf_report
        
        with get_session() as session:
            pdf_path = generate_pdf_report(session, event_id=None)
            
            with open(pdf_path, 'rb') as pdf_file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=pdf_file,
                    filename=f"report_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    caption="📊 Общий отчет по всем мероприятиям")
            
            try:
                os.remove(pdf_path)
            except Exception:
                pass
            
            await query.edit_message_text("✅ Отчет сгенерирован!", reply_markup=get_back_button("stats_menu"))
            logger.info(f"Общий отчет успешно сгенерирован")
    
    except Exception as e:
        logger.error(f"Ошибка генерации отчета: {e}")
        await query.edit_message_text(f"❌ Ошибка генерации отчета: {str(e)}",
                                      reply_markup=get_back_button("stats_menu"))


async def export_report_select_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    with get_session() as session:
        events = session.query(Event).filter_by(status=EventStatus.CLOSED).all()
        
        if not events:
            await query.edit_message_text("ℹ️ Нет завершенных мероприятий для отчета.",
                                          reply_markup=get_back_button("stats_menu"))
            return
        
        await query.edit_message_text("📄 Выберите мероприятие для отчета:",
                                      reply_markup=get_events_for_report_keyboard(events))


async def export_report_event(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id: int):
    query = update.callback_query
    
    with get_session() as session:
        event = session.query(Event).filter_by(id=event_id).first()
        if not event:
            await query.edit_message_text("❌ Мероприятие не найдено.",
                                          reply_markup=get_back_button("stats_menu"))
            return
        event_name = event.name
    
    await query.edit_message_text(f"⏳ Генерирую отчет по мероприятию \"{event_name}\"...")
    
    try:
        from services.pdf_report import generate_pdf_report
        
        with get_session() as session:
            pdf_path = generate_pdf_report(session, event_id=event_id)
            
            with open(pdf_path, 'rb') as pdf_file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=pdf_file,
                    filename=f"report_{event_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    caption=f"📊 Отчет по мероприятию: {event_name}")
            
            try:
                os.remove(pdf_path)
            except Exception:
                pass
            
            await query.edit_message_text("✅ Отчет сгенерирован!", reply_markup=get_back_button("stats_menu"))
            logger.info(f"Отчет по мероприятию {event_id} успешно сгенерирован")
    
    except Exception as e:
        logger.error(f"Ошибка генерации отчета: {e}")
        await query.edit_message_text(f"❌ Ошибка генерации отчета: {str(e)}",
                                      reply_markup=get_back_button("stats_menu"))


# ============ НАСТРОЙКИ ============

async def view_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    from utils.settings import get_setting, DEFAULT_NO_EVENTS_MESSAGE
    
    no_events_msg = get_setting('no_events_message', DEFAULT_NO_EVENTS_MESSAGE)
    
    message = "⚙️ <b>Настройки бота:</b>\n\n"
    message += "<b>1. Сообщение при отсутствии мероприятий:</b>\n"
    message += f"{no_events_msg}\n\n"
    
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=get_back_button("settings_menu"))


async def edit_no_events_message_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    from utils.settings import get_setting, DEFAULT_NO_EVENTS_MESSAGE
    
    current_msg = get_setting('no_events_message', DEFAULT_NO_EVENTS_MESSAGE)
    context.user_data['editing_no_events_msg'] = True
    
    await query.edit_message_text(
        f"📝 <b>Текущее сообщение при отсутствии мероприятий:</b>\n\n{current_msg}\n\n"
        f"<b>Введите новый текст сообщения:</b>\n\nОтмена: /cancel",
        parse_mode='HTML')


async def handle_no_events_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'editing_no_events_msg' not in context.user_data:
        return
    
    new_message = update.message.text.strip()
    context.user_data.pop('editing_no_events_msg', None)
    
    from utils.settings import set_setting
    with get_session() as session:
        telegram_id = update.effective_user.id
        admin_user = session.query(User).filter_by(telegram_id=telegram_id).first()
        set_setting('no_events_message', new_message, admin_user.id if admin_user else None)
    
    await update.message.reply_text(
        f"✅ Сообщение обновлено!\n\n<b>Новое сообщение:</b>\n{new_message}",
        parse_mode='HTML', reply_markup=get_back_button("settings_menu"))
    
    logger.info(f"Обновлено сообщение no_events_message администратором {update.effective_user.id}")
