from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database.models import Event, Feedback, Rating, User, UserRole, EventStatus, FeedbackStatus
from datetime import datetime, timedelta
from collections import Counter
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def get_general_stats(session: Session) -> dict:
    """Получить общую статистику по всем мероприятиям"""
    
    total_events = session.query(Event).count()
    active_events = session.query(Event).filter_by(status=EventStatus.ACTIVE).count()
    closed_events = session.query(Event).filter_by(status=EventStatus.CLOSED).count()
    
    total_feedbacks = session.query(Feedback).count()
    total_ratings = session.query(Rating).count()
    
    avg_rating_result = session.query(func.avg(Rating.rating)).scalar()
    avg_rating = f"{avg_rating_result:.2f}⭐" if avg_rating_result else "—"
    
    total_users = session.query(User).count()
    total_managers = session.query(User).filter_by(role=UserRole.MANAGER).count()
    total_admins = session.query(User).filter_by(role=UserRole.ADMIN).count()
    
    # Топ мероприятий по оценкам
    top_events_query = (
        session.query(
            Event.id,
            Event.name,
            func.avg(Rating.rating).label('avg_rating'),
            func.count(Rating.id).label('rating_count')
        )
        .join(Rating, Event.id == Rating.event_id)
        .group_by(Event.id, Event.name)
        .having(func.count(Rating.id) >= 3)  # Минимум 3 оценки
        .order_by(desc('avg_rating'))
        .limit(3)
        .all()
    )
    
    top_events = [
        {
            'name': event.name,
            'avg_rating': f"{event.avg_rating:.2f}",
            'count': event.rating_count
        }
        for event in top_events_query
    ]
    
    return {
        'total_events': total_events,
        'active_events': active_events,
        'closed_events': closed_events,
        'total_feedbacks': total_feedbacks,
        'total_ratings': total_ratings,
        'avg_rating': avg_rating,
        'total_users': total_users,
        'total_managers': total_managers,
        'total_admins': total_admins,
        'top_events': top_events
    }

def get_event_stats(session: Session, event_id: int) -> dict:
    """Получить детальную статистику по конкретному мероприятию"""
    
    event = session.query(Event).filter_by(id=event_id).first()
    if not event:
        return None
    
    # Основные метрики
    total_feedbacks = len(event.feedbacks)
    total_ratings = len(event.ratings)
    
    # Статистика по статусам обратной связи
    feedback_statuses = Counter(f.status for f in event.feedbacks)
    
    # Средняя оценка и распределение
    ratings_values = [r.rating for r in event.ratings]
    avg_rating = sum(ratings_values) / len(ratings_values) if ratings_values else 0
    rating_distribution = Counter(ratings_values)
    
    # Время ответа менеджеров (среднее)
    response_times = []
    for feedback in event.feedbacks:
        if feedback.answered_at and feedback.created_at:
            delta = feedback.answered_at - feedback.created_at
            response_times.append(delta.total_seconds() / 3600)  # в часах
    
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    # Топ менеджеров по количеству ответов
    manager_stats = (
        session.query(
            User.full_name,
            User.username,
            func.count(Feedback.id).label('answers_count')
        )
        .join(Feedback, User.id == Feedback.answered_by)
        .filter(Feedback.event_id == event_id)
        .group_by(User.id, User.full_name, User.username)
        .order_by(desc('answers_count'))
        .all()
    )
    
    top_managers = [
        {
            'name': m.full_name or m.username or 'Неизвестный',
            'count': m.answers_count
        }
        for m in manager_stats
    ]
    
    # Комментарии с оценками
    comments = [
        {
            'rating': r.rating,
            'comment': r.comment,
            'date': r.created_at
        }
        for r in event.ratings if r.comment
    ]
    
    # Динамика по дням
    feedbacks_by_day = {}
    for feedback in event.feedbacks:
        day = feedback.created_at.date()
        feedbacks_by_day[day] = feedbacks_by_day.get(day, 0) + 1
    
    return {
        'event': event,
        'total_feedbacks': total_feedbacks,
        'total_ratings': total_ratings,
        'avg_rating': avg_rating,
        'rating_distribution': dict(rating_distribution),
        'feedback_statuses': {status.value: count for status, count in feedback_statuses.items()},
        'avg_response_time_hours': avg_response_time,
        'top_managers': top_managers,
        'comments': comments,
        'feedbacks_by_day': feedbacks_by_day
    }

def get_all_events_stats(session: Session) -> list:
    """Получить статистику по всем мероприятиям"""
    
    events = session.query(Event).order_by(Event.created_at.desc()).all()
    
    stats = []
    for event in events:
        event_stat = get_event_stats(session, event.id)
        if event_stat:
            stats.append(event_stat)
    
    return stats

