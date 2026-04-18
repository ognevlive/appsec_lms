"""Load tasks and courses from YAML files into the database."""
import asyncio
import glob
import os
import re
import sys
import unicodedata

import yaml
from sqlalchemy import delete, select

from database import async_session, engine
from models import Base, Course, Module, ModuleUnit, Task, TaskType


_CYRILLIC_MAP = str.maketrans({
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z',
    'и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
    'с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'c','ч':'ch','ш':'sh','щ':'sch',
    'ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
    'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Е':'E','Ё':'E','Ж':'Zh','З':'Z',
    'И':'I','Й':'Y','К':'K','Л':'L','М':'M','Н':'N','О':'O','П':'P','Р':'R',
    'С':'S','Т':'T','У':'U','Ф':'F','Х':'H','Ц':'C','Ч':'Ch','Ш':'Sh','Щ':'Sch',
    'Ъ':'','Ы':'Y','Ь':'','Э':'E','Ю':'Yu','Я':'Ya',
})


def slugify(text: str) -> str:
    text = text.translate(_CYRILLIC_MAP)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:150] or "task"


async def seed_tasks(tasks_dir: str = "/tasks"):
    # Tables are managed by alembic in production, but in the seed CLI we still
    # ensure metadata is present (create_all is a no-op on already-migrated DB).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    task_patterns = [
        os.path.join(tasks_dir, "quizzes", "*.yaml"),
        os.path.join(tasks_dir, "ctf", "*", "task.yaml"),
        os.path.join(tasks_dir, "theory", "*.yaml"),
    ]

    files: list[str] = []
    for pattern in task_patterns:
        files.extend(glob.glob(pattern))

    if files:
        async with async_session() as db:
            for filepath in sorted(files):
                with open(filepath) as f:
                    data = yaml.safe_load(f)

                title = data["title"]
                task_type = TaskType(data["type"])
                slug = data.get("slug") or slugify(title)
                config = data.get("config", {})

                existing = (await db.execute(
                    select(Task).where(Task.title == title)
                )).scalar_one_or_none()

                if existing:
                    existing.description = data.get("description", "")
                    existing.type = task_type
                    existing.config = config
                    existing.order = data.get("order", 0)
                    if not existing.slug:
                        existing.slug = slug
                    print(f"  Updated: {title}")
                else:
                    db.add(Task(
                        title=title,
                        slug=slug,
                        description=data.get("description", ""),
                        type=task_type,
                        config=config,
                        order=data.get("order", 0),
                    ))
                    print(f"  Created: {title}")
            await db.commit()

    # Load courses
    course_files = glob.glob(os.path.join(tasks_dir, "courses", "*.yaml"))
    missing_slugs: list[str] = []
    if course_files:
        async with async_session() as db:
            for filepath in sorted(course_files):
                with open(filepath) as f:
                    data = yaml.safe_load(f)

                slug = data["slug"]
                course = (await db.execute(
                    select(Course).where(Course.slug == slug)
                )).scalar_one_or_none()

                if course:
                    course.title = data["title"]
                    course.description = data.get("description", "")
                    course.order = data.get("order", 0)
                    course.config = data.get("config", {})
                    print(f"  Updated course: {data['title']}")
                else:
                    course = Course(
                        title=data["title"],
                        slug=slug,
                        description=data.get("description", ""),
                        order=data.get("order", 0),
                        config=data.get("config", {}),
                    )
                    db.add(course)
                    await db.flush()
                    print(f"  Created course: {data['title']}")

                # Rebuild modules from scratch (cascades to module_units)
                await db.execute(delete(Module).where(Module.course_id == course.id))
                await db.flush()

                for mod_data in data.get("modules", []):
                    module = Module(
                        course_id=course.id,
                        title=mod_data["title"],
                        description=mod_data.get("description", ""),
                        order=mod_data["order"],
                        estimated_hours=mod_data.get("estimated_hours"),
                        learning_outcomes=mod_data.get("learning_outcomes", []),
                        config=mod_data.get("config", {}),
                    )
                    db.add(module)
                    await db.flush()

                    for unit_data in mod_data.get("units", []):
                        task_slug = unit_data["task_slug"]
                        task = (await db.execute(
                            select(Task).where(Task.slug == task_slug)
                        )).scalar_one_or_none()
                        if not task:
                            missing_slugs.append(task_slug)
                            print(f"    WARNING: task slug not found: {task_slug}")
                            continue
                        db.add(ModuleUnit(
                            module_id=module.id,
                            task_id=task.id,
                            unit_order=unit_data.get("order", 0),
                            is_required=unit_data.get("required", True),
                        ))
            await db.commit()

    if missing_slugs:
        print(
            f"WARNING: {len(missing_slugs)} task slug(s) referenced from course YAML "
            f"were not found in DB: {sorted(set(missing_slugs))}"
        )

    print("Done!")


if __name__ == "__main__":
    tasks_dir = sys.argv[1] if len(sys.argv) > 1 else "/tasks"
    asyncio.run(seed_tasks(tasks_dir))
