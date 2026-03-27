# LMS AppSec

Учебная платформа для обучения безопасной разработке. Студенты решают задачи трёх типов: тесты (Quiz), практические CTF-задания в изолированных контейнерах и задания на работу с GitLab. Стек: FastAPI + PostgreSQL + React/Vite + Traefik, всё поднимается через Docker Compose.

---

## Архитектура

```
                    ┌─────────────────────────────────┐
  HTTP :80          │           Traefik v3.1            │
  Dashboard :8080   │     (reverse proxy + routing)     │
                    └──────────┬──────────┬────────────┘
                               │          │
                    ┌──────────▼──┐  ┌────▼────────────┐
                    │  frontend   │  │    backend       │
                    │ React 18    │  │  FastAPI 0.115   │
                    │ Vite + TW   │  │  SQLAlchemy async│
                    └─────────────┘  └────┬────────────┘
                                          │
                               ┌──────────▼──────────┐
                               │   postgres:16-alpine  │
                               │   (volume: pg_data)   │
                               └──────────────────────┘
                                          │
                               ┌──────────▼──────────┐
                               │   CTF-контейнеры     │
                               │  (lms/{task_name})   │
                               │  создаются динамич.  │
                               └──────────────────────┘
```

**Маршрутизация Traefik:**
- `lms.lab.local/` → frontend:3000
- `lms.lab.local/api` → backend:8000
- `{task}-{user_id}.lab.local` → CTF-контейнер студента

---

## Требования

- **Docker** >= 24 и **Docker Compose** v2 (`docker compose`, не `docker-compose`)
- **Bash** >= 4 (macOS: через `brew install bash`)
- **Порт 80** свободен на хосте
- **DNS**: все запросы к `*.lab.local` должны разрешаться в `127.0.0.1`

---

## Настройка DNS

### macOS / Linux

```bash
sudo bash -c 'cat >> /etc/hosts << EOF

# LMS AppSec
127.0.0.1  lms.lab.local
EOF'
```

Для CTF-заданий каждый запущенный контейнер получает уникальный поддомен вида `sqli-basic-3.lab.local`. Чтобы не добавлять их вручную, используйте локальный DNS-резолвер:

```bash
# macOS — через dnsmasq (homebrew)
brew install dnsmasq
echo 'address=/.lab.local/127.0.0.1' >> /opt/homebrew/etc/dnsmasq.conf
sudo brew services start dnsmasq

# Добавить резолвер
sudo mkdir -p /etc/resolver
echo 'nameserver 127.0.0.1' | sudo tee /etc/resolver/lab.local
```

### Windows

Открыть `C:\Windows\System32\drivers\etc\hosts` от имени администратора и добавить:
```
127.0.0.1  lms.lab.local
```

---

## Переменные окружения

Файл `.env` уже содержит значения для локального запуска. Перед продакшн-деплоем замените:

| Переменная | Описание | Значение по умолчанию |
|---|---|---|
| `POSTGRES_USER` | Пользователь БД | `lms` |
| `POSTGRES_PASSWORD` | Пароль БД | `lms_secret_change_me` |
| `POSTGRES_DB` | Имя базы | `lms` |
| `DATABASE_URL` | Строка подключения (должна совпадать с учётными данными выше) | `postgresql+asyncpg://lms:lms_secret_change_me@postgres:5432/lms` |
| `JWT_SECRET` | Секрет для подписи токенов — **обязательно сменить** | `change-me-to-random-secret-key` |
| `JWT_EXPIRE_MINUTES` | Время жизни JWT-токена в минутах | `480` |
| `DOMAIN` | Базовый домен | `lab.local` |
| `TRAEFIK_NETWORK` | Docker-сеть для Traefik | `lms_network` |
| `GITLAB_URL` | URL GitLab-инстанса (опционально) | — |
| `GITLAB_ADMIN_TOKEN` | Токен администратора GitLab (опционально) | — |

Сгенерировать безопасный `JWT_SECRET`:
```bash
openssl rand -hex 32
```

---

## Быстрый старт

```bash
# 1. Поднять все сервисы (Traefik, PostgreSQL, backend, frontend)
docker compose up --build -d

# 2. Дождаться готовности backend (healthcheck postgres занимает ~10 сек)
docker compose logs -f backend

# 3. Собрать CTF-образы и залить задания в БД
./scripts/deploy-labs.sh

# 4. Открыть платформу
open http://lms.lab.local
```

После этого доступны:

| URL | Что |
|---|---|
| `http://lms.lab.local` | Фронтенд (каталог заданий) |
| `http://lms.lab.local/api/docs` | Swagger UI (интерактивная документация API) |
| `http://localhost:8080` | Traefik dashboard (маршруты, сервисы) |

**Дефолтная учётная запись администратора:** `admin` / `admin`
Сменить пароль сразу после первого входа.

---

## Скрипт deploy-labs.sh

