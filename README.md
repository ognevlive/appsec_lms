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

# 3. Открыть платформу
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

## Управление контентом

Все курсы, модули, юниты и таски управляются через админ-панель:

```
http://lms.lab.local/admin/courses
http://lms.lab.local/admin/tasks
```

### CTF-таски

Dockerfile'ы уязвимых приложений **не хранятся в этом репозитории**. Автор задания:

1. Пишет Dockerfile и собирает образ у себя / в своём CI.
2. Пушит образ в любой доступный Docker registry (Docker Hub, GHCR, приватный).
3. В UI → Таски → Новый таск (type=ctf) заполняет поля:
   - `docker_image`: ссылка на образ (`myuser/lms-sqli-basic:v2`)
   - `flag`: plaintext-флаг (хэшируется в SHA256 на бэкенде при сохранении)
   - `port`, `ttl_minutes`, `difficulty`

При запуске студентом существующий `docker_manager` делает `docker pull` и `docker run`.

### Импорт/экспорт

На страницах курсов и тасков есть кнопки «Экспорт» (скачать zip) и «Импорт»
(загрузить zip). Формат: ZIP с YAML-манифестом внутри.

Курс можно экспортировать отдельно (только структура) или `bundle=true` —
с включением всех referenced тасков.

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
│   └── Dockerfile
├── frontend/             # React 18 + Vite + Tailwind CSS
│   ├── src/
│   │   ├── pages/        # страницы: Login, Catalog, Challenge, Results, Admin
│   │   ├── contexts/     # AuthContext (JWT-токен, роль пользователя)
│   │   └── api.ts        # HTTP-клиент ко всем эндпоинтам backend
│   └── Dockerfile
├── docker-compose.yml
└── .env
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
docker compose down -v && docker compose up --build -d
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

Проверить, что образ доступен локально или в registry:
```bash
docker images | grep <docker_image из таска>
```
Если образа нет — собрать/запушить его и убедиться, что `docker_image` в админке
указывает на правильный тег. Backend сделает `docker pull` при первом запуске.

Проверить логи backend:
```bash
docker compose logs backend | grep ERROR
```

---

**Swagger возвращает 401 на защищённых эндпоинтах**

В Swagger UI нажать «Authorize» и вставить токен в формате `Bearer <token>`. Токен получить через `POST /api/auth/login`.
