"""
Discord Bot Client
Handles Discord bot functionality including message processing, FAQ matching, and escalation.
"""

import os
import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import discord
from discord.ext import commands, tasks
import aiohttp
import logging
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import BotConfig, MessageContext, FloodDetection, FAQEmbedding, ScheduledAnnouncement
from .ai_processor import AIProcessor
from .webhook_client import WebhookClient

logger = logging.getLogger(__name__)


class HackathonBot(commands.Bot):
    """Main Discord bot class for hackathon assistance"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True
        
        super().__init__(
            command_prefix='!hack',
            intents=intents,
            help_command=None
        )
        
        self.ai_processor = AIProcessor()
        self.webhook_client = WebhookClient()
        self.guild_configs: Dict[str, dict] = {}
        
    async def setup_hook(self):
        """Setup bot after login"""
        await self.load_guild_configs()
        
        # Start background tasks
        self.cleanup_task.start()
        self.announcement_task.start()
        
        logger.info(f"Bot setup complete. Serving {len(self.guilds)} guilds.")
    
    async def load_guild_configs(self):
        """Load all active guild configurations"""
        try:
            with SessionLocal() as db:
                configs = db.query(BotConfig).filter(BotConfig.status == "active").all()
                
                for config in configs:
                    self.guild_configs[config.discord_guild_id] = config.config_json
                
                logger.info(f"Loaded {len(configs)} guild configurations")
                
        except Exception as e:
            logger.error(f"Error loading guild configurations: {e}")
    
    async def reload_guild_config(self, guild_id: str):
        """Reload configuration for a specific guild"""
        try:
            with SessionLocal() as db:
                config = db.query(BotConfig).filter(
                    BotConfig.discord_guild_id == guild_id,
                    BotConfig.status == "active"
                ).first()
                
                if config:
                    self.guild_configs[guild_id] = config.config_json
                    logger.info(f"Reloaded configuration for guild {guild_id}")
                else:
                    # Configuration disabled or removed
                    if guild_id in self.guild_configs:
                        del self.guild_configs[guild_id]
                        logger.info(f"Removed configuration for guild {guild_id}")
                        
                        # Leave the guild if configuration is disabled
                        guild = self.get_guild(int(guild_id))
                        if guild:
                            await guild.leave()
                            logger.info(f"Left guild {guild_id} due to disabled configuration")
                
        except Exception as e:
            logger.error(f"Error reloading guild config for {guild_id}: {e}")
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Update bot presence
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="for hackathon questions"
        )
        await self.change_presence(activity=activity)
    
    async def on_guild_join(self, guild):
        """Called when bot joins a new guild"""
        logger.info(f"Joined guild: {guild.name} ({guild.id})")
        
        # Check if we have configuration for this guild
        if str(guild.id) not in self.guild_configs:
            logger.warning(f"No configuration found for guild {guild.id}, leaving...")
            await guild.leave()
            return
        
        # Send welcome message if configured
        config = self.guild_configs.get(str(guild.id), {})
        personality = config.get("personality", {})
        welcome_message = personality.get("welcome_message")
        
        if welcome_message:
            # Find a suitable channel to send welcome message
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    try:
                        await channel.send(welcome_message)
                        break
                    except discord.Forbidden:
                        continue
    
    async def on_message(self, message):
        """Handle incoming messages"""
        # Ignore messages from bots
        if message.author.bot:
            return
        
        # Get guild configuration
        guild_id = str(message.guild.id)
        config = self.guild_configs.get(guild_id)
        
        if not config:
            return
        
        # Process the message
        await self.process_message(message, config)
        
        # Process commands
        await self.process_commands(message)
    
    async def process_message(self, message: discord.Message, config: dict):
        """Process message for FAQ, sentiment, and escalation"""
        try:
            features = config.get("features", {})
            
            # Store message context
            await self.store_message_context(message, config)
            
            # Check for FAQ match if enabled
            if features.get("faq_autoreply", False):
                faq_response = await self.check_faq_match(message, config)
                if faq_response:
                    await message.reply(faq_response)
                    await self.log_faq_event(message, faq_response, config)
                    return
            
            # Check for flood detection if enabled
            if features.get("flood_detection", False):
                await self.check_flood_detection(message, config)
            
            # Check for escalation if enabled
            if features.get("escalation", False):
                await self.check_escalation(message, config)
                
        except Exception as e:
            logger.error(f"Error processing message {message.id}: {e}")
    
    async def store_message_context(self, message: discord.Message, config: dict):
        """Store message context for analysis"""
        try:
            features = config.get("features", {})
            
            # Analyze sentiment if enabled
            sentiment_score = None
            urgency_score = None
            category = None
            
            if features.get("sentiment_detection", False):
                analysis = await self.ai_processor.analyze_message(message.content)
                sentiment_score = analysis.get("sentiment_score")
                urgency_score = analysis.get("urgency_score")
                category = analysis.get("category")
            
            # Store in database
            with SessionLocal() as db:
                context = MessageContext(
                    guild_id=str(message.guild.id),
                    channel_id=str(message.channel.id),
                    user_id=str(message.author.id),
                    message_id=str(message.id),
                    content=message.content,
                    sentiment_score=sentiment_score,
                    urgency_score=urgency_score,
                    category=category
                )
                
                db.add(context)
                db.commit()
                
        except Exception as e:
            logger.error(f"Error storing message context: {e}")
    
    async def check_faq_match(self, message: discord.Message, config: dict) -> Optional[str]:
        """Check if message matches any FAQ"""
        try:
            hackathon_id = config["hackathon_id"]
            embeddings_config = config.get("embeddings", {})
            threshold = embeddings_config.get("similarity_threshold", 0.78)
            
            # Get FAQ match using AI processor
            match = await self.ai_processor.find_faq_match(
                message.content, 
                hackathon_id, 
                threshold
            )
            
            if match:
                return match["answer"]
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking FAQ match: {e}")
            return None
    
    async def check_flood_detection(self, message: discord.Message, config: dict):
        """Check for repeated questions and create summary if needed"""
        try:
            # Create hash of message content (simplified)
            content_hash = hashlib.md5(message.content.lower().encode()).hexdigest()
            
            with SessionLocal() as db:
                # Check existing flood detection
                flood = db.query(FloodDetection).filter(
                    FloodDetection.guild_id == str(message.guild.id),
                    FloodDetection.channel_id == str(message.channel.id),
                    FloodDetection.question_hash == content_hash
                ).first()
                
                if flood:
                    flood.message_count += 1
                    flood.last_seen = datetime.utcnow()
                else:
                    flood = FloodDetection(
                        guild_id=str(message.guild.id),
                        channel_id=str(message.channel.id),
                        question_hash=content_hash,
                        message_count=1
                    )
                    db.add(flood)
                
                db.commit()
                
                # Check if we need to respond to flood
                if flood.message_count >= 5 and not flood.responded:
                    await self.handle_flood_response(message, config, flood)
                    
        except Exception as e:
            logger.error(f"Error in flood detection: {e}")
    
    async def handle_flood_response(self, message: discord.Message, config: dict, flood: FloodDetection):
        """Handle flood response by creating summary"""
        try:
            # Get recent similar messages
            with SessionLocal() as db:
                recent_messages = db.query(MessageContext).filter(
                    MessageContext.guild_id == str(message.guild.id),
                    MessageContext.channel_id == str(message.channel.id),
                    MessageContext.created_at >= datetime.utcnow() - timedelta(minutes=5)
                ).all()
                
                # Generate summary using AI
                messages_content = [msg.content for msg in recent_messages]
                summary = await self.ai_processor.summarize_flood(messages_content)
                
                # Post summary response
                response_msg = await message.channel.send(
                    f"📢 **Flood Detection Alert**\n\n"
                    f"I've noticed multiple similar questions. Here's a summary:\n\n"
                    f"{summary}\n\n"
                    f"*This message has been pinned for visibility.*"
                )
                
                # Pin the response if feature enabled
                features = config.get("features", {})
                if features.get("pin_auto_answers", False):
                    await response_msg.pin()
                    flood.pinned_message_id = str(response_msg.id)
                
                flood.responded = True
                db.commit()
                
        except Exception as e:
            logger.error(f"Error handling flood response: {e}")
    
    async def check_escalation(self, message: discord.Message, config: dict):
        """Check if message requires escalation to organizers"""
        try:
            escalation_config = config.get("escalation", {})
            if not escalation_config.get("enabled", False):
                return
            
            # Analyze message for escalation criteria
            analysis = await self.ai_processor.analyze_message(message.content)
            urgency_score = analysis.get("urgency_score", 0)
            sentiment_score = analysis.get("sentiment_score", 0)
            
            threshold = escalation_config.get("escalation_threshold", 0.7)
            
            # Check if escalation is needed
            needs_escalation = (
                urgency_score >= threshold or 
                sentiment_score <= -0.5  # Very negative sentiment
            )
            
            if needs_escalation:
                await self.escalate_issue(message, config, urgency_score)
                
        except Exception as e:
            logger.error(f"Error checking escalation: {e}")
    
    async def escalate_issue(self, message: discord.Message, config: dict, severity: float):
        """Escalate issue to organizers"""
        try:
            escalation_config = config.get("escalation", {})
            escalation_channel_id = escalation_config.get("channel_id")
            
            if not escalation_channel_id:
                logger.warning("No escalation channel configured")
                return
            
            # Get escalation channel
            escalation_channel = self.get_channel(int(escalation_channel_id))
            if not escalation_channel:
                logger.warning(f"Escalation channel {escalation_channel_id} not found")
                return
            
            # Create escalation summary
            summary = await self.ai_processor.create_escalation_summary(message.content)
            
            # Prepare escalation message
            embed = discord.Embed(
                title="🚨 Issue Escalation",
                description=summary,
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="Severity",
                value=f"{severity:.2f}/1.0",
                inline=True
            )
            
            embed.add_field(
                name="Channel",
                value=f"#{message.channel.name}",
                inline=True
            )
            
            embed.add_field(
                name="User",
                value=f"{message.author.mention}",
                inline=True
            )
            
            embed.add_field(
                name="Jump to Message",
                value=f"[Click here]({message.jump_url})",
                inline=False
            )
            
            # Mention configured roles
            notify_roles = escalation_config.get("notify_roles", [])
            mentions = " ".join([f"<@&{role_id}>" for role_id in notify_roles])
            
            content = f"{mentions}\n" if mentions else ""
            content += "**High-priority issue detected in hackathon Discord:**"
            
            # Send escalation
            await escalation_channel.send(content=content, embed=embed)
            
            # Send webhook event to platform
            await self.send_escalation_webhook(message, config, summary, severity)
            
            logger.info(f"Escalated issue from {message.author} in {message.guild.name}")
            
        except Exception as e:
            logger.error(f"Error escalating issue: {e}")
    
    async def send_escalation_webhook(self, message: discord.Message, config: dict, summary: str, severity: float):
        """Send escalation event to platform webhook"""
        try:
            logging_config = config.get("logging", {})
            if not logging_config.get("send_to_platform_webhook", False):
                return
            
            webhook_url = logging_config.get("platform_webhook_url")
            if not webhook_url:
                return
            
            event_data = {
                "event": "issue_escalation",
                "hackathon_id": config["hackathon_id"],
                "guild_id": str(message.guild.id),
                "channel_id": str(message.channel.id),
                "summary": summary,
                "severity": severity,
                "messages": [{
                    "author": str(message.author),
                    "content": message.content,
                    "timestamp": message.created_at.isoformat()
                }],
                "discord_jump_links": [message.jump_url]
            }
            
            await self.webhook_client.send_event(webhook_url, event_data, config["hackathon_id"])
            
        except Exception as e:
            logger.error(f"Error sending escalation webhook: {e}")
    
    async def log_faq_event(self, message: discord.Message, answer: str, config: dict):
        """Log FAQ auto-reply event"""
        try:
            logging_config = config.get("logging", {})
            if not logging_config.get("send_to_platform_webhook", False):
                return
            
            webhook_url = logging_config.get("platform_webhook_url")
            if not webhook_url:
                return
            
            event_data = {
                "event": "faq_autoreply_triggered",
                "hackathon_id": config["hackathon_id"],
                "guild_id": str(message.guild.id),
                "channel_id": str(message.channel.id),
                "question": message.content,
                "answer": answer,
                "user_id": str(message.author.id),
                "message_id": str(message.id)
            }
            
            await self.webhook_client.send_event(webhook_url, event_data, config["hackathon_id"])
            
        except Exception as e:
            logger.error(f"Error logging FAQ event: {e}")
    
    @tasks.loop(hours=1)
    async def cleanup_task(self):
        """Periodic cleanup of old data"""
        try:
            from .database import DatabaseManager
            DatabaseManager.cleanup_old_data()
            logger.info("Completed periodic data cleanup")
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
    
    @tasks.loop(minutes=1)
    async def announcement_task(self):
        """Check for scheduled announcements"""
        try:
            await self.process_scheduled_announcements()
        except Exception as e:
            logger.error(f"Error in announcement task: {e}")
    
    async def process_scheduled_announcements(self):
        """Process scheduled announcements that are due"""
        try:
            now = datetime.utcnow()
            
            with SessionLocal() as db:
                # Get announcements that are due
                due_announcements = db.query(ScheduledAnnouncement).filter(
                    ScheduledAnnouncement.scheduled_time <= now,
                    ScheduledAnnouncement.sent == False
                ).all()
                
                for announcement in due_announcements:
                    await self.send_scheduled_announcement(announcement, db)
                    
        except Exception as e:
            logger.error(f"Error processing scheduled announcements: {e}")
    
    async def send_scheduled_announcement(self, announcement: ScheduledAnnouncement, db: Session):
        """Send a scheduled announcement"""
        try:
            # Get guild configuration
            config = self.guild_configs.get(announcement.hackathon_id)
            if not config:
                logger.warning(f"No config found for hackathon {announcement.hackathon_id}")
                return
            
            # Get target channel
            if announcement.channel_id:
                channel = self.get_channel(int(announcement.channel_id))
            else:
                # Use default channel (first available)
                guild = discord.utils.get(self.guilds, id=int(config["discord"]["guild_id"]))
                if not guild:
                    logger.warning(f"Guild not found for hackathon {announcement.hackathon_id}")
                    return
                
                channel = discord.utils.get(guild.text_channels, name="general")
                if not channel:
                    channel = guild.text_channels[0] if guild.text_channels else None
            
            if not channel:
                logger.warning(f"No suitable channel found for announcement {announcement.id}")
                return
            
            # Create announcement embed
            embed = discord.Embed(
                title=f"📅 {announcement.title}",
                description=announcement.description,
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="Event Time",
                value=f"<t:{int(announcement.scheduled_time.timestamp())}:F>",
                inline=False
            )
            
            # Send announcement
            await channel.send(embed=embed)
            
            # Mark as sent
            announcement.sent = True
            announcement.sent_at = datetime.utcnow()
            db.commit()
            
            # Send webhook event
            await self.send_announcement_webhook(announcement, config, channel)
            
            logger.info(f"Sent scheduled announcement: {announcement.title}")
            
        except Exception as e:
            logger.error(f"Error sending scheduled announcement {announcement.id}: {e}")
    
    async def send_announcement_webhook(self, announcement: ScheduledAnnouncement, config: dict, channel: discord.TextChannel):
        """Send announcement webhook to platform"""
        try:
            logging_config = config.get("logging", {})
            if not logging_config.get("send_to_platform_webhook", False):
                return
            
            webhook_url = logging_config.get("platform_webhook_url")
            if not webhook_url:
                return
            
            event_data = {
                "event": "scheduled_announcement_sent",
                "hackathon_id": announcement.hackathon_id,
                "guild_id": str(channel.guild.id),
                "channel_id": str(channel.id),
                "event_title": announcement.title,
                "announcement_time": datetime.utcnow().isoformat()
            }
            
            await self.webhook_client.send_event(webhook_url, event_data, announcement.hackathon_id)
            
        except Exception as e:
            logger.error(f"Error sending announcement webhook: {e}")


def create_bot() -> HackathonBot:
    """Create and configure the Discord bot"""
    bot = HackathonBot()
    
    # Add bot commands
    @bot.command(name='ping')
    async def ping(ctx):
        """Check bot responsiveness"""
        await ctx.send(f'Pong! Latency: {round(bot.latency * 1000)}ms')
    
    @bot.command(name='help')
    async def help_command(ctx):
        """Show help information"""
        embed = discord.Embed(
            title="🤖 Hackathon Bot Help",
            description="I'm here to help with your hackathon questions!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Features",
            value="• FAQ Auto-replies\n• Issue Escalation\n• Flood Detection\n• Scheduled Announcements",
            inline=False
        )
        
        embed.add_field(
            name="Commands",
            value="`!hackping` - Check bot latency\n`!hackhelp` - Show this help",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    return bot
