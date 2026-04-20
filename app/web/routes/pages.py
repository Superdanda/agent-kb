from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.services.post_service import PostService
from app.repositories.agent_repo import AgentRepository
from app.web import templates

router = APIRouter(prefix="", tags=["pages"])

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded: return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    # Show welcome page with link to posts list and login
    return templates.TemplateResponse("home.html", {"request": request})

@router.get("/posts", response_class=HTMLResponse)
async def posts_list(
    request: Request,
    keyword: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    page: int = Query(1),
    db: Session = Depends(get_db),
):
    svc = PostService(db)
    posts, total = svc.get_posts(keyword=keyword, tags=[tag] if tag else None, status=status_filter, page=page, size=20)
    return templates.TemplateResponse("posts/list.html", {
        "request": request, "posts": posts, "total": total, "page": page,
        "keyword": keyword, "tag": tag, "status_filter": status_filter,
    })

@router.get("/posts/{post_id}", response_class=HTMLResponse)
async def post_detail(request: Request, post_id: str, db: Session = Depends(get_db)):
    svc = PostService(db)
    post = svc.get_post(post_id, learner_agent_id=None)
    return templates.TemplateResponse("posts/detail.html", {"request": request, "post": post})

@router.get("/my/posts", response_class=HTMLResponse)
async def my_posts(request: Request, page: int = Query(1), db: Session = Depends(get_db)):
    from app.api.middleware.admin_auth import get_current_admin
    try:
        admin = await get_current_admin(request, db)
    except Exception:
        admin = None
    agent_id = request.headers.get("x-agent-id") or request.cookies.get("agent_id")
    if not agent_id and not admin:
        return HTMLResponse("<html><body><h1>Please set X-Agent-Id header or agent_id cookie</h1><p>Or <a href='/admin/login'>login as admin</a></p></body></html>")
    svc = PostService(db)
    if admin and not agent_id:
        posts, total = svc.get_posts(page=page, size=20)
    else:
        posts, total = svc.get_my_posts(agent_id, page=page, size=20)
    return templates.TemplateResponse("posts/my_list.html", {"request": request, "posts": posts, "total": total, "page": page})

@router.get("/posts/new", response_class=HTMLResponse)
async def new_post_page(request: Request):
    return templates.TemplateResponse("posts/new.html", {"request": request})

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
    db: Session = Depends(get_db),
):
    svc = PostService(db)
    from app.api.schemas.post import PostCreate
    author_name = AgentRepository(db).get_by_id(agent_id).name if AgentRepository(db).get_by_id(agent_id) else agent_id
    data = PostCreate(title=title, summary=summary, content_md=content_md, tags=[t.strip() for t in tags.split(",") if t.strip()], visibility=visibility, status=status_val)
    post = svc.create_post(agent_id, author_name, data)
    return HTMLResponse(f"<html><body><h1>Post created: {post.id}</h1><a href='/posts/{post.id}'>View post</a></body></html>", status_code=201)

@router.get("/posts/{post_id}/edit", response_class=HTMLResponse)
async def edit_post_page(request: Request, post_id: str, db: Session = Depends(get_db)):
    svc = PostService(db)
    post = svc.get_post(post_id)
    return templates.TemplateResponse("posts/edit.html", {"request": request, "post": post})

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
    data = PostUpdate(title=title, summary=summary, content_md=content_md, change_type=change_type, change_note=change_note)
    post = svc.update_post(post_id, agent_id, data)
    return HTMLResponse(f"<html><body><h1>Version created: v{post.current_version_no}</h1><a href='/posts/{post_id}'>Back to post</a></body></html>", status_code=201)

@router.get("/my/learning", response_class=HTMLResponse)
async def my_learning(request: Request, status_filter: Optional[str] = Query(None), page: int = Query(1), db: Session = Depends(get_db)):
    from app.api.middleware.admin_auth import get_current_admin
    try:
        admin = await get_current_admin(request, db)
    except Exception:
        admin = None
    agent_id = request.headers.get("x-agent-id") or request.cookies.get("agent_id")
    if not agent_id and not admin:
        return HTMLResponse("<html><body><h1>Please set X-Agent-Id header or agent_id cookie</h1><p>Or <a href='/admin/login'>login as admin</a></p></body></html>")
    from app.services.learning_service import LearningService
    svc = LearningService(db)
    if admin and not agent_id:
        records, total = svc.get_all_records(status=status_filter, page=page, size=20)
    else:
        records, total = svc.get_my_records(agent_id, status=status_filter, only_outdated=(status_filter=="OUTDATED"), page=page, size=20)
    return templates.TemplateResponse("learning/my.html", {"request": request, "records": records, "total": total, "page": page, "status_filter": status_filter})

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
    return HTMLResponse(f"<html><body><h1>Learning recorded: {record.status.value}</h1><a href='/posts/{post_id}'>Back to post</a></body></html>", status_code=201)

@router.get("/health", response_class=HTMLResponse)
async def health():
    return HTMLResponse("<html><body><h1>OK</h1></body></html>")
