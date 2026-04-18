"""Admin CRUD for courses, modules, units, tasks + import/export.

Защищён require_admin. Все endpoints под /api/admin/content.
"""
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import require_admin
from database import get_db
from models import Course, Module, ModuleUnit, Task, TaskType, User
from schemas_admin import (
    CourseCreate,
    CourseUpdate,
    ModuleCreate,
    ModuleUpdate,
    ReorderItem,
    TaskCreate,
    TaskOutAdmin,
    TaskUpdate,
    UnitCreate,
    UnitUpdate,
)
from services.bundle import (
    BundleError,
    list_task_files,
    open_bundle,
    pack_course,
    pack_task,
    read_yaml,
)
from services.flag_hash import apply_flag_to_config

router = APIRouter(
    prefix="/api/admin/content",
    tags=["admin-content"],
    dependencies=[Depends(require_admin)],
)


def _task_out(task: Task, usage: list[dict] | None = None) -> dict:
    return {
        "id": task.id,
        "slug": task.slug,
        "title": task.title,
        "description": task.description or "",
        "order": task.order,
        "type": task.type,
        "config": task.config or {},
        "author_id": task.author_id,
        "updated_at": task.updated_at,
        "usage": usage or [],
    }


class CourseOutAdmin(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    order: int
    config: dict
    is_visible: bool

    model_config = ConfigDict(from_attributes=True)


@router.post("/courses", status_code=201, response_model=CourseOutAdmin)
async def create_course(body: CourseCreate, db: AsyncSession = Depends(get_db)):
    course = Course(
        slug=body.slug, title=body.title, description=body.description,
        order=body.order, config=body.config, is_visible=False,
    )
    db.add(course)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Slug already exists")
    await db.refresh(course)
    return course


@router.get("/courses", response_model=list[CourseOutAdmin])
async def list_courses_admin(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(Course).order_by(Course.order, Course.id))
    return rows.scalars().all()


@router.patch("/courses/{course_id}", response_model=CourseOutAdmin)
async def update_course(course_id: int, body: CourseUpdate,
                         db: AsyncSession = Depends(get_db)):
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(course, k, v)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Slug already exists")
    await db.refresh(course)
    return course


@router.delete("/courses/{course_id}", status_code=204)
async def delete_course(course_id: int, db: AsyncSession = Depends(get_db)):
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    if course.is_visible:
        raise HTTPException(409, "Course must be hidden before deletion")
    await db.delete(course)
    await db.commit()


class ModuleOutAdmin(BaseModel):
    id: int
    course_id: int
    title: str
    description: str
    order: int
    estimated_hours: int | None
    learning_outcomes: list[str]
    config: dict

    model_config = ConfigDict(from_attributes=True)


class UnitOutAdmin(BaseModel):
    id: int
    module_id: int
    task_id: int
    unit_order: int
    is_required: bool

    model_config = ConfigDict(from_attributes=True)


@router.post("/courses/{course_id}/modules", status_code=201, response_model=ModuleOutAdmin)
async def create_module(course_id: int, body: ModuleCreate,
                         db: AsyncSession = Depends(get_db)):
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    m = Module(course_id=course_id, **body.model_dump())
    db.add(m)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Duplicate module order in this course")
    await db.refresh(m)
    return m


@router.patch("/modules/{module_id}", response_model=ModuleOutAdmin)
async def update_module(module_id: int, body: ModuleUpdate,
                         db: AsyncSession = Depends(get_db)):
    m = await db.get(Module, module_id)
    if not m:
        raise HTTPException(404, "Module not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Duplicate module order")
    await db.refresh(m)
    return m


@router.delete("/modules/{module_id}", status_code=204)
async def delete_module(module_id: int, db: AsyncSession = Depends(get_db)):
    m = await db.get(Module, module_id)
    if not m:
        raise HTTPException(404, "Module not found")
    await db.delete(m)
    await db.commit()


@router.post("/courses/{course_id}/reorder-modules")
async def reorder_modules(course_id: int, items: list[ReorderItem],
                           db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(Module).where(Module.course_id == course_id))
    by_id = {m.id: m for m in rows.scalars().all()}
    for i, it in enumerate(items):
        m = by_id.get(it.id)
        if not m:
            raise HTTPException(400, f"Module {it.id} not in course {course_id}")
        m.order = -(i + 1)
    await db.flush()
    for it in items:
        by_id[it.id].order = it.order
    await db.commit()
    return {"ok": True}


@router.post("/modules/{module_id}/units", status_code=201, response_model=UnitOutAdmin)
async def create_unit(module_id: int, body: UnitCreate,
                       db: AsyncSession = Depends(get_db)):
    m = await db.get(Module, module_id)
    if not m:
        raise HTTPException(404, "Module not found")
    task = await db.get(Task, body.task_id)
    if not task:
        raise HTTPException(400, f"Task {body.task_id} not found")
    u = ModuleUnit(module_id=module_id, **body.model_dump())
    db.add(u)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Task already in this module")
    await db.refresh(u)
    return u


@router.patch("/units/{unit_id}", response_model=UnitOutAdmin)
async def update_unit(unit_id: int, body: UnitUpdate,
                       db: AsyncSession = Depends(get_db)):
    u = await db.get(ModuleUnit, unit_id)
    if not u:
        raise HTTPException(404, "Unit not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(u, k, v)
    await db.commit()
    await db.refresh(u)
    return u


@router.delete("/units/{unit_id}", status_code=204)
async def delete_unit(unit_id: int, db: AsyncSession = Depends(get_db)):
    u = await db.get(ModuleUnit, unit_id)
    if not u:
        raise HTTPException(404, "Unit not found")
    await db.delete(u)
    await db.commit()


@router.post("/modules/{module_id}/reorder-units")
async def reorder_units(module_id: int, items: list[ReorderItem],
                         db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(ModuleUnit).where(ModuleUnit.module_id == module_id))
    by_id = {u.id: u for u in rows.scalars().all()}
    for i, it in enumerate(items):
        u = by_id.get(it.id)
        if not u:
            raise HTTPException(400, f"Unit {it.id} not in module {module_id}")
        u.unit_order = -(i + 1)
    await db.flush()
    for it in items:
        by_id[it.id].unit_order = it.order
    await db.commit()
    return {"ok": True}


@router.get("/tasks", response_model=list[TaskOutAdmin])
async def list_tasks(
    type: TaskType | None = None,
    search: str | None = None,
    unused: bool = False,
    db: AsyncSession = Depends(get_db),
):
    q = select(Task)
    if type is not None:
        q = q.where(Task.type == type)
    if search:
        like = f"%{search}%"
        q = q.where(or_(Task.title.ilike(like), Task.slug.ilike(like)))
    if unused:
        used_ids = select(ModuleUnit.task_id).distinct()
        q = q.where(Task.id.notin_(used_ids))
    q = q.order_by(Task.updated_at.desc())
    result = await db.execute(q)
    return [_task_out(t) for t in result.scalars().all()]


@router.post("/tasks", status_code=status.HTTP_201_CREATED, response_model=TaskOutAdmin)
async def create_task(
    body: TaskCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    config = apply_flag_to_config(body.config or {})
    task = Task(
        slug=body.slug,
        title=body.title,
        description=body.description,
        order=body.order,
        type=body.type,
        config=config,
        author_id=admin.id,
    )
    db.add(task)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Slug already exists")
    await db.refresh(task)
    return _task_out(task)


async def _usage_for_task(task_id: int, db: AsyncSession) -> list[dict]:
    rows = await db.execute(
        select(Course.id, Course.slug, Module.id, ModuleUnit.id)
        .join(Module, Module.course_id == Course.id)
        .join(ModuleUnit, ModuleUnit.module_id == Module.id)
        .where(ModuleUnit.task_id == task_id)
    )
    return [
        {"course_id": c_id, "course_slug": c_slug, "module_id": m_id, "unit_id": u_id}
        for c_id, c_slug, m_id, u_id in rows.all()
    ]


@router.get("/tasks/{task_id}", response_model=TaskOutAdmin)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return _task_out(task, usage=await _usage_for_task(task_id, db))


@router.patch("/tasks/{task_id}", response_model=TaskOutAdmin)
async def update_task(
    task_id: int,
    body: TaskUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    data = body.model_dump(exclude_unset=True)
    if "config" in data:
        data["config"] = apply_flag_to_config(data["config"])
    for field, value in data.items():
        setattr(task, field, value)
    task.author_id = admin.id
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Slug already exists")
    await db.refresh(task)
    return _task_out(task, usage=await _usage_for_task(task_id, db))


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    usage = await _usage_for_task(task_id, db)
    if usage:
        raise HTTPException(status_code=409, detail={"message": "Task is in use", "usage": usage})
    await db.delete(task)
    await db.commit()


def _task_manifest(task: Task) -> dict:
    return {
        "slug": task.slug,
        "title": task.title,
        "description": task.description or "",
        "type": task.type.value,
        "order": task.order,
        "config": task.config or {},
    }


@router.get("/tasks/{task_id}/export")
async def export_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    blob = pack_task(_task_manifest(task))
    return Response(
        content=blob,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="task-{task.slug}.zip"'},
    )


async def _upsert_task_from_manifest(manifest: dict, admin_id: int,
                                       db: AsyncSession) -> Task:
    try:
        parsed = TaskCreate.model_validate(manifest)
    except ValidationError as e:
        raise HTTPException(422, f"Invalid task manifest: {e}")
    cfg = apply_flag_to_config(parsed.config or {})
    existing = await db.execute(select(Task).where(Task.slug == parsed.slug))
    task = existing.scalar_one_or_none()
    if task:
        task.title = parsed.title
        task.description = parsed.description
        task.order = parsed.order
        task.type = parsed.type
        task.config = cfg
        task.author_id = admin_id
    else:
        task = Task(
            slug=parsed.slug, title=parsed.title, description=parsed.description,
            order=parsed.order, type=parsed.type, config=cfg, author_id=admin_id,
        )
        db.add(task)
    return task


@router.post("/tasks/import", status_code=201, response_model=TaskOutAdmin)
async def import_task(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    raw = await file.read()
    try:
        zf = open_bundle(raw)
        manifest = read_yaml(zf, "manifest.yaml")
    except BundleError as e:
        raise HTTPException(400, str(e))
    task = await _upsert_task_from_manifest(manifest, admin.id, db)
    await db.commit()
    await db.refresh(task)
    return _task_out(task)


def _module_manifest(m: Module) -> dict:
    return {
        "title": m.title,
        "order": m.order,
        "description": m.description or "",
        "estimated_hours": m.estimated_hours,
        "learning_outcomes": m.learning_outcomes or [],
        "config": m.config or {},
        "units": [
            {"task_slug": u.task.slug, "unit_order": u.unit_order,
             "is_required": u.is_required}
            for u in sorted(m.units, key=lambda x: x.unit_order)
        ],
    }


def _course_manifest(course: Course) -> dict:
    return {
        "slug": course.slug,
        "title": course.title,
        "description": course.description or "",
        "order": course.order,
        "config": course.config or {},
        "modules": [_module_manifest(m) for m in sorted(course.modules, key=lambda x: x.order)],
    }


@router.get("/courses/{course_id}/export")
async def export_course(course_id: int, bundle: bool = False,
                         db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(Course)
        .options(selectinload(Course.modules)
                 .selectinload(Module.units)
                 .selectinload(ModuleUnit.task))
        .where(Course.id == course_id)
    )
    course = rows.scalars().unique().one_or_none()
    if not course:
        raise HTTPException(404, "Course not found")

    tasks_manifest: dict[str, dict] = {}
    if bundle:
        for m in course.modules:
            for u in m.units:
                tasks_manifest[u.task.slug] = _task_manifest(u.task)

    blob = pack_course(_course_manifest(course), tasks_manifest)
    return Response(
        content=blob, media_type="application/zip",
        headers={"Content-Disposition":
                 f'attachment; filename="course-{course.slug}.zip"'},
    )


@router.post("/courses/import", status_code=201, response_model=CourseOutAdmin)
async def import_course(
    file: UploadFile = File(...),
    import_tasks: bool = False,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    raw = await file.read()
    try:
        zf = open_bundle(raw)
        course_data = read_yaml(zf, "course.yaml")
    except BundleError as e:
        raise HTTPException(400, str(e))

    # Опционально импортируем таски ПЕРЕД курсом — нужны для resolve task_slug → task_id
    if import_tasks:
        for name in list_task_files(zf):
            m = read_yaml(zf, name)
            await _upsert_task_from_manifest(m, admin.id, db)
        await db.flush()

    # Resolve task_slug → task_id
    referenced_slugs: set[str] = set()
    for m in course_data.get("modules", []):
        for u in m.get("units", []):
            referenced_slugs.add(u["task_slug"])
    rows = await db.execute(select(Task.slug, Task.id).where(Task.slug.in_(referenced_slugs)))
    slug_to_id = dict(rows.all())
    missing = referenced_slugs - set(slug_to_id)
    if missing:
        await db.rollback()
        raise HTTPException(400, f"Missing tasks: {', '.join(sorted(missing))}")

    # Upsert course (UPDATE если slug уже есть, CREATE иначе)
    existing = await db.execute(
        select(Course)
        .options(selectinload(Course.modules).selectinload(Module.units))
        .where(Course.slug == course_data["slug"])
    )
    course = existing.scalars().unique().one_or_none()
    if course:
        # сносим старые модули — ON DELETE CASCADE удалит юниты
        for m in list(course.modules):
            await db.delete(m)
        course.title = course_data["title"]
        course.description = course_data.get("description", "")
        course.order = course_data.get("order", 0)
        course.config = course_data.get("config", {})
        # is_visible при импорте всегда False (спека, секция 4)
        course.is_visible = False
    else:
        course = Course(
            slug=course_data["slug"], title=course_data["title"],
            description=course_data.get("description", ""),
            order=course_data.get("order", 0),
            config=course_data.get("config", {}),
            is_visible=False,
        )
        db.add(course)
    await db.flush()

    for m_data in course_data.get("modules", []):
        module = Module(
            course_id=course.id, title=m_data["title"], order=m_data["order"],
            description=m_data.get("description", ""),
            estimated_hours=m_data.get("estimated_hours"),
            learning_outcomes=m_data.get("learning_outcomes", []),
            config=m_data.get("config", {}),
        )
        db.add(module)
        await db.flush()
        for u_data in m_data.get("units", []):
            db.add(ModuleUnit(
                module_id=module.id,
                task_id=slug_to_id[u_data["task_slug"]],
                unit_order=u_data.get("unit_order", 0),
                is_required=u_data.get("is_required", True),
            ))
    await db.commit()
    await db.refresh(course)
    return course
