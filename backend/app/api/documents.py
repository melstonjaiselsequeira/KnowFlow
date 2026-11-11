
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Document

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".csv", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload")
async def upload_document(
    project_id: int,
    file: UploadFile = File(...)
):
    extension = Path(file.filename or "").suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type"
        )

    db: Session = SessionLocal()

    try:
        # Verify project exists
        from app.models import Project

        project = db.query(Project).filter(
            Project.id == project_id
        ).first()

        if not project:
            raise HTTPException(
                status_code=404,
                detail="Project not found"
            )

        file_id = str(uuid.uuid4())
        stored_filename = f"{file_id}{extension}"
        file_path = UPLOAD_DIR / stored_filename

        size = 0

        try:
            with file_path.open("wb") as buffer:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)

                    if size > MAX_FILE_SIZE:
                        raise HTTPException(
                            status_code=413,
                            detail="File exceeds 10 MB limit"
                        )

                    buffer.write(chunk)

        except Exception:
            file_path.unlink(missing_ok=True)
            raise

        document = Document(
            project_id=project_id,
            filename=file.filename or stored_filename,
            file_type=extension.lstrip("."),
            file_path=str(file_path),
            processing_status="pending"
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        return {
            "message": "Document uploaded successfully",
            "document_id": document.id,
            "filename": document.filename,
            "status": document.processing_status
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
