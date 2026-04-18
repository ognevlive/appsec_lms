import pytest

from services.slug import slugify, is_valid_slug


@pytest.mark.parametrize("given,expected", [
    ("Hello World", "hello-world"),
    ("Что такое SAST", "chto-takoe-sast"),
    ("Gitleaks — первый запуск", "gitleaks-pervyy-zapusk"),
    ("Lab 1: Найди секреты", "lab-1-naydi-sekrety"),
    ("  spaces   ", "spaces"),
    ("!!!", ""),
])
def test_slugify(given, expected):
    assert slugify(given) == expected


@pytest.mark.parametrize("slug,ok", [
    ("foo", True),
    ("foo-bar-2", True),
    ("a" * 100, True),
    ("A", False),          # uppercase
    ("foo_bar", False),    # underscore
    ("a", False),          # too short
    ("a" * 101, False),    # too long
    ("foo bar", False),    # space
])
def test_is_valid_slug(slug, ok):
    assert is_valid_slug(slug) is ok
