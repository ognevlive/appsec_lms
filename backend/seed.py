"""Load tasks and tracks from YAML files into the database."""
import asyncio
import glob
import hashlib
import os
import sys

import yaml
from sqlalchemy import select, delete

from database import async_session, engine
from models import Base, Task, TaskType, Track, TrackStep


async def seed_tasks(tasks_dir: str = "/tasks"):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    patterns = [
        os.path.join(tasks_dir, "quizzes", "*.yaml"),
        os.path.join(tasks_dir, "ctf", "*", "task.yaml"),
        os.path.join(tasks_dir, "theory", "*.yaml"),
    ]

    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))

    if not files:
        print(f"No task files found in {tasks_dir}")
        return

    async with async_session() as db:
        for filepath in sorted(files):
            with open(filepath) as f:
                data = yaml.safe_load(f)

            title = data["title"]
            task_type = TaskType(data["type"])

            # Check if task already exists
            result = await db.execute(select(Task).where(Task.title == title))
            existing = result.scalar_one_or_none()

            config = data.get("config", {})

            if existing:
                existing.description = data.get("description", "")
                existing.type = task_type
                existing.config = config
                existing.order = data.get("order", 0)
                print(f"  Updated: {title}")
            else:
                task = Task(
                    title=title,
                    description=data.get("description", ""),
                    type=task_type,
                    config=config,
                    order=data.get("order", 0),
                )
                db.add(task)
                print(f"  Created: {title}")

        await db.commit()

    # Load tracks
    track_files = glob.glob(os.path.join(tasks_dir, "tracks", "*.yaml"))
    if track_files:
        async with async_session() as db:
            for filepath in sorted(track_files):
                with open(filepath) as f:
                    data = yaml.safe_load(f)

                slug = data["slug"]
                result = await db.execute(select(Track).where(Track.slug == slug))
                track = result.scalar_one_or_none()

                if track:
                    track.title = data["title"]
                    track.description = data.get("description", "")
                    track.order = data.get("order", 0)
                    track.config = data.get("config", {})
                    print(f"  Updated track: {data['title']}")
                else:
                    track = Track(
                        title=data["title"],
                        slug=slug,
                        description=data.get("description", ""),
                        order=data.get("order", 0),
                        config=data.get("config", {}),
                    )
                    db.add(track)
                    await db.flush()
                    print(f"  Created track: {data['title']}")

                # Rebuild steps
                await db.execute(delete(TrackStep).where(TrackStep.track_id == track.id))

                for step_data in data.get("steps", []):
                    task_result = await db.execute(
                        select(Task).where(Task.title == step_data["task_title"])
                    )
                    task = task_result.scalar_one_or_none()
                    if not task:
                        print(f"    WARNING: task not found: {step_data['task_title']}")
                        continue
                    db.add(TrackStep(
                        track_id=track.id,
                        task_id=task.id,
                        step_order=step_data.get("order", 0),
                    ))

            await db.commit()

    print("Done!")


if __name__ == "__main__":
    tasks_dir = sys.argv[1] if len(sys.argv) > 1 else "/tasks"
    asyncio.run(seed_tasks(tasks_dir))
