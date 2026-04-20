from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.models.agent import Agent
from app.models.post import Post
from app.models.post_version import PostVersion
from app.models.learning_record import LearningRecord, LearningStatus
from app.api.middleware.admin_auth import get_current_admin
from app.web import templates


router = APIRouter(prefix="/admin", tags=["admin_pages"])


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def get_optional_admin(
    request: Request,
    db: Session = Depends(get_db),
) -> AdminUser | None:
    try:
        return await get_current_admin(request, db)
    except HTTPException:
        return None


@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request, db: Session = Depends(get_db)):
    # If already logged in, redirect to dashboard
    admin = await get_optional_admin(request, db)
    if admin:
        return RedirectResponse(url="/admin/dashboard", status_code=302)

    return templates.TemplateResponse("admin/login.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    admin = await get_current_admin(request, db)

    total_posts = db.query(func.count(Post.id)).scalar() or 0
    total_agents = db.query(func.count(Agent.id)).scalar() or 0
    total_learning_records = db.query(func.count(LearningRecord.id)).scalar() or 0
    outdated_records = db.query(func.count(LearningRecord.id)).filter(
        LearningRecord.status == LearningStatus.OUTDATED
    ).scalar() or 0

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "total_posts": total_posts,
        "total_agents": total_agents,
        "total_learning_records": total_learning_records,
        "outdated_records": outdated_records,
    })


@router.get("/agents", response_class=HTMLResponse)
async def admin_agents(request: Request, db: Session = Depends(get_db)):
    await get_current_admin(request, db)
    agents = db.query(Agent).order_by(Agent.created_at.desc()).all()
    return templates.TemplateResponse("admin/agents.html", {
        "request": request,
        "agents": agents,
    })


@router.get("/posts", response_class=HTMLResponse)
async def admin_posts(request: Request, db: Session = Depends(get_db)):
    await get_current_admin(request, db)

    posts = db.query(Post).order_by(Post.created_at.desc()).all()
    posts_list = []
    for post in posts:
        version_count = db.query(func.count(PostVersion.id)).filter(
            PostVersion.post_id == post.id
        ).scalar() or 0
        current_version = (
            db.query(PostVersion)
            .filter(
                PostVersion.post_id == post.id,
                PostVersion.version_no == post.current_version_no
            )
            .first()
        )
        posts_list.append({
            "post": post,
            "version_count": version_count,
            "current_version": current_version,
        })

    return templates.TemplateResponse("admin/posts.html", {
        "request": request,
        "posts_data": posts_list,
    })


@router.get("/learning-records", response_class=HTMLResponse)
async def admin_learning_records(request: Request, db: Session = Depends(get_db)):
    await get_current_admin(request, db)

    records = (
        db.query(LearningRecord)
        .order_by(LearningRecord.learned_at.desc())
        .all()
    )

    return templates.TemplateResponse("admin/learning_records.html", {
        "request": request,
        "records": records,
    })
