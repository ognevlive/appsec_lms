"""Unit tests for upload filename sanitization and validation helpers."""
import pytest

from services.uploads import sanitize_filename, validate_upload_config

pytestmark = pytest.mark.anyio


def test_sanitize_strips_path_separators():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("a/b/c.txt") == "c.txt"
    assert sanitize_filename("x\\y\\z.pdf") == "z.pdf"


def test_sanitize_keeps_unicode():
    assert sanitize_filename("отчёт.pdf") == "отчёт.pdf"


def test_sanitize_truncates():
    name = "a" * 300 + ".pdf"
    result = sanitize_filename(name)
    assert len(result) <= 200
    assert result.endswith(".pdf")


def test_sanitize_rejects_empty_after_clean():
    assert sanitize_filename("") == "file"
    assert sanitize_filename("/") == "file"
    assert sanitize_filename("   ") == "file"


def test_validate_upload_config_rejects_disabled():
    cfg = {}
    with pytest.raises(ValueError, match="uploads_disabled"):
        validate_upload_config(cfg, file_count=1, total_size_bytes=0)


def test_validate_upload_config_required_empty():
    cfg = {"file_upload": {"enabled": True, "required": True, "max_files": 5, "max_size_mb": 20, "allowed_ext": ["pdf"]}}
    with pytest.raises(ValueError, match="file_required"):
        validate_upload_config(cfg, file_count=0, total_size_bytes=0)


def test_validate_upload_config_too_many_files():
    cfg = {"file_upload": {"enabled": True, "required": False, "max_files": 2, "max_size_mb": 20, "allowed_ext": ["pdf"]}}
    with pytest.raises(ValueError, match="too_many_files"):
        validate_upload_config(cfg, file_count=3, total_size_bytes=0)
