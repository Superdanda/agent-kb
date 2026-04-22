from fastapi import APIRouter, Request, Depends, Form, Query, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.services.post_service import PostService
from app.services.domain_service import DomainService
from app.services.skill_service import SkillService
from app.repositories.agent_repo import AgentRepository
from app.models.admin_user import AdminUser
from app.web import templates

router = APIRouter(prefix="", tags=["pages"])


def _parse_tag_query(tag_value: Optional[str]) -> list[str]:
    if not tag_value:
        return []
    return [item.strip() for item in tag_value.split(",") if item.strip()]


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("home.html", {"request": request})


@router.get("/posts", response_class=HTMLResponse)
async def posts_list(
    request: Request,
    keyword: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    domain_id: Optional[str] = Query(None),
    page: int = Query(1),
    db: Session = Depends(get_db),
):
    svc = PostService(db)
    domain_svc = DomainService(db)
    posts, total = svc.get_posts(
        keyword=keyword, tags=[tag] if tag else None,
        status=status_filter, domain_id=domain_id, page=page, size=20
    )
    domains = domain_svc.get_all_domains(include_inactive=False)
    return templates.TemplateResponse("posts/list.html", {
        "request": request, "posts": posts, "total": total, "page": page,
        "keyword": keyword, "tag": tag, "status_filter": status_filter,
        "domain_id": domain_id, "domains": domains,
    })


@router.get("/posts/new", response_class=HTMLResponse)
async def new_post_page(request: Request, db: Session = Depends(get_db)):
    domain_svc = DomainService(db)
    domains = domain_svc.get_all_domains(include_inactive=False)
    return templates.TemplateResponse("posts/new.html", {"request": request, "domains": domains})


@router.post("/posts/new")
async def create_post(
    request: Request,
    title: str = Form(...),
    summary: str = Form(""),
    content_md: str = Form(""),
    tags: str = Form(""),
    visibility: str = Form("PUBLIC_INTERNAL"),
    status_val: str = Form("DRAFT"),
    agent_id: str = Form(...),
    domain_id: str = Form(""),
    db: Session = Depends(get_db),
):
    svc = PostService(db)
    from app.api.schemas.post import PostCreate
    author_name = AgentRepository(db).get_by_id(agent_id).name if AgentRepository(db).get_by_id(agent_id) else agent_id
    data = PostCreate(
        title=title, summary=summary, content_md=content_md,
        tags=[t.strip() for t in tags.split(",") if t.strip()],
        visibility=visibility, status=status_val,
        domain_id=domain_id if domain_id else None
    )
    post = svc.create_post(agent_id, author_name, data)
    return HTMLResponse(
        f"<html><body><h1>Post created: {post.id}</h1><a href='/posts/{post.id}'>View post</a></body></html>",
        status_code=201
    )


@router.get("/posts/{post_id}", response_class=HTMLResponse)
async def post_detail(request: Request, post_id: str, db: Session = Depends(get_db)):
    svc = PostService(db)
    post = svc.get_post(post_id, learner_agent_id=None)
    return templates.TemplateResponse("posts/detail.html", {"request": request, "post": post})


@router.get("/posts/{post_id}/edit", response_class=HTMLResponse)
async def edit_post_page(request: Request, post_id: str, db: Session = Depends(get_db)):
    svc = PostService(db)
    domain_svc = DomainService(db)
    post = svc.get_post(post_id)
    domains = domain_svc.get_all_domains(include_inactive=False)
    return templates.TemplateResponse("posts/edit.html", {"request": request, "post": post, "domains": domains})


@router.post("/posts/{post_id}/versions")
async def create_version(
    request: Request,
    post_id: str,
    title: str = Form(...),
    summary: str = Form(""),
    content_md: str = Form(""),
    change_type: str = Form("MINOR"),
    change_note: str = Form(""),
    agent_id: str = Form(...),
    db: Session = Depends(get_db),
):
    svc = PostService(db)
    from app.api.schemas.post import PostUpdate
    data = PostUpdate(
        title=title, summary=summary, content_md=content_md,
        change_type=change_type, change_note=change_note
    )
    post = svc.update_post(post_id, agent_id, data)
    return HTMLResponse(
        f"<html><body><h1>Version created: v{post.current_version_no}</h1><a href='/posts/{post_id}'>Back to post</a></body></html>",
        status_code=201
    )


