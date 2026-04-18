"""Progression gating logic for Course -> Module -> Unit hierarchy."""
from typing import Any


def is_module_locked(course: Any, module: Any, user_statuses: dict[int, str]) -> bool:
    """Return True if `module` is locked for a user with the given submission statuses.

    `course` and `module` are ORM-like objects with the attributes accessed below.
    `user_statuses` maps task_id -> best submission status ("success"|"fail"|"pending").
    """
    progression = (course.config or {}).get("progression", "free")
    if progression != "linear":
        return False

    for prev in course.modules:
        if prev.order >= module.order:
            continue
        for unit in prev.units:
            if not unit.is_required:
                continue
            if user_statuses.get(unit.task_id) != "success":
                return True
    return False
