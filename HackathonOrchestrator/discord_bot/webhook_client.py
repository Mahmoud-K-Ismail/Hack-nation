"""
Webhook client for sending events back to the platform
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import aiohttp
import hmac
import hashlib
import logging
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import BotEvent
from .security import create_webhook_signature

logger = logging.getLogger(__name__)


class WebhookClient:
    """Client for sending webhook events to the platform"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.max_retries = 3
        self.retry_delays = [1, 5, 15]  # seconds
        
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def send_event(self, webhook_url: str, event_data: Dict[str, Any], hackathon_id: str) -> bool:
        """Send an event to the platform webhook with retries"""
        try:
            # Store event in database first
            event_id = await self._store_event(event_data, hackathon_id)
            
            # Attempt to deliver webhook
            success = await self._deliver_webhook(webhook_url, event_data, hackathon_id)
            
            # Update delivery status
            await self._update_event_status(event_id, success)
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending webhook event: {e}")
            return False
    
    async def _store_event(self, event_data: Dict[str, Any], hackathon_id: str) -> str:
        """Store event in database"""
        try:
            with SessionLocal() as db:
                # Find bot config for this hackathon
                from .models import BotConfig
                config = db.query(BotConfig).filter(
                    BotConfig.hackathon_id == hackathon_id,
                    BotConfig.status == "active"
                ).first()
                
                if not config:
                    logger.warning(f"No active config found for hackathon {hackathon_id}")
                    return ""
                
                event = BotEvent(
                    bot_config_id=config.id,
                    event_type=event_data.get("event", "unknown"),
                    payload=event_data,
                    delivered=False,
                    delivery_attempts=0
                )
                
                db.add(event)
                db.commit()
                
                return str(event.id)
                
        except Exception as e:
            logger.error(f"Error storing event: {e}")
            return ""
    
    async def _deliver_webhook(self, webhook_url: str, event_data: Dict[str, Any], hackathon_id: str) -> bool:
        """Deliver webhook with retries"""
        for attempt in range(self.max_retries):
            try:
                success = await self._send_webhook_request(webhook_url, event_data, hackathon_id)
                if success:
                    return True
                
                # Wait before retry
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delays[attempt])
                    
            except Exception as e:
                logger.error(f"Webhook delivery attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delays[attempt])
        
        logger.error(f"Failed to deliver webhook after {self.max_retries} attempts")
        return False
    
    async def _send_webhook_request(self, webhook_url: str, event_data: Dict[str, Any], hackathon_id: str) -> bool:
        """Send a single webhook request"""
        try:
            session = await self.get_session()
            
            # Prepare payload
            payload = json.dumps(event_data, default=str)
            
            # Create signature
            webhook_secret = self._get_webhook_secret(hackathon_id)
            signature = create_webhook_signature(payload, webhook_secret) if webhook_secret else None
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "HackathonBot/1.0",
                "X-Event-Type": event_data.get("event", "unknown"),
                "X-Hackathon-ID": hackathon_id,
                "X-Timestamp": str(int(datetime.utcnow().timestamp()))
            }
            
            if signature:
                headers["X-Signature"] = signature
            
            # Send request
            async with session.post(webhook_url, data=payload, headers=headers) as response:
                if response.status in [200, 201, 202]:
                    logger.info(f"Webhook delivered successfully: {event_data.get('event')}")
                    return True
                else:
                    response_text = await response.text()
                    logger.warning(f"Webhook delivery failed with status {response.status}: {response_text}")
                    return False
                    
        except asyncio.TimeoutError:
            logger.error("Webhook request timed out")
            return False
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending webhook: {e}")
            return False
    
    def _get_webhook_secret(self, hackathon_id: str) -> Optional[str]:
        """Get webhook secret for hackathon"""
        try:
            # In production, this would fetch from secure storage
            # For now, use environment variable or generate per hackathon
            return os.getenv(f"WEBHOOK_SECRET_{hackathon_id}") or os.getenv("DEFAULT_WEBHOOK_SECRET", "")
        except Exception as e:
            logger.error(f"Error getting webhook secret: {e}")
            return None
    
    async def _update_event_status(self, event_id: str, success: bool):
        """Update event delivery status in database"""
        try:
            if not event_id:
                return
                
            with SessionLocal() as db:
                event = db.query(BotEvent).filter(BotEvent.id == event_id).first()
                if event:
                    event.delivery_attempts += 1
                    event.delivered = success
                    if success:
                        event.delivered_at = datetime.utcnow()
                    
                    db.commit()
                    
        except Exception as e:
            logger.error(f"Error updating event status: {e}")
    
    async def retry_failed_events(self, max_age_hours: int = 24):
        """Retry failed webhook deliveries"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            with SessionLocal() as db:
                # Get failed events that are not too old
                failed_events = db.query(BotEvent).filter(
                    BotEvent.delivered == False,
                    BotEvent.delivery_attempts < self.max_retries,
                    BotEvent.created_at >= cutoff_time
                ).all()
                
                logger.info(f"Retrying {len(failed_events)} failed webhook deliveries")
                
                for event in failed_events:
                    # Get webhook URL from bot config
                    config = event.bot_config
                    if not config or config.status != "active":
                        continue
                    
                    logging_config = config.config_json.get("logging", {})
                    webhook_url = logging_config.get("platform_webhook_url")
                    
                    if not webhook_url:
                        continue
                    
                    # Attempt redelivery
                    success = await self._deliver_webhook(
                        webhook_url, 
                        event.payload, 
                        config.hackathon_id
                    )
                    
                    # Update status
                    event.delivery_attempts += 1
                    event.delivered = success
                    if success:
                        event.delivered_at = datetime.utcnow()
                
                db.commit()
                
        except Exception as e:
            logger.error(f"Error retrying failed events: {e}")
    
    async def get_webhook_stats(self, hackathon_id: Optional[str] = None) -> Dict[str, Any]:
        """Get webhook delivery statistics"""
        try:
            with SessionLocal() as db:
                query = db.query(BotEvent)
                
                if hackathon_id:
                    from .models import BotConfig
                    config = db.query(BotConfig).filter(
                        BotConfig.hackathon_id == hackathon_id
                    ).first()
                    
                    if config:
                        query = query.filter(BotEvent.bot_config_id == config.id)
                
                # Last 24 hours
                cutoff = datetime.utcnow() - timedelta(hours=24)
                recent_events = query.filter(BotEvent.created_at >= cutoff).all()
                
                total_events = len(recent_events)
                delivered_events = len([e for e in recent_events if e.delivered])
                failed_events = total_events - delivered_events
                
                return {
                    "total_events_24h": total_events,
                    "delivered_events_24h": delivered_events,
                    "failed_events_24h": failed_events,
                    "delivery_rate": delivered_events / total_events if total_events > 0 else 0.0
                }
                
        except Exception as e:
            logger.error(f"Error getting webhook stats: {e}")
            return {}


# Global webhook client instance
webhook_client = WebhookClient()
