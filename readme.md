# Repo Signals

Persistent, interpreted health monitoring for GitHub repositories, real-time event ingestion via Kafka, nightly batch analytics via Airflow.

## System Architecture

```mermaid

flowchart TB
    GH[("GitHub<br/>OAuth + Webhooks")]

    BACKEND["Backend API (FastAPI)<br/>auth · webhook setup · ingestion · queries"]

    KAFKA[["Kafka (KRaft)<br/>per-repo topics"]]

    DBCONSUMER["DB Consumer<br/>own container · durable · offset committed after write"]
    LIVECONSUMER["Live-Feed Consumer<br/>in-process (asyncio task) · never commits offsets"]

    APPDB[("Postgres: App DB<br/>Users · RefreshToken · TrackedRepo · EventData · ActiveRepoItems · HealthMetrics")]
    AFDB[("Postgres:Airflow Metadata<br/>separate instance")]

    AIRFLOW["Airflow <br> nightly ETL DAG<br/>extract → compute 4 health metrics → load"]

    FRONTEND["Frontend <br/>index · login · dashboard · repo pages"]
    BROWSER(["Browser"])

    GH -- "OAuth code" --> BACKEND
    GH -- "webhook event" --> BACKEND
    BACKEND -- "produce" --> KAFKA
    BACKEND -- "read / write" --> APPDB

    KAFKA -- "consumer group: event-data-reader" --> DBCONSUMER
    KAFKA -- "consumer group: live-feed" --> LIVECONSUMER

    DBCONSUMER -- "write EventData / ActiveRepoItems" --> APPDB
    LIVECONSUMER -- "push events via SSE" --> BROWSER

    AIRFLOW -- "extract EventData / load HealthMetrics" --> APPDB
    AIRFLOW -. "task state" .-> AFDB

    FRONTEND -- "fetch overview / health-metrics" --> BACKEND
    FRONTEND -- "EventSource" --> LIVECONSUMER
    FRONTEND == "renders in" ==> BROWSER

```

## What this is & what it solves

GitHub tells you what happened in your repository. It doesn't tell you whether your repository is healthy.

The Insights tab shows commit counts and contributor graphs, but the Traffic API caps history at 14 days, and raw counts don't answer the questions a maintainer actually cares about: Are pull requests sitting unreviewed? Is one person silently carrying the entire project? Are issues quietly going stale? Is this week's activity spike meaningful, or normal for this repo?

Repo Signals ingests your repository's GitHub events in real time, stores them durably, and runs nightly analysis to surface four specific health signals.

**What it is not:** a GitHub Insights replacement, a multi-repo comparison dashboard, or a service for tracking repositories you don't own. GitHub requires repository admin access to register webhooks, which makes third-party repo tracking architecturally impossible, so this is deliberately a maintainer's self-monitoring tool.

## How it works

**1. Getting events in**

Once you connect a repo, the backend checks that you actually have admin access to it (GitHub requires this for webhook registration) and registers a webhook. From then on, every push, pull request, issue, and review GitHub reports on that repo gets sent to the backend as a webhook call.

The webhook receiver does the smallest amount of work possible: read the payload, write it into Kafka, respond to GitHub. Nothing else happens inside that request.

**2. Why Kafka sits in the middle**

Kafka acts as a landing zone that decouples event receipt from event processing. The webhook receiver's only job is to accept the event and write it into Kafka as fast as possible, then acknowledge GitHub immediately it never blocks on whatever happens downstream.

Without that separation, the receiver would have to do all processing (parsing, database writes, live-feed updates) synchronously inside the webhook request itself. A slow database or a bug anywhere in that chain could make GitHub's request hang, and since GitHub doesn't retry failed deliveries, a failure anywhere in that chain means the event is gone for good.

Two separate processes(consumers) read from Kafka independently, at their own pace:

- one writes every event to Postgres, so it's kept permanently and also used by Airflow for analytics purpose
- one pushes events out using Server Side Events (SSE) to anyone currently watching that repo's live feed, and doesn't write anything to disk

