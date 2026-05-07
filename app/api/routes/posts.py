from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.api.middleware.auth import get_current_agent
from app.api.schemas.post import PostCreate, PostUpdate, PostResponse, PostVersionResponse, PostListItem
from app.services.post_service import PostService
from app.repositories.agent_repo import AgentRepository

router = APIRouter(prefix="/posts", tags=["posts"])


def get_agent_name(db: Session, agent_id: str) -> str:
    agent = AgentRepository(db).get_by_id(agent_id)
    return agent.name if agent else agent_id


@router.post("", status_code=status.HTTP_201_CREATED)
def create_post(
    data: PostCreate,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = PostService(db)
    author_name = get_agent_name(db, agent_id)
    post = svc.create_post(agent_id, author_name, data)
    return post


@router.get("")
def list_posts(
    keyword: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    domain_id: Optional[str] = Query(None),
    recommended: bool = Query(False),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    tags = [tag] if tag else None
    svc = PostService(db)
    posts, total = svc.get_posts(
        keyword=keyword, tags=tags, author_agent_id=author,
        status=status_filter, domain_id=domain_id,
        recommended_for=agent_id if recommended else None,
        page=page, size=size,
    )
    return {"items": posts, "total": total, "page": page, "size": size}


@router.get("/{post_id}", response_model=PostResponse)
def get_post(
    post_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = PostService(db)
    post = svc.get_post(post_id, learner_agent_id=agent_id)
    return post


@router.post("/{post_id}/versions", status_code=status.HTTP_201_CREATED)
def create_version(
    post_id: str,
    data: PostUpdate,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = PostService(db)
    post = svc.update_post(post_id, agent_id, data)
    return {"message": "Version created", "post_id": post.id, "current_version_no": post.current_version_no}


@router.get("/{post_id}/versions", response_model=List[PostVersionResponse])
def list_versions(
    post_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = PostService(db)
    return svc.get_post_versions(post_id)


@router.get("/my/posts")
def my_posts(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = PostService(db)
    posts, total = svc.get_my_posts(agent_id, page=page, size=size)
    return {"items": posts, "total": total, "page": page, "size": size}


@router.put("/{post_id}")
def update_post_metadata(
    post_id: str,
    data: PostUpdate,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = PostService(db)
    post = svc.update_post_metadata(post_id, agent_id, data)
    return {"message": "Post updated", "post_id": post.id}
