<div align="center">

# 🏝️ COZI — Backend API

**A resort discovery and booking platform backend built with FastAPI.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-SQLAlchemy-4169E1?logo=postgresql&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.5-37814A?logo=celery&logoColor=white)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-3.13-FF6600?logo=rabbitmq&logoColor=white)
![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-Observability-425CC7?logo=opentelemetry&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)

</div>

---

## 📖 1. Project Overview

**COZI** is the backend service for a resort booking application. It lets guests sign up, verify their email, reset a forgotten password, browse resorts, read and write reviews, and book stays — while checking availability, guest capacity, and pricing on the server side. Resort managers (admins) can sign up and log in, with more manager features planned.

### ✨ Key Features

| Area | Capabilities |
| --- | --- |
| 🔐 **Guest authentication** | Sign up, email verification (HTML landing pages), login, logout and forgot/reset password with token-based auth |
| 🧑‍💼 **Manager authentication** | Sign up, email verification, login and logout for resort managers (admins), with tokens kept separate from guest tokens |
| 🛡️ **Secure payloads** | Credentials are sent as encrypted payloads (`EncryptedDataDTO`) and decrypted server-side; passwords hashed with `bcrypt` |
| 🏨 **Resorts** | List resorts, view details (amenities, capacity), read and post reviews |
| 📅 **Bookings** | Price/availability **preview**, create, history, details, and cancel |
| ✅ **Business rules** | Booked dates are blocked (and freed on cancel), guest-capacity validation, price computation, check-out-after-check-in checks |
| 📨 **Async email** | Verification and password reset emails are dispatched through Celery workers over RabbitMQ |
| 📊 **Observability** | Traces (Tempo), logs (Loki), and metrics (Prometheus) via OpenTelemetry, visualised in Grafana |
| 🧪 **Tests** | Endpoint-level tests with `pytest` and `testcontainers` (real PostgreSQL / RabbitMQ) |

---

## 🧰 2. Tech Stack

| Category | Technology |
| --- | --- |
| **Language** | Python 3.12 |
| **Web framework** | FastAPI (`fastapi[standard]`), Uvicorn, Jinja2 templates |
| **Database / ORM** | PostgreSQL (`psycopg`), SQLAlchemy, Alembic migrations |
| **Background jobs** | Celery + RabbitMQ |
| **Security** | PyJWT, PyCryptodome, bcrypt |
| **Observability** | OpenTelemetry SDK/OTLP, Prometheus FastAPI Instrumentator, Grafana, Tempo, Loki, Prometheus |
| **Gateway** | Traefik v3 (reverse proxy / single entry point) |
| **Containers** | Docker, Docker Compose |
| **Testing & tooling** | pytest, pytest-cov, pytest-mock, testcontainers, Black |

---

## 🗂️ 3. Architecture & Project Structure

COZI follows a **domain-oriented** layout: each endpoint has its own *service* module holding the business logic, while routers stay thin and only wire HTTP to services.

```text
cozi-app-be/
├── alembic/                     # Database migrations
│   └── versions/                #   Timestamped migration scripts
├── docker/                      # Docker Compose stacks (one per concern)
│   ├── cozi-app-be-develop/     #   API + Celery worker (Dockerfile, compose.yaml)
│   ├── rabbitmq/                #   Message broker
│   ├── traefik/                 #   Reverse proxy / gateway
│   └── grafana/                 #   Grafana, Tempo, Loki, Prometheus, OTel collector
├── documentations/              # How each feature works (flow diagrams, rules, known limitations)
├── env/                         # Per-stage environment files (local, develop, production, test)
├── src/
│   ├── main.py                  # FastAPI app factory, routers, OpenTelemetry setup
│   ├── core/                    # Cross-cutting concerns
│   │   ├── models/              #   SQLAlchemy models (Guest, Resort, Booking, Payment, ...)
│   │   ├── services/            #   Auth tokens, sessions, encryption, email, helpers
│   │   └── tools/               #   Celery, FastAPI (middlewares, handlers), OTel, SQLAlchemy utils
│   ├── domains/
│   │   ├── guest/               # Guest-facing API
│   │   │   ├── router.py        #   Mounts the /guest/auth, /resorts and /bookings routers
│   │   │   ├── auth/            #   Sign up, verification, login, logout, forgot/reset password
│   │   │   ├── booking/         #   Booking router, services, and rule helpers
│   │   │   └── resort/          #   Resort router and services
│   │   └── manager/             # Manager (admin) API
│   │       └── auth/            #   Sign up, verification, login, logout
│   └── templates/               # Jinja2 / email HTML templates
├── tests/                       # Mirrors src/domains structure
├── alembic.ini
└── pyproject.toml               # Dependencies and pytest configuration
```

### 🔄 Request Flow

