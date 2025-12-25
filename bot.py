import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import Config
from database.db import init_db, get_session
from database.models import User, UserRole
from handlers import admin, manager, user, rating
from utils.keyboards import get_admin_main_menu, get_manager_main_menu, get_user_main_menu

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL),
    handlers=[
        logging.FileHandler('/app/logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def start(update, context):
    """Обработчик команды /start"""
    telegram_id = update.effective_user.id
    chat_type = update.effective_chat.type
    
    with get_session() as session:
        db_user = session.query(User).filter_by(telegram_id=telegram_id).first()
        
        if not db_user:
            db_user = User(
                telegram_id=telegram_id,
                username=update.effective_user.username,
                full_name=update.effective_user.full_name,
                role=UserRole.ADMIN if telegram_id == Config.INITIAL_ADMIN_ID else UserRole.USER
            )
            session.add(db_user)
            session.commit()
        
        if chat_type != 'private':
            return
        
        if db_user.role == UserRole.ADMIN:
            await update.message.reply_text(
                "👋 Добро пожаловать, администратор!\n\n"
                "Используйте меню ниже для управления системой:",
                reply_markup=get_admin_main_menu()
            )
        elif db_user.role == UserRole.MANAGER:
            await update.message.reply_text(
                "👋 Добро пожаловать, менеджер!\n\n"
                "Вы можете задавать вопросы и отвечать пользователям в рабочей группе.",
                reply_markup=get_manager_main_menu()
            )
        else:
            await update.message.reply_text(
                "👋 Добро пожаловать!\n\n"
                "Здесь вы можете задавать вопросы во время мероприятий "
                "и оценивать завершенные события.",
                reply_markup=get_user_main_menu()
            )

async def help_command(update, context):
    """Обработчик команды /help"""
    telegram_id = update.effective_user.id
    
    with get_session() as session:
        db_user = session.query(User).filter_by(telegram_id=telegram_id).first()
        
        if not db_user:
            await update.message.reply_text("Используйте /start для начала работы")
            return
        
        if db_user.role == UserRole.ADMIN:
            help_text = (
                "📖 <b>Справка для администратора</b>\n\n"
                "Используйте кнопки меню для управления:\n\n"
                "📅 <b>Мероприятия</b> - создание и управление\n"
                "👥 <b>Пользователи</b> - назначение ролей\n"
                "📊 <b>Статистика</b> - отчеты и аналитика\n"
                "⚙️ <b>Настройки</b> - настройки бота\n\n"
                "❓ <b>Задать вопрос</b> - вопрос во время мероприятия\n"
                "⭐ <b>Оценить</b> - оценить завершенное мероприятие\n\n"
                "<i>💡 Администратор автоматически имеет права менеджера</i>"
            )
        elif db_user.role == UserRole.MANAGER:
            help_text = (
                "📖 <b>Справка для менеджера</b>\n\n"
                "❓ <b>Задать вопрос</b> - задать вопрос во время мероприятия\n"
                "⭐ <b>Оценить</b> - оценить завершенное мероприятие\n\n"
                "В рабочей группе отвечайте на вопросы пользователей через Reply."
            )
        else:
            help_text = (
                "📖 <b>Справка</b>\n\n"
                "❓ <b>Задать вопрос</b> - задать вопрос во время активного мероприятия\n"
                "⭐ <b>Оценить мероприятие</b> - оценить завершенное мероприятие\n\n"
                "Просто выбирайте кнопки и следуйте инструкциям бота!"
            )
        
        await update.message.reply_text(help_text, parse_mode='HTML')

async def handle_private_message(update: Update, context):
    """Обработка текстовых сообщений в личке"""
    text = update.message.text
    
    if 'creating_event' in context.user_data:
        await admin.handle_event_name_input(update, context)
        return
    
    if 'adding_admin' in context.user_data:
        await admin.handle_add_admin_input(update, context)
        return
    
    if 'adding_manager' in context.user_data:
        await admin.handle_add_manager_input(update, context)
        return
    
    if 'removing_role' in context.user_data:
        await admin.handle_remove_role_input(update, context)
        return
    
    if 'editing_no_events_msg' in context.user_data:
        await admin.handle_no_events_message_input(update, context)
        return
    
    if 'pending_rating_id' in context.user_data:
        await rating.handle_rating_comment(update, context)
        return
    
    if 'selected_event_id' in context.user_data:
        await user.handle_question_text(update, context)
        return
    
    telegram_id = update.effective_user.id
    
    with get_session() as session:
        db_user = session.query(User).filter_by(telegram_id=telegram_id).first()
        
        if not db_user:
            await update.message.reply_text("Используйте /start для начала работы")
            return
        
        if text == "❓ Задать вопрос":
            await user.start_question(update, context)
        
        elif text == "⭐ Оценить мероприятие" or text == "⭐ Оценить":
            await rating.start_rating(update, context)
        
        elif text == "ℹ️ Помощь" or text == "📋 Помощь":
            await help_command(update, context)
        
        elif db_user.role == UserRole.ADMIN:
            if text == "📅 Мероприятия":
                await admin.show_events_menu(update, context)
            
            elif text == "👥 Пользователи":
                await admin.show_users_menu(update, context)
            
            elif text == "📊 Статистика":
                await admin.show_stats_menu(update, context)
            
            elif text == "⚙️ Настройки":
                await admin.show_settings_menu(update, context)
            
            else:
                await update.message.reply_text(
                    "Используйте кнопки меню для навигации или /start для начала."
                )
        else:
            await update.message.reply_text(
                "Используйте кнопки меню для навигации или /start для начала."
            )

def main():
    """Запуск бота"""
    try:
        Config.validate()
        logger.info("Конфигурация валидна")
        
        init_db()
        logger.info("База данных инициализирована")
        
        application = Application.builder().token(Config.BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        
        application.add_handler(CallbackQueryHandler(admin.handle_admin_callbacks))
        
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
            handle_private_message
        ))
        
        application.add_handler(MessageHandler(
            filters.PHOTO & filters.ChatType.PRIVATE, 
            user.handle_question_photo
        ))
        
        application.add_handler(MessageHandler(
            filters.ChatType.SUPERGROUP & filters.REPLY, 
            manager.handle_manager_reply
        ))
        
        application.add_handler(CommandHandler("promote", admin.promote_from_group))
        
        logger.info("✅ Бот успешно запущен")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске бота: {e}")
        raise

if __name__ == '__main__':
    main()
