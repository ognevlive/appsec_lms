import io
import zipfile

import pytest

from services.bundle import BundleError, open_bundle, pack_task, read_yaml


def test_pack_task_roundtrip():
    raw = pack_task({"slug": "x", "title": "X"})
    zf = open_bundle(raw)
    data = read_yaml(zf, "manifest.yaml")
    assert data == {"slug": "x", "title": "X"}


def test_zipslip_rejected():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.yaml", "slug: x")
    zf = open_bundle(buf.getvalue())
    with pytest.raises(BundleError, match="unsafe"):
        read_yaml(zf, "../evil.yaml")


def test_size_limit():
    big = b"x" * (10 * 1024 * 1024 + 1)
    with pytest.raises(BundleError, match="too large"):
        open_bundle(big)


def test_not_a_zip():
    with pytest.raises(BundleError, match="not a valid zip"):
        open_bundle(b"not a zip")