Neither one can slow down or break the other, and neither can slow down the original webhook response.

**3. Making sense of it later**

Raw events on their own don't tell you much. Once a day, an Airflow job reads through the stored events for each tracked repo and works out four things: whether recent activity is a real spike or decline compared to that repo's own normal pace, how long pull requests sit before review and merge, how concentrated contributions are among a small number of people, and how many open issues have gone quiet for a long time. Finally after computing these 4 metrics, the results are stored in a separate database table, that can be accessed via backend endpoint.


**4. What the user sees**

Each tracked repo has two tabs:

- **Overview**: raw totals (commits, PRs, forks, open issues) plus the live feed itself: events as they happen, via Server-Sent Events (a one-way connection the browser keeps open, rather than repeatedly polling the backend endpoint), shown as short human-readable lines ("3 commits pushed to main", "PR #42 merged by someone") each linking back to GitHub.
- **Health Metrics**: the four health numbers, updated once a day, alongside two charts: a bar chart of daily event counts (colored to reflect the current spike/decline verdict) and a doughnut chart of bus factor.

A repo can have more than one maintainer watching it at once each connected viewer gets their own queue of live events, so the live feed isn't limited to a single open tab.

## Why these technologies

**Kafka.** Covered above, it's the layer that lets the webhook receiver respond instantly while the actual storage and live-feed work happens independently, without either one blocking the other or the original GitHub request.

**Airflow.** The nightly health-metrics job runs as a 3-task Airflow DAG (extract → compute → load) on a daily cron schedule. It's used here at a level calibrated to be genuinely resume-worthy a real scheduled DAG with real task dependencies and a real Postgres connection rather than as an excuse to explore every Airflow feature. A single DAG, LocalExecutor, no Celery.

**Cookie-based authentication.** The live feed uses `EventSource`, the browser API for Server-Sent Events, which cannot attach custom headers so a Bearer-token-in-header auth scheme wouldn't work for it. Cookies are sent automatically by the browser on every request, including `EventSource` connections, which is why auth here is cookie-based rather than token-in-header. Cookie settings differ between environments: `secure=False, samesite=lax` in development (works over plain HTTP on localhost), `secure=True, samesite=none` in production (required for the frontend and backend being on different origins).

**Postgres, twice.** There are two separate Postgres containers: one holds the application's own data (users, tracked repos, raw events, computed health metrics), the other holds Airflow's internal metadata (DAG runs, task state). Keeping them separate means Airflow's own bookkeeping never touches the application schema.

## The four health metrics

These thresholds were chosen deliberately based on reasoning about what should count as meaningful, not derived from a large dataset, they're reasonable starting points, not universal constants.

**Spike / decline detection.** Compares today's event count on a repo to that repo's own recent baseline (up to a 28-day rolling window). Needs at least 14 days of tracking history before it will report anything other than "insufficient data." Marked as a **spike** if today's count is more than 1.5× the baseline average and at least 3 events; a **decline** if it's less than 0.5× the baseline average and the baseline itself is at least 1.0; otherwise **normal**.

**PR lifecycle health.** Two separate numbers: average time to merge (days between a pull request being opened and merged), and average time to first review (days between a pull request being opened and its first submitted review). Each needs at least 3 qualifying pull requests in the window before it reports a number; otherwise it shows "insufficient data."

**Bus factor.** What percentage of commits (by push events) each contributor is responsible for, based on the commit author's name. If there are no commits in the tracked window, this reports "insufficient data" rather than an empty list.

**Stale issues.** Tracks the last activity (opened, edited, reopened, or commented on) for every currently-open issue. An issue is considered stale if more than 14 days have passed since its last activity. Reports the percentage of open issues that are stale, and which ones. If there's no open-issue activity in the window at all, this reports "insufficient data."

All four are computed once a night by the Airflow DAG, over a rolling window, data lying inside the rolling window is loaded for analytics.

