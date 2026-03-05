from pathlib import Path
import shutil
import tempfile
import zipfile

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask

from app.conversion_service import convert_file


router = APIRouter()

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/", response_class=HTMLResponse, tags=["pages"])
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"page_title": "Monitor Import"},
    )


def _cleanup_temp_dir(path: str) -> None:
    shutil.rmtree(path, ignore_errors=True)


@router.post("/convert", tags=["pages"])
def convert(
    request: Request,
    file: UploadFile = File(...),
    base_name: str = Form(""),
    dedup_mode: str = Form("skip"),
    existing_materials_file: UploadFile | None = File(default=None),
) -> FileResponse:
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

    try:
        output_files = convert_file(
            input_csv=input_path,
            out_dir=out_dir,
            base_name=effective_base_name,
            existing_materials_file=str(existing_file_path) if existing_file_path else None,
            skip_material_dedup_query=(dedup_mode == "skip"),
        )
    except Exception as exc:
        _cleanup_temp_dir(temp_dir)
        raise HTTPException(status_code=400, detail=f"Conversion failed: {exc}") from exc
    finally:
        file.file.close()
        if existing_materials_file is not None:
            existing_materials_file.file.close()

    zip_name = f"{effective_base_name}_converted.zip"
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
