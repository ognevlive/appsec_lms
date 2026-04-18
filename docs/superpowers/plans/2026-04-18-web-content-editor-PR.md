# PR: Web Content Editor — admin UI for courses/modules/units/tasks

Branch: `claude/nostalgic-morse-05a01b` → `main`
Commits: 39
Plan: `docs/superpowers/plans/2026-04-18-web-content-editor.md`

---

## BREAKING CHANGE: Content migration required before merge

Эта ветка переводит источник правды контента из YAML-файлов (`tasks/`) в БД.
Папка `tasks/` и seed-скрипты удалены.

**Каждому оператору на каждом инстансе (prod/staging/dev) перед pull этой ветки:**

1. `./scripts/deploy-labs.sh --seed` — залить текущий YAML-контент в БД
2. Сделать backup БД: `docker compose exec postgres pg_dump -U lms lms > backup.sql`
3. Pull этой ветки + `docker compose up --build -d`
4. Миграция накатится автоматически на старте backend

После этого ВЕСЬ контент (курсы, модули, юниты, таски) редактируется через
`/admin/courses` и `/admin/tasks`.

---

## Summary

- **Backend (Phases 1–8, Tasks 1–18):** новый router `/api/admin/content/*` с CRUD
  для tasks/courses/modules/units, reorder, ZIP-импорт/экспорт (зашита от zip-slip
  + 10MB cap), SHA-256 хэширование флагов (write-only plaintext), guard на удаление
  visible-курсов и used-тасков, фильтр `is_visible` для студенческих эндпоинтов.
- **Frontend (Phase 9, Tasks 19–28):** добавлены `@dnd-kit/*`, страницы
  `/admin/courses`, `/admin/tasks`, редакторы курса (с DnD-сортировкой модулей и
  юнитов + TaskPicker модалка) и таска (type-specific формы для theory/quiz/ctf/
  ssh_lab/gitlab + write-only flag UI).
- **Cleanup (Phase 10, Tasks 29–32):** удалены `seed.py`, `deploy-labs.sh`,
  `migrate-tracks-to-courses.py`, папка `tasks/`. README переписан под админ-UI.
  smoke-course-flow.sh расширен админ-CRUD секцией.

## Test plan

- [x] Backend pytest: **63 passed, 1 skipped** (запуск через сиблинг-worktree
      с docker, на синхронизированной кодовой базе ветки)
- [x] Frontend `npm run build`: **success** (338 modules, 475.81 kB → 140.50 kB gzip)
- [x] Alembic upgrade head на реальном Postgres: success
- [x] Smoke script bash syntax: OK (runtime end-to-end test not executed —
      см. concerns в коммите `cac5276`)
- [ ] Manual UI walkthrough (рекомендуется ревьюверу): создать курс → модуль →
      юнит → опубликовать → проверить student view → экспорт-bundle → re-import
- [ ] Чистая БД миграция (`docker compose down -v && up --build`)

## Architectural decisions

- **Last-write-wins** для конкурентных правок: никаких version-полей,
  draft-режима, audit log (out of scope per plan).
- **Plaintext flag — write-only:** SECURITY CONTRACT в `schemas_admin.py`,
  централизован в `services/flag_hash.py`, никогда не попадает в Task.config
  ни в БД, ни в API responses.
- **ZIP bundles:** safe extraction (zip-slip refusal, abs path refusal, 10MB
  cap), формат — YAML внутри zip; `import_tasks=true` для course bundle
  включает referenced таски.
- **DnD reorder:** оптимистичный update + rollback на ошибке (cd72e39).
  Двухфазная reorder-транзакция на бэке для обхода UNIQUE(course_id, order).

## Files changed (high level)

- `backend/routers/admin_content.py` — новый router (~640 строк)
- `backend/schemas_admin.py`, `services/{bundle,flag_hash,slug}.py` — поддержка
- `backend/alembic/versions/0004_course_visibility_task_audit.py` — миграция
- `frontend/src/pages/admin/{AdminCoursesPage,AdminTasksPage,CourseEditorPage,TaskEditorPage}.tsx`
- `frontend/src/components/admin/{ModuleCard,UnitRow,TaskPicker,MarkdownEditor,task-forms/*}.tsx`
- `frontend/src/api.ts`, `types.ts`, `main.tsx` (роутинг + sidebar)
- README.md, scripts/smoke-course-flow.sh — обновлены под новый флоу
- ❌ Удалено: `backend/seed.py`, `tests/test_seed_courses.py`,
  `scripts/deploy-labs.sh`, `scripts/migrate-tracks-to-courses.py`, `tasks/`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
