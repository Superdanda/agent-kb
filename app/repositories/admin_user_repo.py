from sqlalchemy.orm import Session

from app.models.admin_user import AdminUser


class AdminUserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, admin: AdminUser) -> AdminUser:
        self.db.add(admin)
        self.db.commit()
        self.db.refresh(admin)
        return admin

    def get_by_id(self, admin_id: int) -> AdminUser | None:
        return self.db.query(AdminUser).filter(AdminUser.id == admin_id).first()

    def get_by_uuid(self, admin_uuid: str) -> AdminUser | None:
        return self.db.query(AdminUser).filter(AdminUser.uuid == admin_uuid).first()

    def get_by_username(self, username: str) -> AdminUser | None:
        return self.db.query(AdminUser).filter(AdminUser.username == username).first()

    def list(self, *, page: int = 1, size: int = 20, keyword: str | None = None) -> tuple[list[AdminUser], int]:
        query = self.db.query(AdminUser)
        if keyword:
            pattern = f"%{keyword}%"
            query = query.filter(
                (AdminUser.username.ilike(pattern))
                | (AdminUser.nickname.ilike(pattern))
                | (AdminUser.email.ilike(pattern))
                | (AdminUser.phone.ilike(pattern))
            )
        total = query.count()
        admins = (
            query.order_by(AdminUser.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        return admins, total
