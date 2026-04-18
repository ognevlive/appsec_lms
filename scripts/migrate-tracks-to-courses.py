#!/usr/bin/env python3
"""One-shot: convert tasks/tracks/*.yaml into tasks/courses/*.yaml with explicit modules.

Logic:
  - Read each tasks/tracks/*.yaml
  - Scan the raw source for '# ── Модуль N: <title> ──' comment separators
    (accepts — and - as well). Each separator starts a new module.
  - If no separators found, wrap all steps in a single "Основы" module.
  - Each unit gets a task_slug (generated from task_title if Task.slug is unknown).
  - Placeholder estimated_hours (null) and empty learning_outcomes.
  - Writes tasks/courses/<slug>.yaml (overwrites). Script is idempotent.
"""
import glob
import os
import re
import sys
import unicodedata

import yaml

SEPARATOR_RE = re.compile(r"#\s*[─—\-]+\s*Модуль\s+\d+:\s*(.+?)\s*[─—\-]+\s*$")


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


def parse_modules_from_source(source: str, steps: list[dict]) -> list[dict]:
    """Use the raw YAML text to detect '# ── Модуль N: <title> ──' separators
    and partition `steps` into modules accordingly.
    """
    if not steps:
        return []

    lines = source.splitlines()
    current_module_title: str | None = None
    modules: list[dict] = []
    current_module: dict | None = None
    step_idx = 0

    title_re = re.compile(r'^\s*-\s*task_title:\s*"([^"]+)"')

    for line in lines:
        sep = SEPARATOR_RE.search(line)
        if sep:
            current_module_title = sep.group(1).strip()
            current_module = {
                "title": current_module_title,
                "order": len(modules) + 1,
                "estimated_hours": None,
                "learning_outcomes": [],
                "units": [],
            }
            modules.append(current_module)
            continue

        m = title_re.search(line)
        if m and step_idx < len(steps):
            step = steps[step_idx]
            step_idx += 1
            if current_module is None:
                current_module = {
                    "title": "Основы",
                    "order": 1,
                    "estimated_hours": None,
                    "learning_outcomes": [],
                    "units": [],
                }
                modules.append(current_module)
            current_module["units"].append({
                "task_slug": slugify(step["task_title"]),
                "task_title": step["task_title"],
                "order": len(current_module["units"]) + 1,
                "required": step.get("required", True),
            })

    if not modules:
        modules = [{
            "title": "Основы",
            "order": 1,
            "estimated_hours": None,
            "learning_outcomes": [],
            "units": [
                {
                    "task_slug": slugify(s["task_title"]),
                    "task_title": s["task_title"],
                    "order": s.get("order", i + 1),
                    "required": True,
                }
                for i, s in enumerate(steps)
            ],
        }]
    return modules


def strip_debug_fields(modules: list[dict]) -> list[dict]:
    for m in modules:
        for u in m["units"]:
            u.pop("task_title", None)
    return modules


def convert(src_path: str, dst_dir: str) -> str:
    with open(src_path) as f:
        source = f.read()
    data = yaml.safe_load(source)

    modules = parse_modules_from_source(source, data.get("steps", []))
    modules = strip_debug_fields(modules)

    out = {
        "title": data["title"],
        "slug": data["slug"],
        "description": data.get("description", ""),
        "order": data.get("order", 0),
        "config": data.get("config", {}),
        "modules": modules,
    }

    dst = os.path.join(dst_dir, f"{data['slug']}.yaml")
    with open(dst, "w") as f:
        yaml.safe_dump(out, f, allow_unicode=True, sort_keys=False)
    return dst


def main(argv: list[str]) -> int:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tracks_dir = os.path.join(repo_root, "tasks", "tracks")
    courses_dir = os.path.join(repo_root, "tasks", "courses")
    os.makedirs(courses_dir, exist_ok=True)

    files = sorted(glob.glob(os.path.join(tracks_dir, "*.yaml")))
    if not files:
        print(f"No track YAMLs in {tracks_dir}", file=sys.stderr)
        return 1

    for src in files:
        dst = convert(src, courses_dir)
        print(f"  {os.path.basename(src)} -> {os.path.basename(dst)}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
