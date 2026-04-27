"""Tasks/Goals API — /api/tasks"""
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.core.config import settings
from app.models.task import Task, TaskAssignment, TaskAttachment, TASK_STATUSES
from app.models.user import User

router = APIRouter(prefix="/tasks", tags=["tasks"])

UPLOAD_DIR = Path(settings.upload_dir)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


def _file_type(mime: str | None) -> str:
    if not mime:
        return "other"
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    if mime in ("application/pdf", "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "text/plain"):
        return "document"
    return "other"


# ── Schemas ───────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    deadline: datetime | None = None
    assignee_ids: list[uuid.UUID] = []


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    deadline: datetime | None = None


class AssignmentUpdate(BaseModel):
    user_ids: list[uuid.UUID]


class SubmitBody(BaseModel):
    completion_note: str | None = None


class ReviewBody(BaseModel):
    approved: bool
    review_note: str | None = None


class AttachmentResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    filename: str
    original_name: str
    file_type: str
    file_size: int | None

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    deadline: datetime | None
    status: str
    created_by_id: uuid.UUID | None
    reviewed_by_id: uuid.UUID | None
    reviewed_at: datetime | None
    review_note: str | None
    submitted_at: datetime | None
    completion_note: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskDetailResponse(TaskResponse):
    assignees: list[dict[str, Any]] = []
    attachments: list[AttachmentResponse] = []


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_task_or_404(task_id: uuid.UUID, db: AsyncSession) -> Task:
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


async def _assert_task_access(task: Task, user: User, db: AsyncSession) -> None:
    """Admin/super_admin can always access. Others must be assigned."""
    if user.role in ("admin", "super_admin"):
        return
    result = await db.execute(
        select(TaskAssignment).where(
            TaskAssignment.task_id == task.id,
            TaskAssignment.user_id == user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Task not found")


async def _build_detail(task: Task, db: AsyncSession) -> dict:
    from app.models.user import User as UserModel
    assign_result = await db.execute(
        select(TaskAssignment).where(TaskAssignment.task_id == task.id)
    )
    assignments = assign_result.scalars().all()
    assignees = []
    for a in assignments:
        u = await db.get(UserModel, a.user_id)
        if u:
            assignees.append({"id": str(u.id), "full_name": u.full_name, "email": u.email})

    att_result = await db.execute(
        select(TaskAttachment).where(TaskAttachment.task_id == task.id)
    )
    attachments = att_result.scalars().all()
    return {
        **{c.name: getattr(task, c.name) for c in task.__table__.columns},
        "assignees": assignees,
        "attachments": attachments,
    }


# ── Task CRUD ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role in ("admin", "super_admin"):
        result = await db.execute(select(Task).order_by(Task.deadline.asc().nullslast()))
        return result.scalars().all()
    # operators: only assigned tasks
    assigned = await db.execute(
        select(Task)
        .join(TaskAssignment, Task.id == TaskAssignment.task_id)
        .where(TaskAssignment.user_id == user.id)
        .order_by(Task.deadline.asc().nullslast())
    )
    return assigned.scalars().all()


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    body: TaskCreate,
    user: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    task = Task(
        title=body.title,
        description=body.description,
        deadline=body.deadline,
        created_by_id=user.id,
    )
    db.add(task)
    await db.flush()
    for uid in body.assignee_ids:
        db.add(TaskAssignment(task_id=task.id, user_id=uid))
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(
    task_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(task_id, db)
    await _assert_task_access(task, user, db)
    return await _build_detail(task, db)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    _: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(task_id, db)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(task, k, v)
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: uuid.UUID,
    _: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(task_id, db)
    await db.delete(task)
    await db.commit()


# ── Assignment management ─────────────────────────────────────────────────────

@router.put("/{task_id}/assignments")
async def set_assignments(
    task_id: uuid.UUID,
    body: AssignmentUpdate,
    _: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(task_id, db)
    await db.execute(delete(TaskAssignment).where(TaskAssignment.task_id == task.id))
    for uid in body.user_ids:
        db.add(TaskAssignment(task_id=task.id, user_id=uid))
    await db.commit()
    return {"status": "assignments updated"}


# ── Status transitions ────────────────────────────────────────────────────────

@router.post("/{task_id}/submit", response_model=TaskResponse)
async def submit_task(
    task_id: uuid.UUID,
    body: SubmitBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """User marks task as completed (→ submitted, pending admin review)."""
    task = await _get_task_or_404(task_id, db)
    await _assert_task_access(task, user, db)
    if task.status not in ("open", "rejected"):
        raise HTTPException(400, f"Cannot submit task with status '{task.status}'")
    task.status = "submitted"
    task.submitted_by_id = user.id
    task.submitted_at = datetime.now(timezone.utc)
    task.completion_note = body.completion_note
    await db.commit()
    await db.refresh(task)
    return task


@router.post("/{task_id}/review", response_model=TaskResponse)
async def review_task(
    task_id: uuid.UUID,
    body: ReviewBody,
    user: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Admin approves → done; rejects → open."""
    task = await _get_task_or_404(task_id, db)
    if task.status != "submitted":
        raise HTTPException(400, "Task must be in 'submitted' state to review")
    task.status = "done" if body.approved else "rejected"
    task.reviewed_by_id = user.id
    task.reviewed_at = datetime.now(timezone.utc)
    task.review_note = body.review_note
    await db.commit()
    await db.refresh(task)

    # Notify assigned users of the review outcome
    _notify_review_result(task, body.approved)
    return task


def _notify_review_result(task: Task, approved: bool) -> None:
    import asyncio
    from app.services.push_service import send_alert_notification

    msg = (
        f"Task '{task.title}' has been approved!" if approved
        else f"Task '{task.title}' was returned for revision."
    )
    asyncio.create_task(send_alert_notification(
        title="Task Update",
        body=msg,
        severity="info",
        sensor_id=None,
        target_user_ids=None,  # handled by task assignments instead
    ))


# ── File attachments ──────────────────────────────────────────────────────────

@router.post("/{task_id}/attachments", response_model=AttachmentResponse, status_code=201)
async def upload_attachment(
    task_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(task_id, db)
    await _assert_task_access(task, user, db)

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large (max 100 MB)")

    ext = Path(file.filename or "file").suffix
    stored_name = f"{uuid.uuid4()}{ext}"
    dest = UPLOAD_DIR / str(task_id)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / stored_name).write_bytes(content)

    mime = file.content_type or mimetypes.guess_type(file.filename or "")[0]
    attachment = TaskAttachment(
        task_id=task_id,
        filename=stored_name,
        original_name=file.filename or stored_name,
        file_type=_file_type(mime),
        file_size=len(content),
        uploaded_by_id=user.id,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)
    return attachment


@router.get("/{task_id}/attachments/{filename}")
async def download_attachment(
    task_id: uuid.UUID,
    filename: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(task_id, db)
    await _assert_task_access(task, user, db)

    path = UPLOAD_DIR / str(task_id) / filename
    if not path.exists():
        raise HTTPException(404, "Attachment not found")

    result = await db.execute(
        select(TaskAttachment).where(
            TaskAttachment.task_id == task_id,
            TaskAttachment.filename == filename,
        )
    )
    att = result.scalar_one_or_none()
    media_type, _ = mimetypes.guess_type(filename)
    headers = {}
    if att:
        headers["Content-Disposition"] = f'inline; filename="{att.original_name}"'
    return FileResponse(str(path), media_type=media_type or "application/octet-stream", headers=headers)


@router.delete("/{task_id}/attachments/{attachment_id}", status_code=204)
async def delete_attachment(
    task_id: uuid.UUID,
    attachment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(task_id, db)
    await _assert_task_access(task, user, db)

    att = await db.get(TaskAttachment, attachment_id)
    if not att or att.task_id != task_id:
        raise HTTPException(404, "Attachment not found")

    path = UPLOAD_DIR / str(task_id) / att.filename
    if path.exists():
        path.unlink()
    await db.delete(att)
    await db.commit()
