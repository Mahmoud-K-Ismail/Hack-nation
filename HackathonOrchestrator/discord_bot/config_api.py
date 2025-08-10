"""
Discord Bot Configuration API endpoints
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import json
import uuid
import logging

from .database import get_db
from .models import BotConfig, BotEvent
from .schemas import (
    BotConfigurationRequest, 
    BotConfigurationResponse, 
    BotConfigurationUpdate,
    ErrorResponse
)
from .security import verify_jwt_token, JWTClaims

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/bot", tags=["Discord Bot Configuration"])


@router.post("/configure", response_model=BotConfigurationResponse)
async def create_or_update_bot_config(
    config_request: BotConfigurationRequest,
    db: Session = Depends(get_db),
    authorization: str = Header(...),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Create or replace bot configuration for a hackathon.
    Idempotent when hackathon_id is the same.
    """
    try:
        # Verify JWT token
        claims = verify_jwt_token(authorization)
        if "bot:configure" not in claims.scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing required scope: bot:configure"
            )
        
        # Check if configuration already exists
        existing_config = db.query(BotConfig).filter(
            BotConfig.hackathon_id == config_request.hackathon_id
        ).first()
        
        config_data = config_request.dict()
        
        if existing_config:
            # Update existing configuration
            existing_config.discord_guild_id = config_request.discord.guild_id
            existing_config.installation_id = config_request.discord.installation_id
            existing_config.config_json = config_data
            existing_config.updated_at = datetime.utcnow()
            existing_config.status = "active"
            
            db.commit()
            
            config_id = str(existing_config.id)
            message = "Configuration updated."
            
            logger.info(f"Updated bot configuration for hackathon {config_request.hackathon_id}")
            
        else:
            # Create new configuration
            new_config = BotConfig(
                hackathon_id=config_request.hackathon_id,
                discord_guild_id=config_request.discord.guild_id,
                installation_id=config_request.discord.installation_id,
                config_json=config_data,
                status="active"
            )
            
            db.add(new_config)
            db.commit()
            
            config_id = str(new_config.id)
            message = "Configuration created."
            
            logger.info(f"Created new bot configuration for hackathon {config_request.hackathon_id}")
        
        # Trigger configuration reload in bot service
        await _trigger_config_reload(config_request.hackathon_id)
        
        return BotConfigurationResponse(
            hackathon_id=config_request.hackathon_id,
            config_id=config_id,
            message=message,
            applied_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error: {e}")
        if "discord_guild_id" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Discord guild already linked to another hackathon"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration validation failed"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating/updating bot configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/configure", response_model=BotConfigurationRequest)
async def get_bot_config(
    hackathon_id: str,
    db: Session = Depends(get_db),
    authorization: str = Header(...)
):
    """Get current bot configuration for a hackathon"""
    try:
        # Verify JWT token
        claims = verify_jwt_token(authorization)
        
        config = db.query(BotConfig).filter(
            BotConfig.hackathon_id == hackathon_id
        ).first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No configuration found for hackathon {hackathon_id}"
            )
        
        return BotConfigurationRequest(**config.config_json)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving bot configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.patch("/configure/{config_id}", response_model=BotConfigurationResponse)
async def update_bot_config(
    config_id: str,
    update_request: BotConfigurationUpdate,
    db: Session = Depends(get_db),
    authorization: str = Header(...),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """Partially update bot configuration"""
    try:
        # Verify JWT token
        claims = verify_jwt_token(authorization)
        if "bot:configure" not in claims.scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing required scope: bot:configure"
            )
        
        config = db.query(BotConfig).filter(BotConfig.id == config_id).first()
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration {config_id} not found"
            )
        
        # Merge updates with existing configuration
        current_config = config.config_json.copy()
        update_data = update_request.dict(exclude_unset=True)
        
        for key, value in update_data.items():
            if value is not None:
                current_config[key] = value
        
        config.config_json = current_config
        config.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Trigger configuration reload
        await _trigger_config_reload(config.hackathon_id)
        
        logger.info(f"Updated bot configuration {config_id} for hackathon {config.hackathon_id}")
        
        return BotConfigurationResponse(
            hackathon_id=config.hackathon_id,
            config_id=str(config.id),
            message="Configuration updated.",
            applied_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating bot configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/configure/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot_config(
    config_id: str,
    db: Session = Depends(get_db),
    authorization: str = Header(...)
):
    """Delete bot configuration and disable bot for hackathon"""
    try:
        # Verify JWT token
        claims = verify_jwt_token(authorization)
        if "bot:configure" not in claims.scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing required scope: bot:configure"
            )
        
        config = db.query(BotConfig).filter(BotConfig.id == config_id).first()
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration {config_id} not found"
            )
        
        hackathon_id = config.hackathon_id
        
        # Mark as disabled instead of deleting to preserve audit trail
        config.status = "disabled"
        config.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Trigger bot to leave guild and clean up
        await _trigger_config_reload(hackathon_id, disable=True)
        
        logger.info(f"Disabled bot configuration {config_id} for hackathon {hackathon_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting bot configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/stats")
async def get_bot_stats(
    db: Session = Depends(get_db),
    authorization: str = Header(...)
):
    """Get bot service statistics"""
    try:
        # Verify JWT token
        verify_jwt_token(authorization)
        
        from .database import DatabaseManager
        
        stats = DatabaseManager.get_stats()
        stats["health"] = DatabaseManager.health_check()
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bot stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


async def _trigger_config_reload(hackathon_id: str, disable: bool = False):
    """
    Trigger bot service to reload configuration.
    In a production setup, this would notify the bot service via Redis/message queue.
    For now, we'll just log the action.
    """
    action = "disable" if disable else "reload"
    logger.info(f"Triggering bot config {action} for hackathon {hackathon_id}")
    
    # TODO: Implement actual bot service notification
    # This could be done via:
    # 1. Redis pub/sub
    # 2. Database trigger
    # 3. HTTP webhook to bot service
    # 4. Message queue (RabbitMQ, etc.)
    pass
