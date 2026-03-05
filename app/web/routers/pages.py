from pathlib import Path
import shutil
import tempfile
import zipfile
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.conversion_service import convert_file
from app.web.auth import (
    SESSION_COOKIE_NAME,
    create_session_token,
    get_current_user,
    get_optional_current_user,
    hash_password,
    require_admin,
    verify_password,
)
from app.web.db import get_db
from app.web.models import ConversionJob, User


router = APIRouter()

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/", response_class=HTMLResponse, tags=["pages"])
def index(request: Request, current_user: User | None = Depends(get_optional_current_user)) -> Response:
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"page_title": "Monitor Import", "current_user": current_user},
    )


def _cleanup_temp_dir(path: str) -> None:
    shutil.rmtree(path, ignore_errors=True)


def _render_admin_page(
    request: Request,
    current_admin: User,
    db: Session,
    error: str = "",
    success: str = "",
    status_code: int = 200,
) -> HTMLResponse:
    users = db.scalars(select(User).order_by(User.username.asc())).all()
    jobs = db.scalars(select(ConversionJob).order_by(desc(ConversionJob.created_at)).limit(25)).all()
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "page_title": "Admin",
            "current_user": current_admin,
            "users": users,
            "jobs": jobs,
            "error": error,
            "success": success,
        },
        status_code=status_code,
    )


@router.post("/convert", tags=["pages"])
def convert(
    request: Request,
    file: UploadFile = File(...),
    base_name: str = Form(""),
    dedup_mode: str = Form("skip"),
    existing_materials_file: UploadFile | None = File(default=None),
    current_user: User = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file name")

    source_name = Path(file.filename).name
    if Path(source_name).suffix.lower() != ".csv":
        raise HTTPException(status_code=400, detail="Only .csv files are supported")

    temp_dir = tempfile.mkdtemp(prefix="monitor_import_")
    temp_path = Path(temp_dir)
    input_path = temp_path / source_name
    out_dir = temp_path / "out"

    with input_path.open("wb") as target:
        shutil.copyfileobj(file.file, target)

    effective_base_name = (base_name or "").strip() or Path(source_name).stem
    dedup_mode = (dedup_mode or "skip").strip().lower()
    if dedup_mode not in {"skip", "sql", "existing-file"}:
        _cleanup_temp_dir(temp_dir)
        raise HTTPException(status_code=400, detail="Invalid dedup mode")

    existing_file_path: Path | None = None
    if dedup_mode == "existing-file":
        if existing_materials_file is None or not existing_materials_file.filename:
            _cleanup_temp_dir(temp_dir)
            raise HTTPException(status_code=400, detail="existing_materials_file is required for this mode")

        existing_name = Path(existing_materials_file.filename).name
        existing_file_path = temp_path / existing_name
        with existing_file_path.open("wb") as target:
            shutil.copyfileobj(existing_materials_file.file, target)
        existing_materials_file.file.close()

    job = ConversionJob(
        user_id=current_user.id,
        source_filename=source_name,
        base_name=effective_base_name,
        dedup_mode=dedup_mode,
        status="running",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        output_files = convert_file(
            input_csv=input_path,
            out_dir=out_dir,
            base_name=effective_base_name,
            existing_materials_file=str(existing_file_path) if existing_file_path else None,
            skip_material_dedup_query=(dedup_mode == "skip"),
        )
        zip_name = f"{effective_base_name}_converted.zip"
        job.status = "success"
        job.output_zip_name = zip_name
        job.finished_at = datetime.utcnow()
        db.commit()
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.finished_at = datetime.utcnow()
        db.commit()
        _cleanup_temp_dir(temp_dir)
        raise HTTPException(status_code=400, detail=f"Conversion failed: {exc}") from exc
    finally:
        file.file.close()
        if existing_materials_file is not None:
            existing_materials_file.file.close()

    zip_path = temp_path / zip_name
    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in (
            output_files.material_parts,
            output_files.parts,
            output_files.bom,
            output_files.purchase_raw,
        ):
            archive.write(path, arcname=path.name)

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=zip_name,
        background=BackgroundTask(_cleanup_temp_dir, temp_dir),
    )


@router.get("/login", response_class=HTMLResponse, tags=["pages"])
def login_page(
    request: Request,
    current_user: User | None = Depends(get_optional_current_user),
) -> Response:
    if current_user is not None:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"page_title": "Login", "current_user": None, "error": ""},
    )


@router.post("/login", tags=["pages"])
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
) -> Response:
    user = db.scalar(select(User).where(User.username == username.strip()))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"page_title": "Login", "current_user": None, "error": "Invalid username or password"},
            status_code=400,
        )

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(user.id),
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 12,
    )
    return response


@router.post("/logout", tags=["pages"])
def logout() -> RedirectResponse:
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@router.get("/profile", response_class=HTMLResponse, tags=["pages"])
def profile_page(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={"page_title": "Profile", "current_user": current_user, "error": "", "success": ""},
    )


@router.post("/profile/password", tags=["pages"])
def update_own_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    if not verify_password(current_password, current_user.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="profile.html",
            context={
                "page_title": "Profile",
                "current_user": current_user,
                "error": "Current password is incorrect",
                "success": "",
            },
            status_code=400,
        )

    normalized_password = new_password.strip()
    if len(normalized_password) < 4:
        return templates.TemplateResponse(
            request=request,
            name="profile.html",
            context={
                "page_title": "Profile",
                "current_user": current_user,
                "error": "New password must be at least 4 characters",
                "success": "",
            },
            status_code=400,
        )

    db_user = db.scalar(select(User).where(User.id == current_user.id))
    if db_user is None:
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie(SESSION_COOKIE_NAME)
        return response

    db_user.password_hash = hash_password(normalized_password)
    db.commit()
    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "page_title": "Profile",
            "current_user": db_user,
            "error": "",
            "success": "Password updated",
        },
    )


@router.get("/admin", response_class=HTMLResponse, tags=["pages"])
def admin_page(
    request: Request,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    return _render_admin_page(request=request, current_admin=current_admin, db=db)


@router.post("/admin/users", tags=["pages"])
def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    is_admin: str | None = Form(default=None),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    normalized_username = username.strip()
    if not normalized_username or not password:
        return _render_admin_page(
            request=request,
            current_admin=current_admin,
            db=db,
            error="Username and password are required",
            status_code=400,
        )

    user = User(
        username=normalized_username,
        password_hash=hash_password(password),
        is_admin=(is_admin == "on"),
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _render_admin_page(
            request=request,
            current_admin=current_admin,
            db=db,
            error="Username already exists",
            status_code=400,
        )

    return RedirectResponse(url="/admin", status_code=303)


@router.post("/admin/users/{user_id}/password", tags=["pages"])
def update_user_password(
    user_id: int,
    request: Request,
    new_password: str = Form(...),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    normalized_password = new_password.strip()
    if len(normalized_password) < 4:
        return _render_admin_page(
            request=request,
            current_admin=current_admin,
            db=db,
            error="Password must be at least 4 characters",
            status_code=400,
        )

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        return _render_admin_page(
            request=request,
            current_admin=current_admin,
            db=db,
            error=f"User with id {user_id} not found",
            status_code=404,
        )

    user.password_hash = hash_password(normalized_password)
    db.commit()
    return _render_admin_page(
        request=request,
        current_admin=current_admin,
        db=db,
        success=f"Password updated for user '{user.username}'",
    )