```text
Client ─▶ Traefik ─▶ FastAPI router ─▶ Service (business rules) ─▶ SQLAlchemy ─▶ PostgreSQL
                                              │
                                              └─▶ Celery task ─▶ RabbitMQ ─▶ Worker ─▶ SMTP email
```

### 🗃️ Data Model

`User` → `Guest` / `Admin` (the manager) / `Master` · `Organization` · `Resort` (with `ResortAmenity`, `ResortAvailability`, `ResortReview`) · `Booking` · `Payment` · `GuestVerification` · `GuestPasswordResetRequest` · `ManagerVerification`

All user types share the `users` table (joined-table inheritance on `user_type`). User ids are ULIDs.

> 📚 See [`documentations/`](documentations/) for how each feature works.

---

## 🚀 4. Getting Started

### Prerequisites

- Python **3.12+**
- PostgreSQL database
- Docker & Docker Compose (for the full stack, RabbitMQ, and tests via testcontainers)

### 1️⃣ Clone and install

```bash
git clone <your-repo-url> cozi-app-be
cd cozi-app-be
python -m venv .venv
```

Activate the virtual environment (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on macOS/Linux), then:

```bash
pip install -e ".[local]"
```

### 2️⃣ Configure environment variables

Environment files live in `env/` (`local.env`, `develop.env`, `production.env`, `test.env`). Create the one you need with these keys:

| Variable | Description |
| --- | --- |
| `STAGE` | Deployment stage (`local`, `develop`, ...). Becomes the API root path: `/<STAGE>/api/v1` |
| `DB_URL` | SQLAlchemy/psycopg PostgreSQL connection string |
| `TOKEN_SECRET_KEY` | Secret used to sign auth tokens |
| `COZI_ENCRYPTION_KEY` | Key used to decrypt/encrypt secure request payloads |
| `SMTP_USER` | Account used to send emails |
| `SMTP_PASS` | Password (or app password) of that account |
| `SMTP_HOST` | *(optional)* SMTP server. Default: `smtp.gmail.com` |
| `SMTP_PORT` | *(optional)* SMTP port. Default: `587` |
| `API_BASE_URL` | *(optional)* Base URL used in the password reset email link. Default: `http://cozi-api.localhost` |
| `RABBITMQ_URL` | *(optional)* Celery broker URL. Default: `amqp://cozi:cozi1234@rabbitmq:5672/` |
| `EMAIL_NOTIF_QUEUE` | *(optional)* Queue name for email notification tasks |

> ℹ️ `env/` is git-ignored. Emails are sent by the Celery worker, so it needs the same `SMTP_*` values and must be running.

> ⚠️ Never commit real secrets. Use strong, unique values outside of local development, and change the default RabbitMQ credentials in `docker/rabbitmq/compose.yaml`.

### 3️⃣ Run database migrations

```bash
alembic upgrade head
```

### 4️⃣ Run the API

**Option A — Local (quick start)**

```bash
cd src
uvicorn main:app --reload
```

Interactive docs are then available at `http://127.0.0.1:8000/<STAGE>/api/v1/docs` (e.g. `/local/api/v1/docs`).

> ℹ️ `main.py` exports telemetry to `otel-collector:4317`. Outside the Docker network this host is unreachable, so telemetry export will fail silently/log warnings; start the observability stack or adjust the endpoint if you need it locally.

**Option B — Full stack with Docker Compose**

The compose files share external networks, so start the infrastructure first:

```bash
docker compose -f docker/traefik/compose.yaml up -d
docker compose -f docker/rabbitmq/compose.yaml up -d
docker compose -f docker/grafana/compose.yaml up -d
docker compose -f docker/cozi-app-be-develop/compose.yaml up -d --build
```

| Service | URL |
| --- | --- |
| 🌐 API | `http://cozi-api.localhost/<STAGE>/api/v1` |
| 🐇 RabbitMQ UI | `http://rabbitmq.localhost` |
| 📈 Grafana | `http://monitoring.localhost/grafana` |
| 🚦 Traefik dashboard | `http://localhost:8080` |

> The `observability` network is declared as `external` by the app compose file — make sure the Grafana stack creates it (or create it with `docker network create observability`).

### 5️⃣ Run the Celery worker (local)

```bash
cd src
celery -A core.tools.celery.celery_app worker --loglevel=info
```

### 🧪 Running tests

Tests use `testcontainers`, so Docker must be running. Settings are loaded from `env/test.env`.

```bash
pytest
pytest --cov=src
```

---

## 💡 5. Usage

Guest routes are prefixed with `/<STAGE>/api/v1/guest` and manager routes with `/<STAGE>/api/v1/manager`.

