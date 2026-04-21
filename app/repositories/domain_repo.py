from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.knowledge_domain import KnowledgeDomain


class DomainRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, domain_id: str) -> KnowledgeDomain | None:
        return self.db.query(KnowledgeDomain).filter(KnowledgeDomain.id == domain_id).first()

    def get_by_code(self, code: str) -> KnowledgeDomain | None:
        return self.db.query(KnowledgeDomain).filter(KnowledgeDomain.code == code).first()

    def get_all(self, include_inactive: bool = False) -> List[KnowledgeDomain]:
        query = self.db.query(KnowledgeDomain)
        if not include_inactive:
            query = query.filter(KnowledgeDomain.is_active == True)
        return query.order_by(KnowledgeDomain.sort_order.asc()).all()

    def create(
        self,
        code: str,
        name: str,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        sort_order: int = 0,
    ) -> KnowledgeDomain:
        domain = KnowledgeDomain(
            code=code,
            name=name,
            description=description,
            icon=icon,
            color=color,
            sort_order=sort_order,
        )
        self.db.add(domain)
        self.db.commit()
        self.db.refresh(domain)
        return domain

    def update(
        self,
        domain_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        sort_order: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> KnowledgeDomain | None:
        domain = self.get_by_id(domain_id)
        if not domain:
            return None
        if name is not None:
            domain.name = name
        if description is not None:
            domain.description = description
        if icon is not None:
            domain.icon = icon
        if color is not None:
            domain.color = color
        if sort_order is not None:
            domain.sort_order = sort_order
        if is_active is not None:
            domain.is_active = is_active
        self.db.commit()
        self.db.refresh(domain)
        return domain

    def delete(self, domain_id: str) -> bool:
        domain = self.get_by_id(domain_id)
        if not domain:
            return False
        self.db.delete(domain)
        self.db.commit()
        return True
