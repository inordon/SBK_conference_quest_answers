from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from database.models import Event, EventStatus

# ============ ГЛАВНЫЕ МЕНЮ ============

def get_admin_main_menu():
    """Главное меню администратора"""
    keyboard = [
        [KeyboardButton("📅 Мероприятия"), KeyboardButton("👥 Пользователи")],
        [KeyboardButton("📊 Статистика"), KeyboardButton("⚙️ Настройки")],
        [KeyboardButton("❓ Задать вопрос"), KeyboardButton("⭐ Оценить")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_manager_main_menu():
    """Главное меню менеджера"""
    keyboard = [
        [KeyboardButton("❓ Задать вопрос"), KeyboardButton("⭐ Оценить")],
        [KeyboardButton("📋 Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_user_main_menu():
    """Главное меню пользователя"""
    keyboard = [
        [KeyboardButton("❓ Задать вопрос")],
        [KeyboardButton("⭐ Оценить мероприятие")],
        [KeyboardButton("ℹ️ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ============ МЕНЮ МЕРОПРИЯТИЙ ============

def get_events_management_menu():
    """Меню управления мероприятиями"""
    keyboard = [
        [InlineKeyboardButton("➕ Создать мероприятие", callback_data="events_create")],
        [InlineKeyboardButton("📋 Список мероприятий", callback_data="events_list")],
        [InlineKeyboardButton("🔒 Закрыть мероприятие", callback_data="events_close")],
        [InlineKeyboardButton("🔒 Закрыть все", callback_data="events_close_all")],
        [InlineKeyboardButton("↩️ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_users_management_menu():
    """Меню управления пользователями"""
    keyboard = [
        [InlineKeyboardButton("📋 Список пользователей", callback_data="users_list")],
        [InlineKeyboardButton("➕ Добавить админа", callback_data="users_add_admin")],
        [InlineKeyboardButton("➕ Добавить менеджера", callback_data="users_add_manager")],
        [InlineKeyboardButton("➖ Снять роль", callback_data="users_remove_role")],
        [InlineKeyboardButton("↩️ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_stats_menu():
    """Меню статистики"""
    keyboard = [
        [InlineKeyboardButton("📊 Общая статистика", callback_data="stats_general")],
        [InlineKeyboardButton("📄 Экспорт PDF (все)", callback_data="stats_export_all")],
        [InlineKeyboardButton("📄 Экспорт по мероприятию", callback_data="stats_export_event")],
        [InlineKeyboardButton("↩️ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_menu():
    """Меню настроек"""
    keyboard = [
        [InlineKeyboardButton("📝 Сообщение \"Нет мероприятий\"", callback_data="settings_no_events")],
        [InlineKeyboardButton("👁 Просмотр всех настроек", callback_data="settings_view")],
        [InlineKeyboardButton("↩️ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ ВЫБОР МЕРОПРИЯТИЙ ============

def get_events_keyboard(events: list) -> InlineKeyboardMarkup:
    """Клавиатура для выбора мероприятия (для вопросов)"""
    keyboard = []
    for event in events:
        keyboard.append([
            InlineKeyboardButton(
                f"📅 {event.name}", 
                callback_data=f"event_{event.id}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)

def get_events_to_close_keyboard(events: list) -> InlineKeyboardMarkup:
    """Клавиатура для выбора мероприятия для закрытия"""
    keyboard = []
    for event in events:
        keyboard.append([
            InlineKeyboardButton(
                f"🔒 {event.name}", 
                callback_data=f"close_event_{event.id}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="events_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_events_for_report_keyboard(events: list) -> InlineKeyboardMarkup:
    """Клавиатура для выбора мероприятия для отчета"""
    keyboard = []
    for event in events:
        keyboard.append([
            InlineKeyboardButton(
                f"📄 {event.name}", 
                callback_data=f"report_event_{event.id}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="stats_menu")])
    return InlineKeyboardMarkup(keyboard)

# ============ ОЦЕНКИ ============

def get_rating_keyboard(event_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для оценки мероприятия"""
    keyboard = []
    stars = ["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]
    for i, star in enumerate(stars, 1):
        keyboard.append([
            InlineKeyboardButton(
                star, 
                callback_data=f"rate_{event_id}_{i}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)

def get_events_to_rate_keyboard(events: list) -> InlineKeyboardMarkup:
    """Клавиатура для выбора мероприятия для оценки"""
    keyboard = []
    for event in events:
        keyboard.append([
            InlineKeyboardButton(
                f"⭐ {event.name}", 
                callback_data=f"rate_select_{event.id}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)

# ============ ПОДТВЕРЖДЕНИЯ ============

def get_confirm_keyboard(action: str, item_id: int = None) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    if item_id:
        callback_yes = f"confirm_{action}_{item_id}"
        callback_no = f"cancel_{action}_{item_id}"
    else:
        callback_yes = f"confirm_{action}"
        callback_no = f"cancel_{action}"
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data=callback_yes),
            InlineKeyboardButton("❌ Нет", callback_data=callback_no)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_button(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
    """Кнопка назад"""
    keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)