@router.get("/my/posts", response_class=HTMLResponse)
async def my_posts(request: Request, page: int = Query(1), db: Session = Depends(get_db)):
    from fastapi.responses import RedirectResponse
    from app.api.middleware.admin_auth import get_current_admin
    try:
        admin = await get_current_admin(request, db)
    except Exception:
        admin = None
    agent_id = request.headers.get("x-agent-id") or request.cookies.get("agent_id")
    if not agent_id and not admin:
        return RedirectResponse(url="/admin/login", status_code=302)
    svc = PostService(db)
    domain_svc = DomainService(db)
    if admin and not agent_id:
        posts, total = svc.get_posts(page=page, size=20)
    else:
        posts, total = svc.get_my_posts(agent_id, page=page, size=20)
    domains = domain_svc.get_all_domains(include_inactive=False)
    return templates.TemplateResponse("posts/my_list.html", {"request": request, "posts": posts, "total": total, "page": page, "domains": domains})


@router.get("/my/learning", response_class=HTMLResponse)
async def my_learning(request: Request, status_filter: Optional[str] = Query(None), page: int = Query(1), db: Session = Depends(get_db)):
    from fastapi.responses import RedirectResponse
    from app.api.middleware.admin_auth import get_current_admin
    try:
        admin = await get_current_admin(request, db)
    except Exception:
        admin = None
    agent_id = request.headers.get("x-agent-id") or request.cookies.get("agent_id")
    if not agent_id and not admin:
        return RedirectResponse(url="/admin/login", status_code=302)
    from app.services.learning_service import LearningService
    svc = LearningService(db)
    if admin and not agent_id:
        records, total = svc.get_all_records(status=status_filter, page=page, size=20)
    else:
        records, total = svc.get_my_records(agent_id, status=status_filter, only_outdated=(status_filter == "OUTDATED"), page=page, size=20)
    return templates.TemplateResponse("learning/my.html", {"request": request, "records": records, "total": total, "page": page, "status_filter": status_filter})


@router.get("/skills", response_class=HTMLResponse)
async def skills_list(
    request: Request,
    keyword: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    uploader_agent_id: Optional[str] = Query(None),
    recommended_only: bool = Query(False),
    official_only: bool = Query(False),
    important_only: bool = Query(False),
    page: int = Query(1),
    db: Session = Depends(get_db),
):
    svc = SkillService(db)
    skills, total = svc.list_skills(
        keyword=keyword,
        tags=_parse_tag_query(tag) or None,
        uploader_agent_id=uploader_agent_id,
        recommended_only=recommended_only,
        official_only=official_only,
        important_only=important_only,
        page=page,
        size=20,
    )
    return templates.TemplateResponse("skills/list.html", {
        "request": request,
        "skills": skills,
        "total": total,
        "page": page,
        "keyword": keyword or "",
        "tag": tag or "",
        "uploader_agent_id": uploader_agent_id or "",
        "recommended_only": recommended_only,
        "official_only": official_only,
        "important_only": important_only,
    })


@router.get("/skills/upload", response_class=HTMLResponse)
async def skill_upload_page(request: Request, db: Session = Depends(get_db)):
    from app.api.middleware.admin_auth import get_current_admin
    try:
        admin = await get_current_admin(request, db)
    except Exception:
        admin = None
    return templates.TemplateResponse("skills/upload.html", {"request": request, "admin": admin})


@router.post("/skills/upload")
async def upload_skill_from_page(
    request: Request,
    file: UploadFile = File(...),
    release_note: str = Form(""),
    agent_id: str = Form(""),
    db: Session = Depends(get_db),
):
    from app.api.middleware.admin_auth import get_current_admin
    try:
        admin = await get_current_admin(request, db)
    except Exception:
        admin = None

    skill, _ = SkillService(db).upload_skill_package(
        file=file,
        uploader_agent_id=agent_id or None,
        uploader_admin_uuid=admin.uuid if admin and not agent_id else None,
        release_note=release_note or None,
    )
    return RedirectResponse(url=f"/skills/{skill.id}", status_code=302)


@router.get("/skills/{skill_id}", response_class=HTMLResponse)
async def skill_detail(request: Request, skill_id: str, db: Session = Depends(get_db)):
    skill = SkillService(db).get_skill(skill_id)
    return templates.TemplateResponse("skills/detail.html", {"request": request, "skill": skill})


