"""
Pydantic schemas for Discord bot API
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, validator
import re


class DiscordConfig(BaseModel):
    guild_id: str = Field(..., description="Discord server ID where bot is installed")
    installation_id: str = Field(..., description="Internal installation ID from OAuth")
    default_organizer_role_id: Optional[str] = Field(None, description="Role ID to consider as organizer")


class Features(BaseModel):
    faq_autoreply: bool = Field(True, description="Enable automatic FAQ replies")
    flood_detection: bool = Field(True, description="Enable flood detection and summarization")
    escalation: bool = Field(True, description="Enable issue escalation to organizers")
    scheduled_announcements: bool = Field(True, description="Enable scheduled announcements")
    thread_autocreate: bool = Field(True, description="Auto-create threads for high-traffic questions")
    sentiment_detection: bool = Field(True, description="Enable sentiment analysis")
    pin_auto_answers: bool = Field(True, description="Auto-pin important bot answers")


class EscalationConfig(BaseModel):
    enabled: bool = Field(True, description="Enable escalation system")
    channel_id: str = Field(..., description="Discord channel ID for alerts")
    escalation_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Severity threshold for escalation")
    notify_roles: List[str] = Field(default=[], description="Discord role IDs to mention for alerts")


class FAQConfig(BaseModel):
    source: Literal["platform", "google_sheets", "manual"] = Field("platform", description="Source of FAQ data")
    url: Optional[str] = Field(None, description="URL for external FAQ source")
    auto_sync: bool = Field(True, description="Auto-sync FAQ from source")
    sync_interval_minutes: int = Field(15, ge=1, description="Sync interval in minutes")


class ScheduleConfig(BaseModel):
    source: Literal["platform", "google_calendar", "manual"] = Field("platform", description="Source of schedule data")
    timezone: str = Field("UTC", description="Timezone for announcements")
    reminder_lead_minutes: List[int] = Field([10, 60, 1440], description="Lead times for reminders")
    
    @validator('reminder_lead_minutes')
    def validate_lead_minutes(cls, v):
        if not all(isinstance(x, int) and x >= 1 for x in v):
            raise ValueError('All reminder lead minutes must be positive integers')
        return v


class EmbeddingsConfig(BaseModel):
    vector_store: Literal["pgvector", "pinecone", "weaviate"] = Field("pgvector", description="Vector store type")
    similarity_threshold: float = Field(0.78, ge=0.0, le=1.0, description="Similarity threshold for FAQ matching")


class PersonalityConfig(BaseModel):
    tone: Literal["casual", "formal", "fun", "custom"] = Field("casual", description="Bot personality tone")
    welcome_message: Optional[str] = Field(None, description="Custom welcome message")


class LoggingConfig(BaseModel):
    send_to_platform_webhook: bool = Field(True, description="Send events to platform webhook")
    platform_webhook_url: str = Field(..., description="Platform webhook URL (must be HTTPS)")
    
    @validator('platform_webhook_url')
    def validate_webhook_url(cls, v):
        if v and not v.startswith('https://'):
            raise ValueError('Webhook URL must be HTTPS')
        return v


class BotConfigurationRequest(BaseModel):
    hackathon_id: str = Field(..., description="Unique platform hackathon ID")
    discord: DiscordConfig
    features: Features = Field(default=Features(), description="Feature toggles")
    escalation: EscalationConfig
    faq: FAQConfig = Field(default=FAQConfig(), description="FAQ configuration")
    schedule: ScheduleConfig = Field(default=ScheduleConfig(), description="Schedule configuration")
    embeddings: EmbeddingsConfig = Field(default=EmbeddingsConfig(), description="Embeddings configuration")
    personality: PersonalityConfig = Field(default=PersonalityConfig(), description="Bot personality")
    logging: LoggingConfig


class BotConfigurationResponse(BaseModel):
    status: str = Field("ok", description="Response status")
    hackathon_id: str
    config_id: str
    message: str = Field("Configuration created/updated.", description="Response message")
    applied_at: datetime


class BotConfigurationUpdate(BaseModel):
    """Partial update model for PATCH requests"""
    features: Optional[Features] = None
    escalation: Optional[EscalationConfig] = None
    faq: Optional[FAQConfig] = None
    schedule: Optional[ScheduleConfig] = None
    embeddings: Optional[EmbeddingsConfig] = None
    personality: Optional[PersonalityConfig] = None
    logging: Optional[LoggingConfig] = None


class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None
    errors: Optional[List[str]] = None


# Webhook event schemas
class IssueEscalationEvent(BaseModel):
    event: Literal["issue_escalation"] = "issue_escalation"
    hackathon_id: str
    guild_id: str
    channel_id: str
    summary: str
    severity: float = Field(ge=0.0, le=1.0)
    messages: List[Dict[str, Any]]
    discord_jump_links: List[str]


class FAQAutoReplyEvent(BaseModel):
    event: Literal["faq_autoreply_triggered"] = "faq_autoreply_triggered"
    hackathon_id: str
    guild_id: str
    channel_id: str
    question: str
    answer: str
    user_id: str
    message_id: str


class ScheduledAnnouncementEvent(BaseModel):
    event: Literal["scheduled_announcement_sent"] = "scheduled_announcement_sent"
    hackathon_id: str
    guild_id: str
    channel_id: str
    event_title: str
    announcement_time: datetime


# FAQ-related schemas
class FAQItem(BaseModel):
    id: Optional[str] = None
    question: str
    answer: str
    category: Optional[str] = None
    tags: List[str] = Field(default=[])


class FAQSyncRequest(BaseModel):
    hackathon_id: str
    faqs: List[FAQItem]


class FAQSyncResponse(BaseModel):
    status: str = "ok"
    synced_count: int
    updated_embeddings: int
