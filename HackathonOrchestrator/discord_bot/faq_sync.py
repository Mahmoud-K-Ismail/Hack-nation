"""
FAQ Synchronization Service
Handles syncing FAQs from the platform and generating embeddings.
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import BotConfig, FAQEmbedding
from .ai_processor import AIProcessor
from .schemas import FAQItem, FAQSyncRequest, FAQSyncResponse

logger = logging.getLogger(__name__)


class FAQSyncService:
    """Service for synchronizing FAQs and generating embeddings"""
    
    def __init__(self):
        self.ai_processor = AIProcessor()
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def sync_hackathon_faqs(self, hackathon_id: str) -> int:
        """Sync FAQs for a specific hackathon"""
        try:
            with SessionLocal() as db:
                config = db.query(BotConfig).filter(
                    BotConfig.hackathon_id == hackathon_id,
                    BotConfig.status == "active"
                ).first()
                
                if not config:
                    logger.warning(f"No active config found for hackathon {hackathon_id}")
                    return 0
                
                faq_config = config.config_json.get("faq", {})
                source = faq_config.get("source", "platform")
                
                if source == "platform":
                    faqs = await self._fetch_platform_faqs(hackathon_id)
                elif source == "google_sheets":
                    faqs = await self._fetch_google_sheets_faqs(faq_config.get("url"))
                else:
                    logger.warning(f"Unsupported FAQ source: {source}")
                    return 0
                
                if faqs:
                    return await self.ai_processor.sync_faq_embeddings(hackathon_id, faqs)
                
                return 0
                
        except Exception as e:
            logger.error(f"Error syncing FAQs for hackathon {hackathon_id}: {e}")
            return 0
    
    async def _fetch_platform_faqs(self, hackathon_id: str) -> List[Dict[str, str]]:
        """Fetch FAQs from the platform API"""
        try:
            session = await self.get_session()
            
            # Get platform API base URL from environment
            import os
            platform_api_url = os.getenv("PLATFORM_API_URL", "http://localhost:8001")
            url = f"{platform_api_url}/hackathon/{hackathon_id}/faq"
            
            # Get API token for platform communication
            api_token = os.getenv("PLATFORM_API_TOKEN", "")
            headers = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json"
            } if api_token else {}
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    faqs = data.get("faqs", [])
                    
                    logger.info(f"Fetched {len(faqs)} FAQs from platform for hackathon {hackathon_id}")
                    return faqs
                elif response.status == 404:
                    logger.info(f"No FAQs found for hackathon {hackathon_id}")
                    return []
                else:
                    logger.error(f"Failed to fetch FAQs: HTTP {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching platform FAQs: {e}")
            return []
    
    async def _fetch_google_sheets_faqs(self, sheets_url: str) -> List[Dict[str, str]]:
        """Fetch FAQs from Google Sheets"""
        try:
            if not sheets_url:
                logger.warning("No Google Sheets URL provided")
                return []
            
            # For now, return empty list - implement Google Sheets integration as needed
            logger.info("Google Sheets FAQ integration not yet implemented")
            return []
            
        except Exception as e:
            logger.error(f"Error fetching Google Sheets FAQs: {e}")
            return []
    
    async def sync_all_hackathons(self):
        """Sync FAQs for all active hackathons"""
        try:
            with SessionLocal() as db:
                configs = db.query(BotConfig).filter(BotConfig.status == "active").all()
                
                total_synced = 0
                for config in configs:
                    faq_config = config.config_json.get("faq", {})
                    
                    if faq_config.get("auto_sync", True):
                        synced = await self.sync_hackathon_faqs(config.hackathon_id)
                        total_synced += synced
                
                logger.info(f"Synced {total_synced} total FAQs across {len(configs)} hackathons")
                return total_synced
                
        except Exception as e:
            logger.error(f"Error syncing all hackathons: {e}")
            return 0
    
    async def manual_faq_sync(self, sync_request: FAQSyncRequest) -> FAQSyncResponse:
        """Manually sync FAQs via API request"""
        try:
            faqs = [faq.dict() for faq in sync_request.faqs]
            updated_count = await self.ai_processor.sync_faq_embeddings(
                sync_request.hackathon_id, 
                faqs
            )
            
            return FAQSyncResponse(
                synced_count=len(faqs),
                updated_embeddings=updated_count
            )
            
        except Exception as e:
            logger.error(f"Error in manual FAQ sync: {e}")
            return FAQSyncResponse(
                status="error",
                synced_count=0,
                updated_embeddings=0
            )
    
    async def get_faq_stats(self, hackathon_id: str) -> Dict[str, Any]:
        """Get FAQ statistics for a hackathon"""
        try:
            with SessionLocal() as db:
                total_faqs = db.query(FAQEmbedding).filter(
                    FAQEmbedding.hackathon_id == hackathon_id
                ).count()
                
                faqs_with_embeddings = db.query(FAQEmbedding).filter(
                    FAQEmbedding.hackathon_id == hackathon_id,
                    FAQEmbedding.embedding.isnot(None)
                ).count()
                
                # Get most recent sync time
                latest_faq = db.query(FAQEmbedding).filter(
                    FAQEmbedding.hackathon_id == hackathon_id
                ).order_by(FAQEmbedding.updated_at.desc()).first()
                
                last_sync = latest_faq.updated_at if latest_faq else None
                
                return {
                    "total_faqs": total_faqs,
                    "faqs_with_embeddings": faqs_with_embeddings,
                    "embedding_coverage": faqs_with_embeddings / total_faqs if total_faqs > 0 else 0.0,
                    "last_sync": last_sync.isoformat() if last_sync else None
                }
                
        except Exception as e:
            logger.error(f"Error getting FAQ stats: {e}")
            return {}


# FAQ sync service instance
faq_sync_service = FAQSyncService()


async def periodic_faq_sync():
    """Periodic task to sync FAQs"""
    while True:
        try:
            logger.info("Starting periodic FAQ sync...")
            await faq_sync_service.sync_all_hackathons()
            
            # Wait for next sync (default 15 minutes)
            await asyncio.sleep(15 * 60)
            
        except Exception as e:
            logger.error(f"Error in periodic FAQ sync: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retry
