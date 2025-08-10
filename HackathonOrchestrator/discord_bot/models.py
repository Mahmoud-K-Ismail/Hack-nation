"""
Database models for Discord bot service
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Float, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()


class BotConfig(Base):
    """Configuration for a Discord bot instance per hackathon"""
    __tablename__ = "bot_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(String(255), unique=True, nullable=False, index=True)
    discord_guild_id = Column(String(20), nullable=False)
    installation_id = Column(String(255), nullable=False)
    config_json = Column(JSON, nullable=False)
    status = Column(String(20), default="active")  # active, disabled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    events = relationship("BotEvent", back_populates="bot_config", cascade="all, delete-orphan")
    faq_embeddings = relationship("FAQEmbedding", back_populates="bot_config", cascade="all, delete-orphan")


class BotEvent(Base):
    """Events and webhook deliveries from the bot"""
    __tablename__ = "bot_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_config_id = Column(UUID(as_uuid=True), ForeignKey("bot_configs.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # issue_escalation, faq_autoreply_triggered, etc.
    payload = Column(JSON, nullable=False)
    delivered = Column(Boolean, default=False)
    delivery_attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)
    
    # Relationships
    bot_config = relationship("BotConfig", back_populates="events")


class FAQEmbedding(Base):
    """FAQ embeddings for semantic search"""
    __tablename__ = "faq_embeddings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_config_id = Column(UUID(as_uuid=True), ForeignKey("bot_configs.id"), nullable=False)
    hackathon_id = Column(String(255), nullable=False, index=True)
    faq_id = Column(String(255), nullable=True)  # Reference to platform FAQ ID
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    embedding = Column(ARRAY(Float), nullable=True)  # Vector embedding
    similarity_threshold = Column(Float, default=0.78)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bot_config = relationship("BotConfig", back_populates="faq_embeddings")


class MessageContext(Base):
    """Short-term message context for flood detection and conversation tracking"""
    __tablename__ = "message_contexts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id = Column(String(20), nullable=False, index=True)
    channel_id = Column(String(20), nullable=False, index=True)
    user_id = Column(String(20), nullable=False)
    message_id = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sentiment_score = Column(Float, nullable=True)  # -1.0 to 1.0
    urgency_score = Column(Float, nullable=True)    # 0.0 to 1.0
    category = Column(String(50), nullable=True)    # faq, complaint, social, spam, unknown
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # TTL: Keep only last 24 hours of messages
    # Note: Partitioning would be set up separately in production


class FloodDetection(Base):
    """Flood detection tracking for channels"""
    __tablename__ = "flood_detections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id = Column(String(20), nullable=False)
    channel_id = Column(String(20), nullable=False)
    question_hash = Column(String(64), nullable=False)  # Hash of similar questions
    message_count = Column(Integer, default=1)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    responded = Column(Boolean, default=False)
    pinned_message_id = Column(String(20), nullable=True)
    
    __table_args__ = (
        UniqueConstraint('guild_id', 'channel_id', 'question_hash'),
    )


class ScheduledAnnouncement(Base):
    """Scheduled announcements from platform"""
    __tablename__ = "scheduled_announcements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hackathon_id = Column(String(255), nullable=False)
    event_id = Column(String(255), nullable=False)  # Platform event ID
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    scheduled_time = Column(DateTime, nullable=False)
    lead_minutes = Column(Integer, nullable=False)  # How many minutes before event
    channel_id = Column(String(20), nullable=True)  # Target Discord channel
    sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
