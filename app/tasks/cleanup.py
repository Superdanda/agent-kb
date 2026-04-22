import logging
import os
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.config import settings
from app.models.api_nonce import ApiNonce

logger = logging.getLogger(__name__)


def run_cleanup_task():
    """Clean up expired nonces and temporary files."""
    logger.info("Starting cleanup task...")
    db = SessionLocal()
    cleaned = 0
    
    try:
        # Clean expired nonces
        now = datetime.now(timezone.utc)
        expired_count = db.query(ApiNonce).filter(ApiNonce.expires_at < now).delete()
        db.commit()
        cleaned += expired_count
        logger.info(f"Deleted {expired_count} expired nonces")
        
        # Clean local temp upload files older than 24h
        temp_dirs_cleaned = _clean_temp_dirs()
        cleaned += temp_dirs_cleaned
        
        logger.info(f"Cleanup complete. Cleaned {cleaned} items total")
        return cleaned
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def _clean_temp_dirs() -> int:
    """Clean temporary upload directories."""
    cleaned = 0
    temp_base = Path("/tmp/hermes-kb-uploads")
    
    if not temp_base.exists():
        return 0
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    
    for item in temp_base.iterdir():
        try:
            mtime = datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                cleaned += 1
                logger.debug(f"Removed temp file: {item}")
        except Exception as e:
            logger.warning(f"Failed to clean {item}: {e}")
    
    return cleaned
