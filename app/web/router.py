"""Server-rendered web pages."""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(tags=["web"])


@router.get("/")
def index() -> RedirectResponse:
    """Redirect root page to dashboard."""

    return RedirectResponse(url="/dashboard")


@router.get("/login")
def login_page(request: Request):
    """Render login page."""

    return templates.TemplateResponse(request, "login.html")


@router.get("/dashboard")
def dashboard_page(request: Request):
    """Render dashboard map page."""

    return templates.TemplateResponse(request, "dashboard.html")


@router.get("/planner")
def planner_page(request: Request):
    """Render transmission planner page."""

    return templates.TemplateResponse(request, "planner.html")


@router.get("/terminals/{terminal_id}/view")
def terminal_detail_page(request: Request, terminal_id: int):
    """Render terminal detail page."""

    return templates.TemplateResponse(
        request,
        "terminal_detail.html",
        {"terminal_id": terminal_id},
    )