Скрипт находится в `scripts/deploy-labs.sh`. Управляет тремя операциями:

```bash
./scripts/deploy-labs.sh              # полный цикл: hash → build → seed → summary
./scripts/deploy-labs.sh --hash       # вычислить SHA-256 флагов из Dockerfile/app.py, обновить task.yaml
./scripts/deploy-labs.sh --build      # только собрать Docker-образы CTF-заданий (lms/{task_name})
./scripts/deploy-labs.sh --seed       # только залить задания из task.yaml в БД
./scripts/deploy-labs.sh --summary    # вывести статистику: количество заданий, образы
```

**Когда запускать повторно:**
- После добавления нового CTF-задания в `tasks/ctf/`
- После изменения флага в Dockerfile (нужен `--hash` + `--build` + `--seed`)
- После сброса БД

---

## Структура проекта

```
lms/
├── backend/              # FastAPI-приложение
│   ├── main.py           # точка входа, lifespan (создание таблиц, планировщик)
│   ├── config.py         # настройки через Pydantic BaseSettings
│   ├── models.py         # ORM-модели: User, Task, TaskSubmission, ContainerInstance
│   ├── routers/          # эндпоинты по доменам (auth, tasks, ctf, quiz, admin, progress)
│   ├── services/         # бизнес-логика (docker_manager, scheduler, gitlab_client)
│   ├── seed.py           # скрипт заливки задач из task.yaml в БД
│   └── Dockerfile
├── frontend/             # React 18 + Vite + Tailwind CSS
│   ├── src/
│   │   ├── pages/        # страницы: Login, Catalog, Challenge, Results, Admin
│   │   ├── contexts/     # AuthContext (JWT-токен, роль пользователя)
│   │   └── api.ts        # HTTP-клиент ко всем эндпоинтам backend
│   └── Dockerfile
├── tasks/                # определения заданий (не в git, добавить вручную)
│   ├── ctf/
│   │   └── {task-name}/
│   │       ├── Dockerfile    # уязвимое приложение, содержит FLAG{...}
│   │       ├── task.yaml     # метаданные, flag_hash, TTL, автопроверки
│   │       └── app.py        # код задания
│   └── quizzes/
│       └── {quiz-name}.yaml  # вопросы и варианты ответов
├── scripts/
│   └── deploy-labs.sh    # сборка образов + seed БД
├── docker-compose.yml
└── .env
```

---

## Добавление нового CTF-задания

1. Создать директорию `tasks/ctf/{task-name}/`
2. Положить туда `Dockerfile` (с `FLAG{...}` внутри), `app.py`, `task.yaml`
3. Минимальный `task.yaml`:

```yaml
title: "Название задания"
description: "Описание"
type: ctf
order: 10
difficulty: medium
docker_image: lms/{task-name}
ttl_minutes: 120
flag_hash: ""   # заполнится автоматически через --hash
port: 5000      # порт внутри контейнера
```

4. Запустить:
```bash
./scripts/deploy-labs.sh
```

---

## Управление сервисами

```bash
# Статус
docker compose ps

# Логи конкретного сервиса
docker compose logs -f backend
docker compose logs -f frontend

# Перезапуск backend после изменений кода
docker compose restart backend

# Полный сброс (данные БД сохранятся в volume)
docker compose down && docker compose up -d

# Полный сброс с удалением данных БД
docker compose down -v && docker compose up --build -d && ./scripts/deploy-labs.sh
```

---

## Типичные проблемы

**Backend не стартует**
```
sqlalchemy.exc.OperationalError: could not connect to server
```
Причина: postgres ещё не готов. Compose ждёт healthcheck, но если образ не собирался — занимает дольше.
Решение: подождать 15–20 секунд, затем `docker compose restart backend`.

---

**CTF-задания не появляются в каталоге**

Задания не залиты в БД. Запустить:
```bash
./scripts/deploy-labs.sh --seed
```

---

**Страница не открывается: `ERR_NAME_NOT_RESOLVED`**

DNS не настроен. Добавить `127.0.0.1 lms.lab.local` в `/etc/hosts` (см. раздел «Настройка DNS»).

---

**Порт 80 занят**
```
Error starting userland proxy: listen tcp4 0.0.0.0:80: bind: address already in use
```
Найти и остановить процесс:
```bash
sudo lsof -i :80
# macOS: отключить AirPlay Receiver: System Settings → General → AirDrop & Handoff
# Linux: sudo systemctl stop nginx apache2
```

---

**CTF-контейнер не запускается для студента**

Проверить, что образ собран:
```bash
docker images | grep lms/
```
Если образа нет — запустить `./scripts/deploy-labs.sh --build`.

Проверить логи backend:
```bash
docker compose logs backend | grep ERROR
```

---

**Swagger возвращает 401 на защищённых эндпоинтах**

В Swagger UI нажать «Authorize» и вставить токен в формате `Bearer <token>`. Токен получить через `POST /api/auth/login`.
