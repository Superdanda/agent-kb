from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.post_asset import PostAsset


class AssetRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, asset: PostAsset) -> PostAsset:
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def get_by_id(self, id: str) -> PostAsset | None:
        return (
            self.db.query(PostAsset)
            .filter(PostAsset.id == id)
            .first()
        )

    def get_by_post(
        self, post_id: str, version_id: Optional[str] = None
    ) -> List[PostAsset]:
        query = self.db.query(PostAsset).filter(PostAsset.post_id == post_id)
        if version_id:
            query = query.filter(PostAsset.version_id == version_id)
        return query.order_by(PostAsset.created_at.desc()).all()

    def get_by_sha256(self, sha256: str) -> PostAsset | None:
        return self.db.query(PostAsset).filter(PostAsset.sha256 == sha256).first()

    def count_by_post(self, post_id: str) -> int:
        return self.db.query(PostAsset).filter(PostAsset.post_id == post_id).count()
