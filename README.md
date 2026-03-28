# Hireflow

Hiring workflow API: job postings, applications, interviews, feedback, reporting, and real-time notifications.

## Architecture overview

**Layout.** Django project `config/` holds settings (`config/settings/`, loaded via `SETTINGS_KEY`), ASGI/WSGI, Celery, and URL routing. Domain code lives under `apps/` (on `PYTHONPATH` as `apps`):

| App | Responsibility |
|-----|------------------|
| **users** | `CustomUser`, roles (HR Admin, Recruiter, Interviewer), JWT auth URLs, DRF permission classes |
| **jobs** | Departments, job postings, status workflow (draft/open/closed), bulk updates |
| **candidates** | Candidates, applications, stage transitions, documents |
| **interviews** | Scheduling, conflicts, feedback rubrics/scores, interviewer actions |
| **notification** | In-app notifications, WebSocket consumer, Celery tasks (email + push to channels) |
| **reports** | Cached analytics (funnel, time-to-hire, workload, department breakdown) |

**Stack.** PostgreSQL, Redis (cache, Channels, Celery broker), Daphne ASGI for HTTP + WebSockets, Celery worker + Beat (`config/celery.py` defines the daily interview-reminder schedule).

**Design choices.** REST is organized around resource routers with occasional `@action` endpoints (e.g. publish job, interview stage/feedback). Errors and many write responses use a small shared envelope (`message`, `status_code`, optional `data` / `details`) via `config.exceptions` and `config.utils.api_response`. Object-level access for recruiters is tied to **owning the job posting** (`created_by` on `JobPosting`, or `application.job` / `interview.application.job`), so recruiters do not implicitly see every tenant-wide record. Interview feedback uses **writable nested serializers** (scores under one POST) and DB constraints for one feedback per interviewer per interview.

---

## Local setup

1. **Environment**  
   Copy the bundled env template to `.env` and adjust if needed:

   ```bash
   cp ".env example" .env
   ```

   Ensure `SETTINGS_KEY=local` (see `config/settings/__init__.py`) and that Postgres/Redis variables match Docker service names when using Compose (`POSTGRES_HOST=db`, Celery broker pointing at `redis-hireflow`).

2. **Docker Compose**

   ```bash
   docker compose up --build
   ```

   The `web` service runs migrations before starting Daphne. Postgres is exposed on host port `5434` by default (`POSTGRES_HOST_PORT`).

3. **Migrations (host / without relying on web startup)**

   ```bash
   export SETTINGS_KEY=local
   # Point DB at localhost if Postgres is mapped (e.g. localhost:5434) and set POSTGRES_* in .env accordingly.
   python manage.py migrate
   ```

---

## API documentation and browsable API

| Tool | URL | Notes |
|------|-----|--------|
| **OpenAPI schema** | `/api/schema/` | JSON schema (drf-spectacular) |
| **Swagger UI** | `/api/docs/` | Interactive docs |
| **ReDoc** | `/api/redoc/` | Alternate doc UI |

**Browsable API.** DRF’s HTML browsable renderer is enabled for API routes when the client requests HTML (e.g. visiting a list/detail URL in the browser while logged in or with session). Authenticated JSON APIs use **JWT** (`Authorization: Bearer <access>`); the browsable API can use session login if you expose it, but primary API auth is JWT from `auth/` (SimpleJWT).

---

## DRF permission model

Defaults (`config/settings/base.py`): `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]` — every view requires a logged-in user unless overridden.

**Custom classes** (`apps/users/permissions.py`):

- **`IsHRAdmin`** — `has_permission`: user is HR Admin (`role == admin`). Used for admin-only actions (e.g. publishing a draft job).
- **`IsRecruiterOrAdmin`** — `has_permission`: Recruiter or HR Admin. `has_object_permission`: HR Admin passes always; Recruiter passes if they own the resource via `created_by` / `recruiter` / `assigned_recruiter` on the object, or via the related **`job`** (`obj.job.created_by`), or via **`application.job`** (covers `Application`, `Interview`, and similar).
- **`IsAssignedInterviewer`** — `has_permission`: role Interviewer. `has_object_permission`: user is in `interviewers` M2M (or `interviewer_id` for single-assignee patterns).

Viewsets set `permission_classes = [...]` on the class or on specific `@action`s (e.g. `complete` uses `IsAssignedInterviewer`; list/create on interviews use `IsRecruiterOrAdmin`). DRF combines class-level and action-level `permission_classes` per route; checks run **after** authentication.

---

## Django Channels: notifications consumer

**Auth.** `config/asgi.py` wraps WebSocket routes in **`JWTAuthMiddleware`** (`config/middleware/channel_auth_midddleware.py`). The client connects with the access token in the query string, e.g.:

`ws://<host>:8000/ws/notifications/?token=<jwt_access_token>`

The middleware decodes the JWT (SimpleJWT `AccessToken`), loads the user, and sets `scope["user"]`. Invalid or missing tokens yield an anonymous user; **`NotificationConsumer`** closes the socket with code **4401** if not authenticated.

**Event flow.**

1. Backend code (e.g. Celery task) calls **`push_notification`** in `apps/notification/services.py`: persists a `Notification` row and sends **`channel_layer.group_send`** to `notifications_user_{user_id}` with `type: send_notification` and a JSON `payload`.
2. Each connected client is in their personal group from **`connect()`** (`group_add`).
3. Channels dispatches to **`NotificationConsumer.send_notification`**, which **`send`s** the payload over the WebSocket.
4. Optional client → server: JSON `{"action": "mark_read", "notification_id": ...}` marks a row (recipient must match); server replies with an acknowledgement message.

---

## Known limitations and trade-offs

**Testing.** Coverage is uneven: there are focused API tests (jobs, candidates, interviews, users, reports) but no full integration suite across Docker services, no systematic performance or load tests, and CI may not run DB-dependent tests without a compose stack. With more time: expand pytest/Django tests for permissions edge cases, WebSocket auth failure paths, Celery tasks (with eager or containerized workers), and contract tests against the OpenAPI schema.

**API versioning.** The API is unversioned (`/jobs/`, `/applications/`, etc.). Breaking serializer or URL changes would affect all clients at once. With more time: introduce **`/api/v1/`** (or header-based versioning), deprecate old paths explicitly, and tie drf-spectacular to a stable version tag.

**Other.** Global JSON response wrapping is not applied to every paginated list endpoint (only where `api_response` or the exception handler is used). Email delivery uses `fail_silently=True` in reminders—production would use a real SMTP backend and stronger failure handling. Redis/Postgres hostnames assume Docker networking for local dev.
