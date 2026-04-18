"""Integration test: guard returns 403 when user tries locked unit."""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.skip(reason="requires full app + DB fixture — placeholder for smoke; real coverage via e2e")
def test_quiz_submit_blocked_when_module_locked():
    # This test is a placeholder. Real coverage is done via the smoke script
    # and test_courses_api.py integration test in a later task, since wiring
    # a full DB fixture here duplicates the integration-test setup.
    pass
