from typing import Optional, List

from sqlalchemy.orm import Session

from app.repositories.domain_repo import DomainRepository
from app.models.knowledge_domain import KnowledgeDomain
from app.core.exceptions import ResourceNotFoundError, ConflictError


class DomainService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DomainRepository(db)

    def get_by_id(self, domain_id: str) -> KnowledgeDomain:
        domain = self.repo.get_by_id(domain_id)
        if not domain:
            raise ResourceNotFoundError(f"Domain {domain_id} not found")
        return domain

    def get_by_code(self, code: str) -> KnowledgeDomain:
        domain = self.repo.get_by_code(code)
        if not domain:
            raise ResourceNotFoundError(f"Domain with code '{code}' not found")
        return domain

    def get_all_domains(self, include_inactive: bool = False) -> List[KnowledgeDomain]:
        return self.repo.get_all(include_inactive=include_inactive)

    def create_domain(
        self,
        code: str,
        name: str,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        sort_order: int = 0,
    ) -> KnowledgeDomain:
        # Check for duplicate code
        existing = self.repo.get_by_code(code)
        if existing:
            raise ConflictError(f"Domain with code '{code}' already exists")
        return self.repo.create(
            code=code,
            name=name,
            description=description,
            icon=icon,
            color=color,
            sort_order=sort_order,
        )

    def update_domain(
        self,
        domain_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        sort_order: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> KnowledgeDomain:
        return self.repo.update(
            domain_id=domain_id,
            name=name,
            description=description,
            icon=icon,
            color=color,
            sort_order=sort_order,
            is_active=is_active,
        )

    def delete_domain(self, domain_id: str) -> bool:
        # Check if domain has posts
        domain = self.repo.get_by_id(domain_id)
        if not domain:
            raise ResourceNotFoundError(f"Domain {domain_id} not found")
        if domain.posts.count() > 0:
            raise ConflictError(f"Domain has {domain.posts.count()} posts, cannot delete")
        return self.repo.delete(domain_id)