def get_user_activity_stats(session: Session, days: int = 30) -> dict:
    """Статистика активности пользователей за последние N дней"""
    
    since_date = datetime.utcnow() - timedelta(days=days)
    
    # Активные пользователи (оставившие feedback или оценку)
    active_users_feedback = (
        session.query(func.count(func.distinct(Feedback.user_id)))
        .filter(Feedback.created_at >= since_date)
        .scalar()
    )
    
    active_users_rating = (
        session.query(func.count(func.distinct(Rating.user_id)))
        .filter(Rating.created_at >= since_date)
        .scalar()
    )
    
    # Новые пользователи
    new_users = (
        session.query(func.count(User.id))
        .filter(User.created_at >= since_date)
        .scalar()
    )
    
    # Активность менеджеров
    manager_activity = (
        session.query(
            User.full_name,
            User.username,
            func.count(Feedback.id).label('responses')
        )
        .join(Feedback, User.id == Feedback.answered_by)
        .filter(
            Feedback.answered_at >= since_date,
            User.role.in_([UserRole.MANAGER, UserRole.ADMIN])
        )
        .group_by(User.id, User.full_name, User.username)
        .order_by(desc('responses'))
        .all()
    )
    
    return {
        'days': days,
        'active_users_feedback': active_users_feedback,
        'active_users_rating': active_users_rating,
        'new_users': new_users,
        'manager_activity': [
            {
                'name': m.full_name or m.username or 'Неизвестный',
                'responses': m.responses
            }
            for m in manager_activity
        ]
    }

def prepare_dataframe_for_export(session: Session, event_id: int = None) -> pd.DataFrame:
    """Подготовить DataFrame для экспорта"""
    
    if event_id:
        feedbacks = session.query(Feedback).filter_by(event_id=event_id).all()
    else:
        feedbacks = session.query(Feedback).all()
    
    data = []
    for f in feedbacks:
        data.append({
            'ID': f.id,
            'Мероприятие': f.event.name,
            'Пользователь': f.user.full_name or f.user.username or f'ID{f.user.telegram_id}',
            'Сообщение': f.message_text,
            'Статус': f.status.value,
            'Дата создания': f.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'Дата ответа': f.answered_at.strftime('%Y-%m-%d %H:%M:%S') if f.answered_at else '—',
            'Менеджер': f.manager.full_name if f.manager else '—'
        })
    
    return pd.DataFrame(data)

def get_word_frequency(session: Session, event_id: int = None, top_n: int = 50) -> Counter:
    """Получить частоту слов из отзывов (для облака слов)"""
    
    if event_id:
        feedbacks = session.query(Feedback).filter_by(event_id=event_id).all()
    else:
        feedbacks = session.query(Feedback).all()
    
    # Объединяем все тексты
    all_text = ' '.join([f.message_text for f in feedbacks])
    
    # Простая токенизация (можно улучшить с помощью NLTK или spaCy)
    words = all_text.lower().split()
    
    # Фильтруем стоп-слова (базовый список)
    stop_words = {
        'в', 'на', 'и', 'с', 'по', 'для', 'не', 'от', 'за', 'к', 'до', 'из', 'у', 'о',
        'что', 'это', 'как', 'так', 'но', 'а', 'то', 'все', 'она', 'он', 'они', 'мы',
        'вы', 'я', 'был', 'была', 'было', 'были', 'есть', 'быть', 'был', 'будет'
    }
    
    filtered_words = [w for w in words if len(w) > 3 and w not in stop_words]
    
    return Counter(filtered_words).most_common(top_n)

def calculate_nps(ratings: list) -> dict:
    """Рассчитать Net Promoter Score на основе оценок"""
    
    if not ratings:
        return {'nps': 0, 'promoters': 0, 'passives': 0, 'detractors': 0}
    
    # Переводим оценки 1-5 в систему NPS (0-10)
    # 5 звезд = 9-10 (промоутеры)
    # 4 звезды = 7-8 (пассивные)
    # 1-3 звезды = 0-6 (детракторы)
    
    promoters = sum(1 for r in ratings if r >= 5)
    passives = sum(1 for r in ratings if r == 4)
    detractors = sum(1 for r in ratings if r <= 3)
    
    total = len(ratings)
    
    nps = ((promoters - detractors) / total) * 100 if total > 0 else 0
    
    return {
        'nps': round(nps, 1),
        'promoters': promoters,
        'passives': passives,
        'detractors': detractors,
        'promoters_pct': round((promoters / total) * 100, 1) if total > 0 else 0,
        'passives_pct': round((passives / total) * 100, 1) if total > 0 else 0,
        'detractors_pct': round((detractors / total) * 100, 1) if total > 0 else 0
    }