The Health Metrics tab pairs these with two charts: a daily event-count bar chart (colored to reflect the current spike/decline verdict), and a doughnut chart breaking down bus factor by contributor.



## Tech stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python) |
| Event streaming | Apache Kafka (KRaft mode) |
| Batch orchestration | Apache Airflow (LocalExecutor) |
| Database | Postgres (separate instances for app data and Airflow metadata) |
| Auth | GitHub OAuth, JWT access tokens, database-backed refresh tokens, Fernet-encrypted stored GitHub tokens |
| Frontend | HTML, CSS, JavaScript, Chart.js |
| Infra | Docker Compose, nginx (static frontend), ngrok (local webhook delivery) |

## Project structure

```
repo-signals/
├── airflow/
│   ├── dags/
│   │   └── etl_dag.py
│   └── docker-compose-airflow.yaml
├── backend/
│   ├── endpoints/
│   │   ├── delete_webhook.py    # removes a tracked repo + unregisters its webhook
│   │   ├── display_repos.py     # lists a user's tracked repos
│   │   ├── health_metrics.py    # serves the latest computed health metrics
│   │   ├── live_feed.py         # SSE endpoint
│   │   ├── overview.py          # raw activity totals for a repo
│   │   ├── producer.py          # webhook receiver → Kafka producer
│   │   ├── users.py             # GitHub OAuth login/callback/refresh/logout
│   │   └── webhook_setter.py    # registers a new repo's webhook (checks admin access first)
│   ├── utils/                   # config, JWT/auth helpers, Fernet encryption
│   ├── workers/
│   │   ├── consumer.py          # durable Kafka → Postgres consumer
│   │   └── live_feed_consumer.py   # in-process Kafka consumer feeding the SSE queues
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── registry.py              # shared per-repo SSE client queue registry
│   ├── schemas.py
│   ├── Dockerfile
│   └── docker-compose-backend.yaml
├── frontend/
│   ├── index.html / index.css / index.js       # landing page
│   ├── login.html / login.css / login.js       # GitHub OAuth entry point
│   ├── dashboard.html / dashboard.css / dashboard.js   # tracked repos list
│   ├── repo.html / repo.css / repo.js          # Overview (totals + live feed) / Health Metrics (4 metrics + 2 charts) tabs
│   ├── navbar.js / navbar.css                  # shared authenticated-page navbar
│   ├── common.css                              # shared styles, palette, fonts
│   ├── config.js                               # backend URL config
│   ├── auth.js                                 # 401 → refresh → retry handling
│   └── messages.js                             # shared dismissible banner/message helper
└── docker-compose.yaml                         # Main docker compose file, that combines other two compose files
```

## Running it locally

### Prerequisites

