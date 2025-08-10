"""
Discord Bot Service Main Entry Point
"""

import os
import asyncio
import logging
from typing import Optional
import signal
import sys
from dotenv import load_dotenv

from .bot_client import create_bot, HackathonBot
from .database import init_database, DatabaseManager
from .webhook_client import webhook_client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('discord_bot.log')
    ]
)

logger = logging.getLogger(__name__)


class BotService:
    """Main bot service orchestrator"""
    
    def __init__(self):
        self.bot: Optional[HackathonBot] = None
        self.running = False
        
    async def start(self):
        """Start the bot service"""
        try:
            logger.info("Starting Discord Bot Service...")
            
            # Initialize database
            logger.info("Initializing database...")
            init_database()
            
            # Check database health
            if not DatabaseManager.health_check():
                logger.error("Database health check failed")
                return False
            
            # Create and start bot
            self.bot = create_bot()
            
            # Get Discord bot token
            bot_token = os.getenv("DISCORD_BOT_TOKEN")
            if not bot_token:
                logger.error("DISCORD_BOT_TOKEN environment variable not set")
                return False
            
            # Set up signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            # Start bot
            logger.info("Starting Discord bot...")
            self.running = True
            
            try:
                await self.bot.start(bot_token)
            except Exception as e:
                logger.error(f"Error starting bot: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting bot service: {e}")
            return False
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def stop(self):
        """Stop the bot service"""
        try:
            logger.info("Stopping Discord Bot Service...")
            self.running = False
            
            if self.bot:
                # Close bot connection
                await self.bot.close()
                logger.info("Bot connection closed")
            
            # Close webhook client
            await webhook_client.close()
            logger.info("Webhook client closed")
            
            logger.info("Bot service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping bot service: {e}")
    
    async def reload_config(self, guild_id: str):
        """Reload configuration for a specific guild"""
        if self.bot:
            await self.bot.reload_guild_config(guild_id)
    
    def get_status(self) -> dict:
        """Get bot service status"""
        return {
            "running": self.running,
            "bot_connected": self.bot is not None and not self.bot.is_closed(),
            "guild_count": len(self.bot.guilds) if self.bot else 0,
            "database_healthy": DatabaseManager.health_check()
        }


# Global bot service instance
bot_service = BotService()


async def main():
    """Main entry point for the bot service"""
    try:
        await bot_service.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await bot_service.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot service interrupted")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
