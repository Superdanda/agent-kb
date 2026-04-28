from fastapi import APIRouter, Request, Depends, HTTPException, status, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.models.agent import Agent, AgentStatus
from app.models.post import Post
from app.models.post_version import PostVersion
from app.models.skill import Skill
from app.models.learning_record import LearningRecord, LearningStatus
from app.api.middleware.admin_auth import get_current_admin
from app.services.domain_service import DomainService
from app.services.skill_service import SkillService
from app.services.admin_user_service import AdminUserService
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
    total_skills = db.query(func.count(Skill.id)).scalar() or 0
    total_agents = db.query(func.count(Agent.id)).scalar() or 0
    total_learning_records = db.query(func.count(LearningRecord.id)).scalar() or 0
    outdated_records = db.query(func.count(LearningRecord.id)).filter(
        LearningRecord.status == LearningStatus.OUTDATED
    ).scalar() or 0

    from app.services.agent_registration_service import AgentRegistrationService
    from app.models.agent_registration import RegistrationStatus
    reg_svc = AgentRegistrationService(db)
    pending_registrations = len(reg_svc.list_all(RegistrationStatus.PENDING)[0])

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "total_posts": total_posts,
        "total_skills": total_skills,
        "total_agents": total_agents,
        "total_learning_records": total_learning_records,
        "outdated_records": outdated_records,
        "pending_registrations": pending_registrations,
    })


@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    page: int = Query(1, ge=1),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    current_admin = await get_current_admin(request, db)
    page_size = 20
    admins, total = AdminUserService(db).list_admins(page=page, size=page_size, keyword=keyword)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "admins": admins,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "keyword": keyword or "",
        "current_admin": current_admin,
    })


@router.get("/agents", response_class=HTMLResponse)
async def admin_agents(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    await get_current_admin(request, db)

    query = db.query(Agent)

    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Agent.name.ilike(search_term)) |
            (Agent.agent_code.ilike(search_term)) |
            (Agent.agent_type.ilike(search_term)) |
            (Agent.device_name.ilike(search_term))
        )

    # Apply status filter
    if status_filter:
        try:
            status_enum = AgentStatus(status_filter.upper())
            query = query.filter(Agent.status == status_enum)
        except ValueError:
            pass

    # Get total count for stats
    total_agents = db.query(Agent).count()
    total_active = db.query(Agent).filter(Agent.status == AgentStatus.ACTIVE).count()
    total_inactive = db.query(Agent).filter(Agent.status == AgentStatus.INACTIVE).count()

    # Get total count after filters
    total = query.count()

    # Calculate pagination
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    offset = (page - 1) * per_page

    # Get paginated results
    agents = query.order_by(Agent.created_at.desc()).offset(offset).limit(per_page).all()

    return templates.TemplateResponse("admin/agents.html", {
        "request": request,
        "agents": agents,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "search": search or "",
        "status_filter": status_filter or "",
        "total_agents": total_agents,
        "total_active": total_active,
        "total_inactive": total_inactive,
    })


@router.get("/agents/{agent_id}/edit", response_class=HTMLResponse)
async def admin_agent_edit(request: Request, agent_id: str, db: Session = Depends(get_db)):
    await get_current_admin(request, db)
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"detail": "Agent not found"})
    return templates.TemplateResponse("admin/agent_edit.html", {
        "request": request,
        "agent": agent,
    })


@router.get("/posts", response_class=HTMLResponse)
async def admin_posts(request: Request, domain_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    await get_current_admin(request, db)
    domain_svc = DomainService(db)

    query = db.query(Post).order_by(Post.created_at.desc())
    if domain_id:
        query = query.filter(Post.domain_id == domain_id)
    posts = query.all()

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

    domains = domain_svc.get_all_domains(include_inactive=False)
    return templates.TemplateResponse("admin/posts.html", {
        "request": request,
        "posts_data": posts_list,
        "domains": domains,
        "domain_id": domain_id,
    })


@router.get("/registration-requests", response_class=HTMLResponse)
async def admin_registration_requests(
    request: Request,
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    await get_current_admin(request, db)
    from app.services.agent_registration_service import AgentRegistrationService
    from app.models.agent_registration import RegistrationStatus

    svc = AgentRegistrationService(db)

    status_enum = None
    if status_filter:
        try:
            status_enum = RegistrationStatus(status_filter.upper())
        except ValueError:
            pass

    page_size = 20
    requests, total = svc.list_all(status_enum, page, page_size)
    pending_list, pending_count = svc.list_all(RegistrationStatus.PENDING)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return templates.TemplateResponse("admin/registration_requests.html", {
        "request": request,
        "requests": requests,
        "total": total,
        "status_filter": status_filter or "",
        "pending_count": pending_count,
        "page": page,
        "total_pages": total_pages,
        "page_size": page_size,
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


@router.get("/skills", response_class=HTMLResponse)
async def admin_skills(
    request: Request,
    keyword: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    await get_current_admin(request, db)
    svc = SkillService(db)
    skills, total = svc.list_skills(
        keyword=keyword,
        tags=[item.strip() for item in (tag or "").split(",") if item.strip()] or None,
        status_value=status_filter or None,
        include_hidden=True,
        page=page,
        size=20,
    )
    return templates.TemplateResponse("admin/skills.html", {
        "request": request,
        "skills": skills,
        "total": total,
        "page": page,
        "keyword": keyword or "",
        "tag": tag or "",
        "status_filter": status_filter or "",
    })


@router.post("/skills/{skill_id}/flags")
async def admin_skill_flags(
    request: Request,
    skill_id: str,
    is_recommended: Optional[str] = Form(None),
    is_important: Optional[str] = Form(None),
    is_official: Optional[str] = Form(None),
    status_value: str = Form("ACTIVE"),
    db: Session = Depends(get_db),
):
    await get_current_admin(request, db)
    SkillService(db).update_skill_admin(
        skill_id,
        is_recommended=is_recommended == "on",
        is_important=is_important == "on",
        is_official=is_official == "on",
        status=status_value,
    )
    return RedirectResponse(url="/admin/skills", status_code=302)


@router.post("/skills/versions/{version_id}/status")
async def admin_skill_version_status(
    request: Request,
    version_id: str,
    status_value: str = Form(...),
    db: Session = Depends(get_db),
):
    await get_current_admin(request, db)
    SkillService(db).update_version_status(version_id, status_value)
    return RedirectResponse(url="/admin/skills", status_code=302)