- Docker and Docker Compose
- An [ngrok](https://ngrok.com) account (GitHub needs a public URL to send webhooks to)
- A GitHub account

### 1. Register a GitHub OAuth App

Go to GitHub → Settings → Developer settings → OAuth Apps → New OAuth App.

- **Homepage URL:** `http://localhost:3000`
- **Authorization callback URL:** `https://<your-ngrok-domain>/callback`

Save the Client ID and Client Secret.

### 2. Start ngrok

```bash
ngrok http 8000
```

Take the forwarding URL it gives you and set it as `backend_ngrok` in `backend/utils/config.py`. This must match the callback URL from step 1 it's the URL GitHub sends both the OAuth redirect and webhook deliveries to.

### 3. Create the environment files

Four `.env` files are needed. See `.env.example` for the full list.

**`.env`** (repository root)
```
POSTGRES_PASSWORD=your_password
POSTGRES_USER=your_username
AIRFLOW_CONN_BACKEND_DB=postgresql://your_username:your_password@database:5432/backend_db
```

**`airflow/.env`**
```
AIRFLOW_UID=50000
```

**`backend/endpoints/.env`**
```
GITHUB_CLIENT_ID=<from step 1>
GITHUB_CLIENT_SECRET=<from step 1>
```

**`backend/utils/.env`**
```
SECRET_KEY=<any random string, used to sign JWTs>
GITHUB_ENCRYPTION_KEY=<generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
DEVELOPMENT=True
```

`DEVELOPMENT=True` switches cookies to `secure=False, samesite=lax` so they work over plain HTTP locally. In production it flips to `secure=True, samesite=none`, which the live feed's `EventSource` connection needs to send cookies across origins.

### 4. Start everything

```bash
docker compose up
```

The root `docker-compose.yaml` pulls in the Airflow and backend compose files with `include`, and adds an nginx container that serves the frontend.

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Airflow UI | http://localhost:8080 (`airflow` / `airflow`) |
| Backend Postgres | localhost:5431 |
| Airflow Postgres | localhost:5432 |

### 5. Turn on the DAG

Airflow creates DAGs paused by default. Open the Airflow UI, find `etl_dag`, and unpause it. It runs nightly at 02:00 IST — until the first run completes for a newly tracked repo, its Health tab will correctly show "insufficient data" for every metric.

## Known limitations & tradeoffs

- **GitHub doesn't retry failed webhook deliveries.** If the backend is down, unreachable, or errors when GitHub sends an event, that event is lost permanently — there's no backlog or replay from GitHub's side.
- **Self-monitoring scope only, by design.** GitHub webhooks require repository admin access, so this can only track repos you administer. GitHub OAuth Apps (as opposed to GitHub Apps) also have no repo-picker UI, so a repo is added by entering it directly rather than browsing a list. Repos can also be removed, which unregisters the webhook and stops tracking — but the repo's already-collected events and health metrics stay in the database rather than being deleted.
- **No refresh-token rotation.** Refresh tokens are database-backed and revocable (logging out flips a revoked flag), but a token isn't rotated on use, and there's no account-deletion or mass-token-revocation flow yet.
- **Single Kafka consumer, single partition, per topic.** This is enough for personal-scale event volume. Scaling ingestion throughput would need repartitioning and multiple consumers per group.
- **Health metrics are a nightly snapshot, not real-time.** They're computed once a day (02:00 IST), so the health tab can lag up to roughly 24 hours behind the live feed.
- **PR lifecycle health has no historical chart.** Unlike spike/decline (backed by a daily event-count chart) and bus factor (a doughnut chart), average time-to-merge and time-to-review only expose their latest computed value, shown as plain numbers rather than a trend over time.
- **Metrics use day-level granularity.** Time differences (e.g. time-to-merge) are calculated from dates, not exact timestamps, so an event just after midnight and one just before aren't distinguished.
- **Airflow's Fernet key isn't set in the current environment configuration**, which means Airflow stores its own internal connections (including the Postgres connection string and credentials) unencrypted in its metadata database. Not exposed outside the local machine, but worth knowing before deploying this anywhere shared.
- **No incremental aggregation.** The nightly job reprocesses a rolling ~29-day window from scratch each run rather than aggregating incrementally, which is simpler at this scale but does more repeated work as history grows.

## Bugs hit along the way

- **Duplicate rows after a crash/restart test.** Fixed by switching to `enable.auto.commit=False` and manually committing each Kafka offset only after its corresponding Postgres write actually succeeded.
- **Encrypted GitHub token stored incorrectly.** Fernet's `.encrypt()` returns bytes; storing those bytes directly caused a mismatch on read-back. Fixed by decoding to a UTF-8 string before storing.
- **Refresh-token lookups silently failing.** Refresh tokens were first hashed with Argon2, which applies a random salt per call — so the same token produced a different hash every time and could never be matched again on lookup. Switched to SHA-256, a plain deterministic hash, which is appropriate here because the refresh token itself is already a long random value rather than a guessable secret.
- **JWT encoding error on the `sub` claim.** GitHub's numeric user ID had to be explicitly cast to a string before being placed in the JWT `sub` claim, since JWT encoding expects `sub` to be a string.