@router.get("/skills/{skill_id}/download")
async def skill_download_page(skill_id: str, db: Session = Depends(get_db)):
    data, filename, mime_type = SkillService(db).download_skill_latest(skill_id)
    return Response(
        content=data,
        media_type=mime_type,
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


@router.get("/skills/versions/{version_id}/download")
async def skill_version_download_page(version_id: str, db: Session = Depends(get_db)):
    data, filename, mime_type = SkillService(db).download_skill_version(version_id)
    return Response(
        content=data,
        media_type=mime_type,
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


@router.post("/posts/{post_id}/learn")
async def submit_learning(
    request: Request,
    post_id: str,
    version_id: str = Form(...),
    learn_note: str = Form(""),
    agent_id: str = Form(...),
    db: Session = Depends(get_db),
):
    from app.services.learning_service import LearningService
    from app.api.schemas.learning import LearningSubmit
    svc = LearningService(db)
    data = LearningSubmit(version_id=version_id, learn_note=learn_note)
    record = svc.submit_learning(agent_id, post_id, data)
    return HTMLResponse(
        f"<html><body><h1>Learning recorded: {record.status.value}</h1><a href='/posts/{post_id}'>Back to post</a></body></html>",
        status_code=201
    )


@router.get("/tasks", response_class=HTMLResponse)
async def tasks_page(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    page: int = Query(1),
    size: int = Query(20),
    db: Session = Depends(get_db),
):
    from fastapi.responses import RedirectResponse
    from app.api.middleware.admin_auth import get_current_admin
    try:
        admin = await get_current_admin(request, db)
    except Exception:
        admin = None
    agent_id = request.headers.get("x-agent-id") or request.cookies.get("agent_id")
    if not agent_id and not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    from app.modules.task_board.models.task import Task, TaskStatus, TaskPriority
    query = db.query(Task)
    if status_filter:
        query = query.filter(Task.status == TaskStatus(status_filter))
    if priority:
        query = query.filter(Task.priority == TaskPriority(priority))
    total = query.count()
    tasks = query.order_by(Task.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return templates.TemplateResponse("tasks/list.html", {
        "request": request,
        "tasks": tasks,
        "total": total,
        "page": page,
        "size": size,
        "status_filter": status_filter,
        "priority": priority,
        "is_admin": admin is not None,
    })


@router.get("/tasks/new", response_class=HTMLResponse)
async def new_task_page(
    request: Request,
    db: Session = Depends(get_db),
):
    from fastapi.responses import RedirectResponse
    from app.api.middleware.admin_auth import get_current_admin
    try:
        admin = await get_current_admin(request, db)
    except Exception:
        return RedirectResponse(url="/admin/login", status_code=302)

    from app.modules.task_board.models.task import TaskPriority, TaskDifficulty
    from app.models.agent import Agent
    agents = db.query(Agent).order_by(Agent.name).all()
    return templates.TemplateResponse("tasks/new.html", {
        "request": request,
        "priorities": list(TaskPriority),
        "difficulties": list(TaskDifficulty),
        "agents": agents,
    })


@router.get("/tasks/{task_id}", response_class=HTMLResponse)
async def task_detail_page(
    request: Request,
    task_id: str,
    db: Session = Depends(get_db),
):
    from fastapi.responses import RedirectResponse
    from app.api.middleware.admin_auth import get_current_admin
    from app.modules.task_board.models.task import Task
    from app.modules.task_board.models.task_status_log import TaskStatusLog
    from app.modules.task_board.models.task_rating import TaskRating
    from app.modules.task_board.models.task_material import TaskMaterial

    try:
        admin = await get_current_admin(request, db)
    except Exception:
        admin = None

    agent_id = request.headers.get("x-agent-id") or request.cookies.get("agent_id")
    if not agent_id and not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return HTMLResponse("<html><body><h1>Task not found</h1><a href='/tasks'>Back to tasks</a></body></html>", status_code=404)

    creator_label = "系统"
    if task.created_by:
        creator_label = task.created_by.name
    elif task.created_by_admin_uuid:
        admin_user = db.query(AdminUser).filter(AdminUser.uuid == task.created_by_admin_uuid).first()
        creator_label = admin_user.username if admin_user else f"管理员 {task.created_by_admin_uuid}"

    logs = (
        db.query(TaskStatusLog)
        .filter(TaskStatusLog.task_id == task.id)
        .order_by(TaskStatusLog.created_at.desc())
        .all()
    )
    ratings = (
        db.query(TaskRating)
        .filter(TaskRating.task_id == task.id)
        .order_by(TaskRating.created_at.desc())
        .all()
    )
    materials = (
        db.query(TaskMaterial)
        .filter(TaskMaterial.task_id == task.id)
        .order_by(TaskMaterial.created_at.desc())
        .all()
    )

    return templates.TemplateResponse("tasks/detail.html", {
        "request": request,
        "task": task,
        "creator_label": creator_label,
        "logs": logs,
        "ratings": ratings,
        "materials": materials,
        "is_admin": admin is not None,
    })


@router.post("/tasks/new")
async def create_task(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    priority: str = Form("MEDIUM"),
    difficulty: str = Form(""),
    assigned_to_agent_code: str = Form(""),
    points: int = Form(0),
    estimated_hours: int = Form(0),
    due_date: str = Form(""),
    tags: str = Form(""),
    db: Session = Depends(get_db),
):
    from fastapi.responses import RedirectResponse
    from app.api.middleware.admin_auth import get_current_admin
    try:
        admin = await get_current_admin(request, db)
    except Exception:
        return RedirectResponse(url="/admin/login", status_code=302)

    from app.modules.task_board.models.task import TaskPriority, TaskDifficulty, TaskStatus
    from app.models.agent import Agent
    from app.modules.task_board.services.task_service import TaskService

    # Resolve agent_code to agent_id if provided
    assigned_to_agent_id = None
    if assigned_to_agent_code:
        agent = db.query(Agent).filter(Agent.agent_code == assigned_to_agent_code).first()
        if agent:
            assigned_to_agent_id = agent.id

    # Parse difficulty
    task_difficulty = None
    if difficulty:
        try:
            task_difficulty = TaskDifficulty(difficulty)
        except ValueError:
            pass

    # Parse due date
    task_due_date = None
    if due_date:
        from datetime import datetime
        try:
            task_due_date = datetime.fromisoformat(due_date)
        except ValueError:
            pass

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    svc = TaskService(db)
    task = svc.create_task(
        title=title,
        created_by_admin_uuid=admin.uuid,  # Admin's UUID
        description=description if description else None,
        assigned_to_agent_id=assigned_to_agent_id,
        priority=TaskPriority(priority),
        difficulty=task_difficulty,
        points=points,
        estimated_hours=estimated_hours if estimated_hours else None,
        due_date=task_due_date,
        tags=tag_list if tag_list else None,
    )

    return RedirectResponse(url=f"/tasks/new?task_id={task.id}", status_code=302)


@router.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(
    request: Request,
    period: Optional[str] = Query("WEEKLY"),
    limit: int = Query(20),
    db: Session = Depends(get_db),
):
    from fastapi.responses import RedirectResponse
    from app.api.middleware.admin_auth import get_current_admin
    try:
        admin = await get_current_admin(request, db)
    except Exception:
        admin = None
    agent_id = request.headers.get("x-agent-id") or request.cookies.get("agent_id")
    if not agent_id and not admin:
        return RedirectResponse(url="/admin/login", status_code=302)

    from app.modules.task_board.models.leaderboard import LeaderboardPeriod
    from app.modules.task_board.services.leaderboard_service import LeaderboardService
    svc = LeaderboardService(db)
    try:
        period_enum = LeaderboardPeriod(period)
    except Exception:
        period_enum = LeaderboardPeriod.WEEKLY
    entries = svc.get_leaderboard_simple(period=period_enum, limit=limit)
    return templates.TemplateResponse("leaderboard/page.html", {
        "request": request,
        "entries": entries,
        "period": period_enum.value,
        "periods": [p.value for p in LeaderboardPeriod],
    })


@router.get("/register", response_class=HTMLResponse)
async def agent_register_page(request: Request):
    """Agent self-registration page."""
    return templates.TemplateResponse("agent/register.html", {"request": request})


@router.get("/health", response_class=HTMLResponse)
async def health():
    return HTMLResponse("<html><body><h1>OK</h1></body></html>")
