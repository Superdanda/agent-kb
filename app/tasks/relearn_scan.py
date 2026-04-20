import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.post import Post, PostStatus
from app.models.post_version import PostVersion, ChangeType
from app.models.learning_record import LearningRecord, LearningStatus
from app.repositories.post_repo import PostRepository
from app.repositories.learning_repo import LearningRepository

logger = logging.getLogger(__name__)


def run_relearn_scan():
    """Scan posts for version updates and mark outdated learning records."""
    logger.info("Starting relearn scan...")
    db = SessionLocal()
    try:
        post_repo = PostRepository(db)
        learning_repo = LearningRepository(db)
        
        # Find all PUBLISHED posts
        posts = db.query(Post).filter(Post.status == PostStatus.PUBLISHED).all()
        
        total_marked = 0
        for post in posts:
            # Get latest version
            latest = post_repo.get_latest_version(post.id)
            if not latest:
                continue
            
            # Skip if latest is MINOR (no need to mark outdated)
            if latest.change_type != ChangeType.MAJOR:
                continue
            
            # Get all learning records that learned an older version
            outdated_records = db.query(LearningRecord).filter(
                LearningRecord.post_id == post.id,
                LearningRecord.status == LearningStatus.LEARNED,
                LearningRecord.learned_version_no < latest.version_no,
            ).all()
            
            for record in outdated_records:
                record.status = LearningStatus.OUTDATED
                record.updated_at = datetime.now(timezone.utc)
                logger.info(f"Marked record {record.id} as OUTDATED for post {post.id}")
            
            total_marked += len(outdated_records)
        
        db.commit()
        logger.info(f"Relearn scan complete. Marked {total_marked} records as OUTDATED across {len(posts)} posts")
        return total_marked
        
    except Exception as e:
        logger.error(f"Relearn scan error: {e}")
        db.rollback()
        raise
    finally:
        db.close()
