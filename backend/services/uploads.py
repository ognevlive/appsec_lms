"""Upload handling: filename sanitization, config validation, storage, streaming."""
from __future__ import annotations

import os
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

    max_mb = int(cfg.get("max_size_mb", settings.uploads_max_size_mb))
    if any_size_over(total_size_bytes, file_count, max_mb):
        raise ValueError(f"file_too_large:{max_mb}")


def any_size_over(total_size_bytes: int, file_count: int, max_mb: int) -> bool:
    # Total bound — per-file enforced during streaming.
    return total_size_bytes > file_count * max_mb * 1024 * 1024


def validate_file(task_config: dict, filename: str, size_bytes: int) -> None:
    cfg = _upload_cfg(task_config)
    if cfg is None:
        raise ValueError("uploads_disabled")

    max_mb = int(cfg.get("max_size_mb", settings.uploads_max_size_mb))
    if size_bytes > max_mb * 1024 * 1024:
        raise ValueError(f"file_too_large:{max_mb}")

    allowed = [e.lower() for e in cfg.get("allowed_ext") or settings.uploads_allowed_ext_default]
    ext = Path(filename).suffix.lstrip(".").lower()
    if ext not in allowed:
        raise ValueError(f"ext_not_allowed:{ext}")


async def save_submission_files(
    submission: TaskSubmission,
    task_config: dict,
    files: Iterable[UploadFile],
    db: AsyncSession,
) -> list[SubmissionFile]:
    """Stream-save each UploadFile to disk, insert SubmissionFile rows, return list."""
    sub_dir = Path(settings.uploads_dir) / str(submission.id)
    sub_dir.mkdir(parents=True, exist_ok=True)

    saved: list[SubmissionFile] = []
    try:
        for upload in files:
            original = sanitize_filename(upload.filename or "file")
            stored_name = f"{secrets.token_hex(8)}_{original}"
            dst = sub_dir / stored_name
            size = 0
            with dst.open("wb") as fp:
                while True:
                    chunk = await upload.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    size += len(chunk)
                    fp.write(chunk)
            validate_file(task_config, original, size)

            rec = SubmissionFile(
                submission_id=submission.id,
                filename=original,
                stored_path=str(dst.relative_to(settings.uploads_dir)),
                size_bytes=size,
                content_type=upload.content_type,
            )
            db.add(rec)
            saved.append(rec)
        await db.flush()
        return saved
    except Exception:
        # Roll back files on disk if any step failed
        shutil.rmtree(sub_dir, ignore_errors=True)
        raise


def delete_submission_files(submission_id: int) -> None:
    sub_dir = Path(settings.uploads_dir) / str(submission_id)
    shutil.rmtree(sub_dir, ignore_errors=True)


def absolute_stored_path(stored_path: str) -> Path:
    """Resolve a file path, guarding against traversal outside UPLOADS_DIR."""
    base = Path(settings.uploads_dir).resolve()
    target = (base / stored_path).resolve()
    if not str(target).startswith(str(base) + os.sep) and target != base:
        raise ValueError("path_escape")
    return target
