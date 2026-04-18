"""SHA256-хэширование флагов для CTF/ssh_lab.

Plaintext `flag` в API — write-only: при сохранении заменяется на `flag_hash`,
plaintext нигде не остаётся (ни в БД, ни в логах, ни в ответах API).
"""
import hashlib


def hash_flag(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


def apply_flag_to_config(config: dict) -> dict:
    """Вернуть новый config: если есть plaintext `flag` — хэшировать и выбросить plaintext."""
    out = dict(config)
    plaintext = out.pop("flag", None)
    if plaintext:
        out["flag_hash"] = hash_flag(plaintext)
    return out
