"""
Database configuration and utilities for Discord bot service
"""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from .models import Base
import logging

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:password@localhost:5432/hackathon_orchestrator"
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=os.getenv("DEBUG", "0") == "1"
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """Initialize database with extensions and tables"""
    try:
        # Create pgvector extension if using PostgreSQL
        from sqlalchemy import text
        
        with engine.connect() as conn:
            # Enable pgvector extension
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
                logger.info("pgvector extension enabled")
            except Exception as e:
                logger.warning(f"Could not enable pgvector extension: {e}")
        
        # Create tables
        create_tables()
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


class DatabaseManager:
    """Database management utilities"""
    
    @staticmethod
    def health_check() -> bool:
        """Check database connection health"""
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    @staticmethod
    def cleanup_old_data():
        """Clean up old message contexts and other temporary data"""
        try:
            from datetime import datetime, timedelta
            from .models import MessageContext, FloodDetection
            
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            with SessionLocal() as db:
                # Clean up old message contexts (keep only last 24 hours)
                deleted_messages = db.query(MessageContext).filter(
                    MessageContext.created_at < cutoff_time
                ).delete()
                
                # Clean up old flood detections (keep only last 1 hour)
                flood_cutoff = datetime.utcnow() - timedelta(hours=1)
                deleted_floods = db.query(FloodDetection).filter(
                    FloodDetection.last_seen < flood_cutoff
                ).delete()
                
                db.commit()
                
                logger.info(f"Cleaned up {deleted_messages} old message contexts and {deleted_floods} old flood detections")
                
        except Exception as e:
            logger.error(f"Error during data cleanup: {e}")
    
    @staticmethod
    def get_stats() -> dict:
        """Get database statistics"""
        try:
            from .models import BotConfig, BotEvent, FAQEmbedding, MessageContext
            
            with SessionLocal() as db:
                stats = {
                    "active_configs": db.query(BotConfig).filter(BotConfig.status == "active").count(),
                    "total_events": db.query(BotEvent).count(),
                    "faq_embeddings": db.query(FAQEmbedding).count(),
                    "recent_messages": db.query(MessageContext).filter(
                        MessageContext.created_at >= datetime.utcnow() - timedelta(hours=1)
                    ).count()
                }
                return stats
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}


# Initialize database on import
if __name__ != "__main__":
    init_database()
