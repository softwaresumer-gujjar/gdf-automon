"""Chat API — /api/chat
Rooms can be of type:
  task    — auto-created per task; access = assignees + creator + admins
  topic   — admin creates; access = explicit members + superadmins
  general — any authenticated user
"""
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select, delete, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.core.config import settings
from app.core.redis_client import publish_chat_message
from app.models.chat import ChatRoom, ChatRoomMember, ChatMessage, ChatAttachment
from app.models.task import Task, TaskAssignment
from app.models.user import User

router = APIRouter(prefix="/chat", tags=["chat"])

CHAT_UPLOAD_DIR = Path(settings.upload_dir) / "chat"
CHAT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


# ── Helpers ────────────────────────────────────────────────────────────────────

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


async def _assert_room_access(room: ChatRoom, user: User, db: AsyncSession) -> None:
    """Raise 404 if user cannot access this chat room."""
    if user.role == "super_admin":
        return
    if room.room_type == "general":
        return
    if room.room_type == "task":
        if user.role in ("admin", "super_admin"):
            return
        # Check task assignment
        task_row = await db.execute(
            select(TaskAssignment).where(
                TaskAssignment.task_id == room.task_id,
                TaskAssignment.user_id == user.id,
            )
        )
        if task_row.scalars().first() is None:
            # Also allow if user is task creator
            task = await db.get(Task, room.task_id)
            if task is None or task.created_by_id != user.id:
                raise HTTPException(404, "Chat room not found")
        return
    # topic room — check explicit membership
    member = await db.execute(
        select(ChatRoomMember).where(
            ChatRoomMember.room_id == room.id,
            ChatRoomMember.user_id == user.id,
        )
    )
    if member.scalars().first() is None:
        raise HTTPException(404, "Chat room not found")


async def _get_room_or_404(room_id: uuid.UUID, db: AsyncSession) -> ChatRoom:
    room = await db.get(ChatRoom, room_id)
    if room is None:
        raise HTTPException(404, "Chat room not found")
    return room


async def _user_row(user_id: uuid.UUID | None, db: AsyncSession) -> dict:
    if user_id is None:
        return {"id": None, "full_name": "Deleted user", "email": ""}
    u = await db.get(User, user_id)
    if u is None:
        return {"id": str(user_id), "full_name": "Deleted user", "email": ""}
    return {"id": str(u.id), "full_name": u.full_name, "email": u.email}


def _attachment_out(a: ChatAttachment) -> dict:
    return {
        "id": str(a.id),
        "original_name": a.original_name,
        "file_type": a.file_type,
        "file_size": a.file_size,
        "mime_type": a.mime_type,
        "url": f"/api/chat/attachments/{a.id}",
    }


async def _message_out(msg: ChatMessage, db: AsyncSession) -> dict:
    sender = await _user_row(msg.user_id, db)
    attachments_res = await db.execute(
        select(ChatAttachment).where(ChatAttachment.message_id == msg.id)
    )
    attachments = [_attachment_out(a) for a in attachments_res.scalars().all()]
    return {
        "id": str(msg.id),
        "room_id": str(msg.room_id),
        "sender": sender,
        "content": msg.content,
        "attachments": attachments,
        "created_at": msg.created_at.isoformat(),
    }


# ── Schemas ────────────────────────────────────────────────────────────────────

class RoomCreate(BaseModel):
    name: str
    room_type: str = "topic"
    member_ids: list[uuid.UUID] = []


class MessageCreate(BaseModel):
    content: str | None = None


class MemberAdd(BaseModel):
    user_ids: list[uuid.UUID]


# ── Rooms ──────────────────────────────────────────────────────────────────────

