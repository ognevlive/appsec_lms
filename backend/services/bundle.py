"""ZIP-бандлы для экспорта/импорта тасков и курсов.

Формат:
- task bundle: zip с `manifest.yaml`
- course bundle: zip с `course.yaml` и, при bundle=true, `tasks/{slug}.yaml`

Импорт защищён от zip-slip (отказ на `..` и абсолютные пути) и лимитом 10 MB.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import PurePosixPath

import yaml

MAX_BUNDLE_BYTES = 10 * 1024 * 1024


class BundleError(ValueError):
    pass


def _safe_name(name: str) -> str:
    """Принимает имя файла внутри архива, отказывает на попытках выхода за пределы."""
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts:
        raise BundleError(f"unsafe path in bundle: {name}")
    return str(p)


def read_yaml(zf: zipfile.ZipFile, name: str) -> dict:
    safe = _safe_name(name)
    with zf.open(safe) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise BundleError(f"{name}: expected YAML mapping")
    return data


def list_task_files(zf: zipfile.ZipFile) -> list[str]:
    """Список файлов под tasks/ в бандле курса. Каждое имя проверяется."""
    out = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        safe = _safe_name(info.filename)
        if safe.startswith("tasks/") and safe.endswith(".yaml"):
            out.append(safe)
    return out


def open_bundle(raw: bytes) -> zipfile.ZipFile:
    if len(raw) > MAX_BUNDLE_BYTES:
        raise BundleError(f"bundle too large ({len(raw)} > {MAX_BUNDLE_BYTES})")
    try:
        return zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as e:
        raise BundleError(f"not a valid zip: {e}")


def pack_task(manifest: dict) -> bytes:
    """Создать zip с одним manifest.yaml."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.yaml", yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False))
    return buf.getvalue()


def pack_course(course: dict, tasks: dict[str, dict] | None = None) -> bytes:
    """Создать zip с course.yaml и опционально tasks/{slug}.yaml."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("course.yaml", yaml.safe_dump(course, allow_unicode=True, sort_keys=False))
        for slug, task in (tasks or {}).items():
            zf.writestr(f"tasks/{slug}.yaml", yaml.safe_dump(task, allow_unicode=True, sort_keys=False))
    return buf.getvalue()
