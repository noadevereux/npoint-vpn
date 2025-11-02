# Nexpoint Technical Overview

## Runtime entry points and configuration
- `main.py` is the executable entry point. It validates optional SSL material, decides how Uvicorn binds to the network, and launches a single-worker FastAPI server pointing at `main:app`. Debug mode forces a plain TCP listener on `0.0.0.0` for local development.【F:main.py†L15-L103】
- Application configuration is centralized in `config.py`. Environment variables (optionally loaded from `.env`) control database connectivity, server bindings, dashboard options, Xray integration parameters, feature toggles, notification behavior, and scheduler intervals. Downstream modules import settings directly from this module.【F:config.py†L1-L148】

## FastAPI application composition
- `app/__init__.py` builds the FastAPI instance, enables CORS, registers routers, and exposes the global `scheduler`, `logger`, and `xray` singletons. A startup hook verifies that the public subscription path does not conflict with the API routes and then starts the background scheduler; shutdown stops it. Validation errors are normalized into a flattened JSON structure.【F:app/__init__.py†L15-L74】
- Routers in `app/routers/` group domain-specific endpoints under the `/api` prefix. Examples include `admin.py` for authentication and admin CRUD, `core.py` for Xray core control, `node.py` for node lifecycle, `system.py` for aggregated statistics, `user.py` for subscriber management, and `subscription.py` for public subscription feeds. Each router declares its own dependencies and response contracts, and most guard sensitive operations via the `Admin` Pydantic helper methods.【F:app/routers/__init__.py†L1-L27】【F:app/routers/admin.py†L1-L191】【F:app/routers/core.py†L1-L114】【F:app/routers/subscription.py†L1-L194】
- Common dependencies live in `app/dependencies.py`, where helpers fetch database records, validate credentials, and enforce per-admin access rules. Routers import these functions when they need strongly-typed resources (admins, users, nodes, subscriptions).【F:app/dependencies.py†L1-L90】

## Persistence layer
- SQLAlchemy is used directly rather than via FastAPI extensions. `app/db/__init__.py` exposes `SessionLocal`, a `GetDB` context manager, and the generator dependency `get_db()` used across routers. It also re-exports CRUD helpers that encapsulate write logic and cross-table updates.【F:app/db/__init__.py†L1-L77】
- Data models defined in `app/db/models.py` cover administrators, subscribers, proxies, Xray inbounds/hosts, nodes, hourly usage logs, JWT secrets, TLS material, and reminder queues. Declarative relationships connect entities so higher-level logic can traverse from admins to users, users to proxies, and nodes to consumption metrics.【F:app/db/models.py†L35-L352】
- Pydantic response and request schemas in `app/models/` mirror the SQLAlchemy entities and expose computed properties like inbound availability. These models power validation in the routers and orchestrate Xray updates through `UserResponse` and related objects.【F:app/models/user.py†L1-L200】

## Xray integration layer
- `app/xray/__init__.py` wires together the in-process Xray control stack. It instantiates the `XRayCore`, dynamically allocates an API port, loads `XRayConfig`, and provides a shared `xray.api` client. A `DictStorage` cache populates inbound host metadata from the database for fast template generation.【F:app/xray/__init__.py†L1-L83】
- Operational helpers in `app/xray/operations.py` propagate user and node changes to Xray. They add/remove/alter users across all configured inbounds, manage TLS certificates, and keep remote nodes synchronized via threaded helper functions. Nodes are tracked in the global `xray.nodes` registry and expose restart/connect/disconnect controls used by routers and jobs.【F:app/xray/operations.py†L1-L120】【F:app/xray/operations.py†L183-L220】
- The Xray core lifecycle is tied to the FastAPI lifecycle through `app/jobs/0_xray_core.py`. On startup it renders the runtime config from the database, boots the main core, connects enabled nodes, and schedules a periodic health check that reconnects or restarts unhealthy components. Shutdown cleanly stops all cores.【F:app/jobs/0_xray_core.py†L4-L78】

## Background jobs and scheduler
- `app/jobs/__init__.py` dynamically imports all job modules so simply adding a file registers new scheduled tasks.【F:app/jobs/__init__.py†L1-L13】
- `record_usages.py` polls the Xray API on an interval, aggregates per-user and per-node traffic, persists counters, and updates admin usage totals. It respects a `DISABLE_RECORDING_NODE_USAGE` toggle when necessary.【F:app/jobs/record_usages.py†L12-L225】
- `review_users.py` enforces quota and expiration policies by scanning active users, moving them into `limited` or `expired` states, performing “next plan” resets, and triggering webhook notifications. It also transitions `on_hold` users back to `active` when they reconnect.【F:app/jobs/review_users.py†L6-L120】
- `send_notifications.py` drains a process-wide queue of webhook notifications, implements retry/backoff, purges expired reminders, and ensures pending messages are flushed on shutdown when webhooks are enabled.【F:app/jobs/send_notifications.py†L8-L98】
- Additional jobs such as `remove_expired_users.py` or `reset_user_data_usage.py` follow the same pattern and rely on the shared `scheduler` declared in `app/__init__.py`.

## Notification channels
- Telegram integration spins up a bot (if a token is configured) on application startup, dynamically loads handler modules, and exports helper functions to report account events. Polling runs in a dedicated thread so it does not block the FastAPI event loop.【F:app/telegram/__init__.py†L1-L54】
- Discord/webhook reporting uses similar handler shims and is invoked by the reporting utilities under `app/utils/report.py`. Webhook delivery is centralized in the notification queue processed by `send_notifications.py`.

## Subscription and templating pipeline
- Public subscription endpoints live under `/{XRAY_SUBSCRIPTION_PATH}` and serve both HTML landing pages and client-specific configuration payloads. Incoming requests are validated via signed tokens, and response headers include metadata (profile title, update interval, usage info) consumed by client apps.【F:app/routers/subscription.py†L35-L194】
- Subscription rendering delegates to `app/subscription/` modules for Clash, Sing-box, V2Ray, Outline, etc., while Jinja templates in `app/templates/` supply customizable HTML wrappers. The template loader honours a user-specified override directory so operators can supply bespoke branding.【F:app/templates/__init__.py†L1-L21】

## Dashboard frontend
- `app/dashboard/__init__.py` mounts the bundled Vite/React dashboard into the FastAPI app. In development it spawns `npm run dev` with the correct API base path; in production it builds static assets on-demand and serves them under the configured dashboard path along with a static asset mount.【F:app/dashboard/__init__.py†L6-L59】

## Command-line tooling
- `nexpoint-cli.py` provides a Typer-based CLI that groups admin, subscription, and user commands. It can also install shell completions. The CLI modules under `cli/` reuse the same API surface exposed by the FastAPI backend, giving administrators an alternative automation interface.【F:nexpoint-cli.py†L1-L55】

## Putting it together
1. Configuration is loaded, the FastAPI app is instantiated, and routers, jobs, and integrations register themselves.
2. On startup the scheduler runs, the dashboard mounts, Telegram (and other) bots begin polling, and the Xray core boots with database-derived user assignments.
3. API calls from the dashboard, CLI, or third-party tools run through routers, Pydantic schemas, and CRUD helpers to mutate the database. The Xray operations layer mirrors those changes to the running Xray core(s).
4. Background jobs continuously sync usage statistics, enforce lifecycle policies, and deliver notifications so the database, API, and Xray stay consistent.

Armed with this map you can jump directly into the relevant module—routers for HTTP behavior, `app/db` for persistence, `app/xray` for core interactions, or `app/jobs` for scheduled automation—when implementing new features.
