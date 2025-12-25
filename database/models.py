from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text, Enum, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum

Base = declarative_base()

class UserRole(enum.Enum):
    USER = "user"
    MANAGER = "manager"
    ADMIN = "admin"

class EventStatus(enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"

class FeedbackStatus(enum.Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    ANSWERED = "answered"
    CLOSED = "closed"

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255))
    full_name = Column(String(255))
    role = Column(Enum(UserRole), default=UserRole.USER)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    feedbacks = relationship("Feedback", foreign_keys="Feedback.user_id", back_populates="user")
    ratings = relationship("Rating", back_populates="user")
    answered_feedbacks = relationship("Feedback", foreign_keys="Feedback.answered_by", back_populates="manager")

class Event(Base):
    __tablename__ = 'events'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False)
    description = Column(Text)
    topic_id = Column(Integer)
    status = Column(Enum(EventStatus), default=EventStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    feedbacks = relationship("Feedback", back_populates="event")
    ratings = relationship("Rating", back_populates="event")

class Feedback(Base):
    __tablename__ = 'feedbacks'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    message_text = Column(Text, nullable=False)
    photo_file_id = Column(String(255))
    status = Column(Enum(FeedbackStatus), default=FeedbackStatus.NEW)
    topic_message_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    answered_at = Column(DateTime)
    answered_by = Column(Integer, ForeignKey('users.id'))
    
    user = relationship("User", foreign_keys=[user_id], back_populates="feedbacks")
    event = relationship("Event", back_populates="feedbacks")
    manager = relationship("User", foreign_keys=[answered_by], back_populates="answered_feedbacks")

class Rating(Base):
    __tablename__ = 'ratings'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="ratings")
    event = relationship("Event", back_populates="ratings")

class BotSetting(Base):
    __tablename__ = 'bot_settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey('users.id'))
