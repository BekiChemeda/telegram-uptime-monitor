## Telegram Uptime Monitor

### About
Telegram Uptime Monitor is a FastAPI and TeleBot based reliability assistant that keeps track of HTTP services, notifies Telegram users when outages happen, and records rich telemetry (status, latency, SSL health, incidents). A background scheduler performs checks while the Telegram bot provides a conversational UI for configuring monitors, reviewing stats, and pausing maintenance windows.

### Feature Highlights
- Monitor any HTTPS endpoint on custom intervals with status-code, latency, keyword, and SSL expiry rules.
- Async scheduler batches checks and persists detailed `CheckLog` records for analytics.
- Telegram bot menus let users create monitors, run on-demand checks, view stats, and toggle maintenance windows.
- Email alerts powered by Brevo plus Telegram notifications during incidents or when SSL certificates near expiry.
- FastAPI REST endpoints for `users`, `monitors`, and `checks`, including `/health` for probes.
- Dockerfile and docker-compose definitions for reproducible deployments.

### Architecture Overview
- **FastAPI application** (`app/app.py`) wires lifespan hooks that initialize the database, start the async monitoring scheduler, and launch the Telegram bot in the same event loop.
- **Database layer** (`app/database`) uses SQLAlchemy + async sessions against PostgreSQL. Alembic handles schema migrations under `alembic/`.
- **Domain models** (`app/models.py`) represent users, monitors, maintenance windows, and historical check logs.
- **Schedulers & services** (`app/services/*`) encapsulate monitoring, notification, statistics, and email logic.
- **Telegram bot** (`app/bot/*`) gives an interactive UX with inline keyboards, stateful flows, admin broadcast tools, and contextual help topics.

### Requirements
- Python 3.12+
- PostgreSQL 14+ (or compatible)
- Redis is **not** required; asyncio tasks and SQL timestamps drive scheduling.
- Optional: Docker 24+, Docker Compose v2 for containerized deployments.

### Quick Start (Local Development)
1. Clone the repo and create an environment:
	 ```bash
	 git clone <repo-url>
	 cd telegram-uptime-monitor
	 python -m venv .venv
	 .venv\Scripts\activate  # (PowerShell) or source .venv/bin/activate on Unix
	 ```
2. Install dependencies (PEP 621 / `pyproject.toml`):
	 ```bash
	 pip install -e .
	 ```
3. Configure environment variables via `.env` in the project root (see table below).
4. Initialize and migrate the database:
	 ```bash
	 alembic upgrade head
	 ```
5. Launch the FastAPI app + scheduler + Telegram bot:
	 ```bash
	 python main.py
	 ```

### Environment Variables (.env)
| Name | Description |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection string (e.g., `postgresql+asyncpg://user:pass@host:5432/uptime`). Required. |
| `TELEGRAM_BOT_TOKEN` | Bot token from `@BotFather`. Required for Telegram functionality. |
| `BOT_USERNAME` | Public username of your Telegram bot (without @). Enables deep links in alerts. |
| `BREVO_API_KEY` | API key for Brevo (Sendinblue) transactional email alerts. |
| `BREVO_SENDER_EMAIL` | Sender email verified in Brevo. |
| `ADMIN_IDS` | Comma-separated Telegram user IDs with elevated privileges (broadcasts, quotas). |
| `API_ACCESS_TOKEN` | Secret string clients must supply via `X-API-KEY` header for every REST call. |
| `DB_ECHO` | Optional (`true`/`false`). Controls SQLAlchemy echo logging; leave `false` in production. |

> The app loads `.env` explicitly inside `app/config.py`, so local runs should place configuration there. Production deployments can rely on real environment variables instead.

### Database & Migrations
- Create the database before running Alembic migrations.
- Use `alembic revision --autogenerate -m "description"` for new schema changes, then `alembic upgrade head` to apply.
- For rollbacks, `alembic downgrade -1` steps back a single migration.

### Running the Telegram Bot
- `/start` registers a Telegram user in the database (see `app/bot/handlers.py`).
- Inline menus allow users to add monitors, check histories, pause/resume, and manage alert parameters (keywords, latency, SSL, maintenance windows).
- Admin-only flows (broadcast, quota changes) require the user's Telegram ID to exist in `ADMIN_IDS`.

### Help & Support
- **Troubleshooting**
	- If the bot replies with *"Error running check"*, inspect scheduler logs or run `python main.py` with `LOGLEVEL=INFO` to surface stack traces.
	- Database connection failures typically come from malformed `DATABASE_URL`. Ensure the async driver prefix `postgresql+asyncpg` is present.
	- Run `alembic upgrade head` whenever migrations change to avoid missing table/column errors during runtime.
- **Operational Checks**
	- `GET /health` returns `{ "status": "ok" }` when FastAPI is live.
	- Use `/stats_<monitor_id>` callback to get uptime analytics without hitting the API.
- **Where to ask**
	- Create GitHub issues for bugs/feature requests.
	- Share stack traces, Python version, and reproduction steps to speed up triage.

### Deployment
#### 1. Docker (recommended)
```bash
docker build -t telegram-uptime-monitor:latest .
docker run -d \
	--name uptime-monitor \
	-p 8000:8000 \
	--env-file .env \
	telegram-uptime-monitor:latest
```
- Ensure the container can reach PostgreSQL (either linked service or managed instance).
- For Compose, edit `docker-compose.yml` with your secrets and run `docker compose up -d`.

#### 2. Bare-metal / VM
1. Provision Python 3.12, PostgreSQL, and a process supervisor (systemd, Supervisor, etc.).
2. Export environment variables securely (systemd `EnvironmentFile` or secret store).
3. Run `alembic upgrade head` once per release.
4. Start the app via `uvicorn app.app:app --host 0.0.0.0 --port 8000` or wrap `python main.py` in your supervisor.
5. Optionally place Nginx/Caddy in front for TLS termination and rate limiting.

#### Production Checklist
- [ ] Rotate `BREVO_API_KEY`/bot tokens regularly and never commit `.env`.
- [ ] Configure PostgreSQL backups + monitoring.
- [ ] Enable observability (e.g., Docker logs shipping, Prometheus exporters) to catch failed checks.
- [ ] Confirm firewall rules allow outbound HTTPS for monitor targets.
- [ ] Scale with multiple worker replicas only if you externalize the scheduler (one replica should own it to avoid duplicate checks).

### Testing
- Use the included `test_email.py` as a starting point for integration tests (e.g., mock Brevo API responses).
- Add additional pytest suites for routers/services under `app/`.

### Contributing
- Fork the repo, branch from `main`, and run formatting/tests before opening a PR.
- Write migrations for every schema change and document API updates.
- Provide screenshots or screen recordings for bot UX tweaks.

### License
Specify your license of choice (MIT, Apache 2.0, etc.) in `LICENSE`. Update this section accordingly.
