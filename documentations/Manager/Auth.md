# Manager · Auth

How a manager signs up and logs in. A **manager is an admin**: the person who owns or manages **one resort**. The code calls them `Admin`, the API calls them `manager`. Routes are under `/<STAGE>/api/v1/manager/auth`.

The flow is a copy of the guest one. See [Guest · Auth](../Guest/Auth.md) for encrypted payloads, tokens and emails. Only the differences are here.

## Differences from guest

| Topic | Guest | Manager |
| --- | --- | --- |
| Paths | `/sign-up`, `/verification` | `/signup`, `/verify` |
| Tables | `guests`, `guest_verifications` | `admins`, `manager_verifications` |
| Login response id | `guest_id` | `manager_id` |
| Logout | Only needs the header | Also checks the token belongs to a manager |
| Forgot / reset password | Yes | Not built yet |

A new manager has no resort yet. `organization_id` and `resort_id` on `admins` stay empty until the manager adds a resort.

## 1. Sign up and verify

```mermaid
sequenceDiagram
    autonumber
    participant C as Client app
    participant A as API
    participant D as Database
    participant W as Celery worker

    C->>A: POST /signup {data: encrypted}
    Note over A: Same checks as guest: decrypt, name, password 6-72
    A->>D: Find admin by email
    alt Already verified
        A-->>C: 400 EMAIL_REGISTERED
    else Unverified, last email under 24h ago
        A-->>C: 400 CHECK_YOUR_EMAIL
    else New, or unverified and over 24h ago
        A->>D: Save admin and manager_verifications row
        A->>W: Queue the verification email
        A-->>C: 200
        W-->>C: Email with link to /manager/auth/verify?d=token
    end

    C->>A: Open the link GET /verify, then click POST /verify
    alt Not found 400 ACCOUNT_DOES_NOT_EXISTS, or older than 24h 400 LINK_EXPIRED
        A-->>C: 400
    else
        A->>D: Set verified_at
        A-->>C: "Account Verified" page
    end
```

Login works like guest login and returns `manager_id`, the name and a 7-day JWT.

## 2. Guest and manager tokens are separate

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant A as API
    participant D as Database

    C->>A: Request with Authorization: JWT
    A->>D: Load user by the id in the token
    Note over A: users table holds guests, admins (managers) and masters
    alt Manager endpoint and the user is an Admin
        A-->>C: Allowed
    else Guest endpoint and the user is a Guest
        A-->>C: Allowed
    else Wrong user type
        A-->>C: 401 INVALID_SESSION
    end
```

All user types share the `users` table (SQLAlchemy joined inheritance, chosen by `user_type`):

| `user_type` | Model | Meaning |
| --- | --- | --- |
| `guest` | `Guest` | Books resorts |
| `admin` | `Admin` | Manager of a single resort |
| `master` | `Master` | Owns multiple resorts with an admin in each (mapped, no endpoints yet) |

## Where things are

| What | Where |
| --- | --- |
| Routes and services | `src/domains/manager/auth/` |
| Error names | `src/domains/manager/enums.py` (plus the shared `INVALID_NAME`, `INVALID_PASSWORD_LENGTH`) |
| Models | `src/core/models/admin.py`, `manager_verification.py`, `master.py` |
| Manager token check | `AutoManagerUser` in `src/core/services/auto_user.py` |
| Tests (need Docker) | `tests/domains/manager/auth/` |

## Not built yet

Forgot/reset password for managers, master auth, creating a resort, and foreign keys from `admins.resort_id` and `organization_id` to `resorts` and `organizations`.
