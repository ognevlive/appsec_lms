from dataclasses import dataclass
from services.progression import is_module_locked


@dataclass
class FakeUnit:
    task_id: int
    is_required: bool = True


@dataclass
class FakeModule:
    order: int
    units: list[FakeUnit]


@dataclass
class FakeCourse:
    config: dict
    modules: list[FakeModule]


def test_free_course_never_locks():
    course = FakeCourse(
        config={"progression": "free"},
        modules=[
            FakeModule(order=1, units=[FakeUnit(1)]),
            FakeModule(order=2, units=[FakeUnit(2)]),
        ],
    )
    assert is_module_locked(course, course.modules[0], {}) is False
    assert is_module_locked(course, course.modules[1], {}) is False


def test_missing_progression_defaults_to_free():
    course = FakeCourse(
        config={},
        modules=[FakeModule(order=1, units=[]), FakeModule(order=2, units=[FakeUnit(9)])],
    )
    assert is_module_locked(course, course.modules[1], {}) is False


def test_linear_first_module_is_open():
    course = FakeCourse(
        config={"progression": "linear"},
        modules=[FakeModule(order=1, units=[FakeUnit(1)])],
    )
    assert is_module_locked(course, course.modules[0], {}) is False


def test_linear_locked_when_prev_required_unit_unfinished():
    course = FakeCourse(
        config={"progression": "linear"},
        modules=[
            FakeModule(order=1, units=[FakeUnit(1), FakeUnit(2)]),
            FakeModule(order=2, units=[FakeUnit(3)]),
        ],
    )
    # unit 1 success, unit 2 fail
    statuses = {1: "success", 2: "fail"}
    assert is_module_locked(course, course.modules[1], statuses) is True


def test_linear_unlocked_when_all_prev_required_success():
    course = FakeCourse(
        config={"progression": "linear"},
        modules=[
            FakeModule(order=1, units=[FakeUnit(1), FakeUnit(2)]),
            FakeModule(order=2, units=[FakeUnit(3)]),
        ],
    )
    statuses = {1: "success", 2: "success"}
    assert is_module_locked(course, course.modules[1], statuses) is False


def test_linear_non_required_ignored():
    course = FakeCourse(
        config={"progression": "linear"},
        modules=[
            FakeModule(order=1, units=[FakeUnit(1, is_required=True), FakeUnit(2, is_required=False)]),
            FakeModule(order=2, units=[FakeUnit(3)]),
        ],
    )
    statuses = {1: "success"}  # unit 2 (non-required) not touched
    assert is_module_locked(course, course.modules[1], statuses) is False


def test_linear_pending_counts_as_locked():
    course = FakeCourse(
        config={"progression": "linear"},
        modules=[
            FakeModule(order=1, units=[FakeUnit(1)]),
            FakeModule(order=2, units=[FakeUnit(2)]),
        ],
    )
    statuses = {1: "pending"}
    assert is_module_locked(course, course.modules[1], statuses) is True