@router.get("/rooms")
async def list_rooms(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return rooms accessible to the current user."""
    if user.role == "super_admin":
        result = await db.execute(select(ChatRoom).order_by(ChatRoom.created_at))
        rooms = result.scalars().all()
    else:
        # General rooms + explicitly membered topic rooms + task rooms user has access to
        member_rooms = await db.execute(
            select(ChatRoomMember.room_id).where(ChatRoomMember.user_id == user.id)
        )
        membered_ids = [r for r, in member_rooms.all()]

        # Task rooms where user is assigned or created
        assigned_tasks = await db.execute(
            select(TaskAssignment.task_id).where(TaskAssignment.user_id == user.id)
        )
        task_ids_assigned = [r for r, in assigned_tasks.all()]

        created_tasks = await db.execute(
            select(Task.id).where(Task.created_by_id == user.id)
        )
        task_ids_created = [r for r, in created_tasks.all()]
        all_task_ids = list(set(task_ids_assigned + task_ids_created))

        result = await db.execute(
            select(ChatRoom).where(
                (ChatRoom.room_type == "general") |
                (ChatRoom.id.in_(membered_ids)) |
                (ChatRoom.task_id.in_(all_task_ids)) |
                ((ChatRoom.room_type == "task") & (user.role == "admin"))
            ).order_by(ChatRoom.created_at)
        )
        rooms = result.scalars().all()

    out = []
    for room in rooms:
        # Get last message
        last_msg_res = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.room_id == room.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(1)
        )
        last_msg = last_msg_res.scalars().first()
        # Count unread (simplified: just total message count)
        count_res = await db.execute(
            select(sqlfunc.count()).where(ChatMessage.room_id == room.id)
        )
        msg_count = count_res.scalar() or 0

        out.append({
            "id": str(room.id),
            "name": room.name,
            "room_type": room.room_type,
            "task_id": str(room.task_id) if room.task_id else None,
            "created_at": room.created_at.isoformat(),
            "message_count": msg_count,
            "last_message": {
                "content": last_msg.content,
                "created_at": last_msg.created_at.isoformat(),
            } if last_msg else None,
        })
    return out


@router.post("/rooms", status_code=201)
async def create_room(
    body: RoomCreate,
    user: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if body.room_type not in ("topic", "general"):
        raise HTTPException(400, "room_type must be 'topic' or 'general'")
    room = ChatRoom(
        name=body.name,
        room_type=body.room_type,
        created_by_id=user.id,
    )
    db.add(room)
    await db.flush()
    # Add creator + specified members
    member_ids = list({user.id} | set(body.member_ids))
    for uid in member_ids:
        db.add(ChatRoomMember(room_id=room.id, user_id=uid))
    await db.commit()
    await db.refresh(room)
    return {"id": str(room.id), "name": room.name, "room_type": room.room_type}


@router.get("/rooms/task/{task_id}")
async def get_or_create_task_room(
    task_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get (or auto-create) the chat room for a task."""
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(404, "Task not found")

    # Access check: must be admin or assigned/creator
    if user.role not in ("admin", "super_admin"):
        assignment = await db.execute(
            select(TaskAssignment).where(
                TaskAssignment.task_id == task_id,
                TaskAssignment.user_id == user.id,
            )
        )
        if assignment.scalars().first() is None and task.created_by_id != user.id:
            raise HTTPException(404, "Task not found")

    existing = await db.execute(
        select(ChatRoom).where(ChatRoom.task_id == task_id)
    )
    room = existing.scalars().first()
    if room is None:
        room = ChatRoom(
            name=f"Task: {task.title}",
            room_type="task",
            task_id=task_id,
            created_by_id=user.id,
        )
        db.add(room)
        await db.commit()
        await db.refresh(room)
    return {"id": str(room.id), "name": room.name, "room_type": room.room_type, "task_id": str(room.task_id)}


@router.get("/rooms/{room_id}")
async def get_room(
    room_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    room = await _get_room_or_404(room_id, db)
    await _assert_room_access(room, user, db)
    members_res = await db.execute(
        select(ChatRoomMember).where(ChatRoomMember.room_id == room_id)
    )
    members = []
    for m in members_res.scalars().all():
        u = await db.get(User, m.user_id)
        if u:
            members.append({"id": str(u.id), "full_name": u.full_name, "email": u.email})
    return {
        "id": str(room.id),
        "name": room.name,
        "room_type": room.room_type,
        "task_id": str(room.task_id) if room.task_id else None,
        "members": members,
    }


# ── Members ────────────────────────────────────────────────────────────────────

@router.post("/rooms/{room_id}/members", status_code=201)
async def add_members(
    room_id: uuid.UUID,
    body: MemberAdd,
    user: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    room = await _get_room_or_404(room_id, db)
    if room.room_type == "task":
        raise HTTPException(400, "Task room members are derived from task assignments")
    added = 0
    for uid in body.user_ids:
        existing = await db.execute(
            select(ChatRoomMember).where(
                ChatRoomMember.room_id == room_id,
                ChatRoomMember.user_id == uid,
            )
        )
        if existing.scalars().first() is None:
            db.add(ChatRoomMember(room_id=room_id, user_id=uid))
            added += 1
    await db.commit()
    return {"added": added}


@router.delete("/rooms/{room_id}/members/{user_id}", status_code=204)
async def remove_member(
    room_id: uuid.UUID,
    user_id: uuid.UUID,
    user: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    room = await _get_room_or_404(room_id, db)
    if room.room_type == "task":
        raise HTTPException(400, "Task room members are derived from task assignments")
    await db.execute(
        delete(ChatRoomMember).where(
            ChatRoomMember.room_id == room_id,
            ChatRoomMember.user_id == user_id,
        )
    )
    await db.commit()


# ── Messages ───────────────────────────────────────────────────────────────────

@router.get("/rooms/{room_id}/messages")
async def list_messages(
    room_id: uuid.UUID,
    before_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    room = await _get_room_or_404(room_id, db)
    await _assert_room_access(room, user, db)

    q = select(ChatMessage).where(ChatMessage.room_id == room_id)
    if before_id is not None:
        pivot = await db.get(ChatMessage, before_id)
        if pivot:
            q = q.where(ChatMessage.created_at < pivot.created_at)
    q = q.order_by(ChatMessage.created_at.desc()).limit(limit)
    result = await db.execute(q)
    msgs = result.scalars().all()
    # Return in ascending order (oldest first in the batch)
    msgs = list(reversed(msgs))
    return [await _message_out(m, db) for m in msgs]


@router.post("/rooms/{room_id}/messages", status_code=201)
async def send_message(
    room_id: uuid.UUID,
    body: MessageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    room = await _get_room_or_404(room_id, db)
    await _assert_room_access(room, user, db)
    if not body.content or not body.content.strip():
        raise HTTPException(400, "Message content cannot be empty")
    msg = ChatMessage(
        room_id=room_id,
        user_id=user.id,
        content=body.content.strip(),
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    out = await _message_out(msg, db)
    # Broadcast via Redis → Socket.io
    try:
        await publish_chat_message(str(room_id), out)
    except Exception:
        pass  # non-fatal if Redis unavailable
    return out


@router.post("/rooms/{room_id}/messages/upload", status_code=201)
async def send_message_with_file(
    room_id: uuid.UUID,
    file: UploadFile = File(...),
    content: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    room = await _get_room_or_404(room_id, db)
    await _assert_room_access(room, user, db)

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large (max 100 MB)")

    mime = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"
    ext = Path(file.filename or "file").suffix or ""
    stored_name = f"{uuid.uuid4()}{ext}"
    room_dir = CHAT_UPLOAD_DIR / str(room_id)
    room_dir.mkdir(parents=True, exist_ok=True)
    (room_dir / stored_name).write_bytes(data)

    msg = ChatMessage(room_id=room_id, user_id=user.id, content=content)
    db.add(msg)
    await db.flush()

    attachment = ChatAttachment(
        message_id=msg.id,
        filename=stored_name,
        original_name=file.filename or stored_name,
        file_type=_file_type(mime),
        file_size=len(data),
        mime_type=mime,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(msg)
    out = await _message_out(msg, db)
    try:
        await publish_chat_message(str(room_id), out)
    except Exception:
        pass
    return out


@router.delete("/rooms/{room_id}/messages/{message_id}", status_code=204)
async def delete_message(
    room_id: uuid.UUID,
    message_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    room = await _get_room_or_404(room_id, db)
    await _assert_room_access(room, user, db)
    msg = await db.get(ChatMessage, message_id)
    if msg is None or msg.room_id != room_id:
        raise HTTPException(404, "Message not found")
    if user.role not in ("admin", "super_admin") and msg.user_id != user.id:
        raise HTTPException(403, "Cannot delete another user's message")
    # Delete on-disk files
    attachments_res = await db.execute(
        select(ChatAttachment).where(ChatAttachment.message_id == message_id)
    )
    for a in attachments_res.scalars().all():
        try:
            (CHAT_UPLOAD_DIR / str(room_id) / a.filename).unlink(missing_ok=True)
        except Exception:
            pass
    await db.delete(msg)
    await db.commit()


# ── Attachments ────────────────────────────────────────────────────────────────

@router.get("/attachments/{attachment_id}")
async def get_attachment(
    attachment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    attachment = await db.get(ChatAttachment, attachment_id)
    if attachment is None:
        raise HTTPException(404, "Attachment not found")
    # Check room access via message
    msg = await db.get(ChatMessage, attachment.message_id)
    if msg is None:
        raise HTTPException(404, "Attachment not found")
    room = await _get_room_or_404(msg.room_id, db)
    await _assert_room_access(room, user, db)

    file_path = CHAT_UPLOAD_DIR / str(msg.room_id) / attachment.filename
    if not file_path.exists():
        raise HTTPException(404, "File not found on disk")
    return FileResponse(
        str(file_path),
        media_type=attachment.mime_type,
        filename=attachment.original_name,
    )