### Guest endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/guest/auth/sign-up` | Register a guest (encrypted payload) |
| `GET` | `/guest/auth/verification?d=<token>` | Email verification page |
| `POST` | `/guest/auth/verification` | Confirm verification |
| `POST` | `/guest/auth/login` | Log in, returns an auth token |
| `POST` | `/guest/auth/logout` | Log out |
| `POST` | `/guest/auth/forgot-password` | Email a password reset link (same response whether or not the email exists) |
| `GET` | `/guest/auth/reset-password?d=<token>` | Password reset page |
| `POST` | `/guest/auth/reset-password` | Set the new password (form post from that page) |
| `GET` | `/guest/resorts` | List resorts |
| `GET` | `/guest/resorts/{resort_id}` | Resort details |
| `GET` | `/guest/resorts/{resort_id}/reviews` | List resort reviews |
| `POST` | `/guest/resorts/{resort_id}/reviews` | Post a review |
| `POST` | `/guest/bookings/preview` | Preview price & availability |
| `POST` | `/guest/bookings` | Create a booking |
| `GET` | `/guest/bookings` | Booking history |
| `GET` | `/guest/bookings/{booking_id}` | Booking details |
| `PUT` | `/guest/bookings/{booking_id}/cancel` | Cancel a booking and free its dates |

### Manager endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/manager/auth/signup` | Register a manager (encrypted payload) |
| `GET` | `/manager/auth/verify?d=<token>` | Email verification page |
| `POST` | `/manager/auth/verify` | Confirm verification |
| `POST` | `/manager/auth/login` | Log in, returns an auth token |
| `POST` | `/manager/auth/logout` | Log out |

A guest token only works on guest endpoints and a manager token only on manager endpoints.

### Example

```bash
# Browse resorts
curl http://cozi-api.localhost/develop/api/v1/guest/resorts

# Login (payload must be encrypted with COZI_ENCRYPTION_KEY)
curl -X POST http://cozi-api.localhost/develop/api/v1/guest/auth/login \
  -H "Content-Type: application/json" \
  -d '{"data": "<encrypted-payload>"}'

# Authenticated request
curl http://cozi-api.localhost/develop/api/v1/guest/bookings \
  -H "Authorization: <auth-token>"
```

> 📝 The exact request schemas are in the interactive OpenAPI docs at `/<STAGE>/api/v1/docs`. For how each feature works, read the pages in [`documentations/`](documentations/): [Guest Auth](documentations/Guest/Auth.md), [Guest Booking](documentations/Guest/Booking.md), [Guest Resort](documentations/Guest/Resort.md) and [Manager Auth](documentations/Manager/Auth.md).

### 🖼️ Screenshots

<!-- Replace with real captures -->
| Swagger UI | Grafana Dashboard |
| --- | --- |
| _`docs/images/swagger.png`_ | _`docs/images/grafana.png`_ |

---

## 🗺️ 6. Roadmap

- [ ] 💳 Payment gateway integration (the `Payment` model is in place)
- [ ] 🧑‍💼 Manager features beyond auth: create and manage a resort, view its bookings
- [ ] 👑 Master (multi-resort owner) auth and management of its admins
- [ ] 🔁 Forgot/reset password for managers
- [ ] 🔍 Resort search, filtering, and pagination
- [ ] 🔑 Token refresh and revoking tokens after a password reset
- [ ] ⏳ Expire unpaid `PENDING` bookings so their dates are released
- [ ] 🔒 Database unique constraint on resort dates to rule out double booking under concurrent requests
- [ ] 📬 Booking confirmation and cancellation emails
- [ ] 🚦 Rate limiting and CORS configuration
- [ ] ⚙️ CI/CD pipeline (lint, tests, image build)
- [ ] 🏭 Production Docker target and deployment guide
- [ ] 📚 Expanded test coverage for sign-up/login edge cases

---

## 🤝 7. Contributing

Contributions are welcome!

1. **Fork** the repository and create a branch from `develop`:
   ```bash
   git checkout -b feat/your-feature
   ```
2. Follow the existing conventions: one service module per endpoint, thin routers, and tests mirroring `src/` under `tests/`.
3. Format code with **Black** and make sure `pytest` passes.
   If you change how a feature works, update its page in [`documentations/`](documentations/).
4. Use [Conventional Commits](https://www.conventionalcommits.org/) (e.g. `feat:`, `fix:`, `chore:`).
5. Open a **Pull Request** against `develop` describing the change and how it was tested.

### 🗄️ Creating a migration

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

---

## 📄 License

No license file is currently included in this repository, which means all rights are reserved by default. To permit others to use or contribute to the code, add a `LICENSE` file — the [MIT License](https://choosealicense.com/licenses/mit/) is a common, permissive choice for projects like this.

---

<div align="center">

Made with ☕ and 🏝️ by the COZI team

</div>
