from services.flag_hash import hash_flag, apply_flag_to_config


def test_hash_flag_is_sha256_hex():
    h = hash_flag("FLAG{secret}")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_hash_flag_deterministic():
    assert hash_flag("x") == hash_flag("x")
    assert hash_flag("x") != hash_flag("y")


def test_apply_flag_to_config_replaces_plaintext_with_hash():
    cfg = {"docker_image": "a", "flag": "FLAG{abc}"}
    out = apply_flag_to_config(cfg)
    assert "flag" not in out
    assert out["flag_hash"] == hash_flag("FLAG{abc}")
    assert out["docker_image"] == "a"


def test_apply_flag_to_config_preserves_existing_hash_if_no_plaintext():
    cfg = {"docker_image": "a", "flag_hash": "deadbeef" * 8}
    out = apply_flag_to_config(cfg)
    assert out["flag_hash"] == "deadbeef" * 8
    assert "flag" not in out


def test_apply_flag_to_config_plaintext_takes_precedence():
    cfg = {"flag": "new", "flag_hash": "old"}
    out = apply_flag_to_config(cfg)
    assert out["flag_hash"] == hash_flag("new")
