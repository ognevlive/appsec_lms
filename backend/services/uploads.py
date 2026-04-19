"""Upload handling: filename sanitization, config validation, storage, streaming."""
from __future__ import annotations

import secrets
import shutil
import unicodedata
from pathlib import Path
from typing import Iterable

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import SubmissionFile, TaskSubmission

_MAX_NAME_LEN = 200
_CHUNK_SIZE = 1 << 20  # 1 MiB


def sanitize_filename(name: str) -> str:
    """Strip path separators / control chars, NFC normalize, truncate."""
    if not name:
        return "file"
    cleaned = name.replace("\\", "/").split("/")[-1]
    cleaned = unicodedata.normalize("NFC", cleaned)
    cleaned = "".join(ch for ch in cleaned if ch.isprintable()).strip()
    if not cleaned:
        return "file"
    if len(cleaned) > _MAX_NAME_LEN:
        stem = Path(cleaned).stem
        suffix = Path(cleaned).suffix
        keep = _MAX_NAME_LEN - len(suffix)
        cleaned = stem[: max(keep, 1)] + suffix
    return cleaned


def _upload_cfg(task_config: dict) -> dict | None:
    cfg = (task_config or {}).get("file_upload")
    if not cfg or not cfg.get("enabled"):
        return None
    return cfg


def _allowed_ext(cfg: dict) -> list[str]:
    return [e.lower() for e in cfg.get("allowed_ext") or settings.uploads_allowed_ext_default]


def validate_upload_config(
    task_config: dict, file_count: int, total_size_bytes: int
) -> None:
    """Raise ValueError on limit violation. file_count=0 is allowed unless required."""
    cfg = _upload_cfg(task_config)
    if cfg is None:
        if file_count > 0:
            raise ValueError("uploads_disabled")
        return

    if cfg.get("required") and file_count == 0:
        raise ValueError("file_required")

    max_files = int(cfg.get("max_files", 5))
    if file_count > max_files:
        raise ValueError(f"too_many_files:{max_files}")


def validate_file(task_config: dict, filename: str) -> None:
    """Metadata-only check: extension is allowed. Size is enforced during streaming."""
    cfg = _upload_cfg(task_config)
    if cfg is None:
        raise ValueError("uploads_disabled")

    sanitized = sanitize_filename(filename)
    ext = sanitized.rsplit(".", 1)[-1].lower() if "." in sanitized else ""
    allowed = _allowed_ext(cfg)
    if ext not in allowed:
        raise ValueError(f"ext_not_allowed:{ext}")


async def save_submission_files(
    submission: TaskSubmission,
    task_config: dict,
    files: Iterable[UploadFile],
    db: AsyncSession,
) -> list[SubmissionFile]:
    """Stream-save each UploadFile to disk, insert SubmissionFile rows, return list."""
    cfg = _upload_cfg(task_config)
    if cfg is None:
        raise ValueError("uploads_disabled")
    max_mb = int(cfg.get("max_size_mb", settings.uploads_max_size_mb))
    max_bytes = max_mb * 1024 * 1024
    allowed = _allowed_ext(cfg)

    sub_dir = Path(settings.uploads_dir) / str(submission.id)
    sub_dir.mkdir(parents=True, exist_ok=True)

    saved: list[SubmissionFile] = []
    created_paths: list[Path] = []
    try:
        for upload in files:
            original = sanitize_filename(upload.filename or "file")
            ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
            if ext not in allowed:
                raise ValueError(f"ext_not_allowed:{ext}")

            stored_name = f"{secrets.token_hex(8)}_{original}"
            dst = sub_dir / stored_name
            written = 0
            with dst.open("wb") as fp:
                created_paths.append(dst)
                while chunk := upload.file.read(_CHUNK_SIZE):
                    written += len(chunk)
                    if written > max_bytes:
                        raise ValueError(f"file_too_large:{original}")
                    fp.write(chunk)

            stored_path = f"{submission.id}/{stored_name}"
            rec = SubmissionFile(
                submission_id=submission.id,
                filename=original,
                stored_path=stored_path,
                size_bytes=written,
                content_type=upload.content_type,
            )
            db.add(rec)
            saved.append(rec)
        await db.flush()
        return saved
    except Exception:
        for path in created_paths:
            path.unlink(missing_ok=True)
        raise


def delete_submission_files(submission_id: int) -> None:
    sub_dir = Path(settings.uploads_dir) / str(submission_id)
    shutil.rmtree(sub_dir, ignore_errors=True)


def absolute_stored_path(stored_path: str) -> Path:
    """Resolve a file path, guarding against traversal outside UPLOADS_DIR."""
    if Path(stored_path).is_absolute():
        raise ValueError("absolute stored_path not allowed")
    base = Path(settings.uploads_dir).resolve()
    target = (base / stored_path).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise ValueError("stored_path escapes uploads dir")
    return target
