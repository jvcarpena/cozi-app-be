# Manager · Auth

How a manager signs up, logs in and recovers a password. A **manager is an admin**: the person who owns or manages **one resort**. The code calls them `Admin`, the API calls them `manager`. Routes are under `/<STAGE>/api/v1/manager/auth`.

The flow is a copy of the guest one. See [Guest · Auth](../Guest/Auth.md) for encrypted payloads, tokens and emails. Only the differences are here.

## Differences from guest

| Topic | Guest | Manager |
| --- | --- | --- |
| Paths | `/sign-up`, `/verification` | `/signup`, `/verify` |
| Tables | `guests`, `guest_verifications` | `admins`, `manager_verifications` |
| Login response id | `guest_id` | `manager_id` |
| Logout | Only needs the header | Also checks the token belongs to a manager |
| Forgot / reset password | `/forgot-password`, `/reset-password` | Same paths, under `/manager/auth` |
| Reset tables | `guest_password_reset_requests` | `manager_password_reset_requests` |

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

## 2. Forgot and reset password

Same flow as [guest forgot and reset password](../Guest/Auth.md#4-forgot-password), with a manager's own request table, links and pages. The reset page is the same HTML page, posting to `/manager/auth/reset-password`.

```mermaid
sequenceDiagram
    autonumber
    participant C as Client app
    participant A as API
    participant D as Database
    participant W as Celery worker
    participant U as Manager (browser)

    C->>A: POST /forgot-password {data: encrypted email}
    A->>D: Find admin and the latest reset request
    alt Not a manager, unverified, or an active request already exists
        Note over A: Do nothing, no email
    else
        A->>D: Insert manager_password_reset_requests (expires in 1 hour)
        Note over A: Build a token signed for managers only
        A->>W: Queue the reset email with a /manager/auth/reset-password link
    end
    A-->>C: 200 with the same generic message in every case

    U->>A: Open the link GET /reset-password?d=token
    alt Token invalid, expired, used, or not a manager token
        A-->>U: 400 "Link Expired" page
    else
        A-->>U: Form with new and confirm password
    end
    U->>A: Submit POST /reset-password (token, new, confirm)
    alt Passwords differ, or not 6 to 72 characters
        A-->>U: 400 form shown again with the message
    else
        A->>D: Lock the request, save the new hash, mark it consumed
        A-->>U: "Password Updated" page
    end
```

**Guest and manager reset tokens are not interchangeable.** The token only holds a request id, so each type is signed with its own key (`password_reset` for guests, `manager_password_reset` for managers). A guest token cannot open or use the manager page, and the other way round, even though both request tables start counting ids from 1.

## 3. Guest and manager tokens are separate

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
| Models | `src/core/models/admin.py`, `manager_verification.py`, `manager_password_reset_request.py`, `master.py` |
| Forgot / reset password | `initiate_password_reset.py`, `reset_password.py`, `get_active_password_reset_request.py` in `src/domains/manager/auth/` |
| Reset token | `PasswordResetTokenHandler` (with `MANAGER_PURPOSE`) in `src/core/services/password_reset_token_handler.py` |
| Pages and email | Shared with guest: `reset_password.html`, `password_reset_success.html`, `emails/password_reset_email.html` |
| Manager token check | `AutoManagerUser` in `src/core/services/auto_user.py` |
| Tests (need Docker) | `tests/domains/manager/auth/` |

## Not built yet

Master auth, creating a resort, and foreign keys from `admins.resort_id` and `organization_id` to `resorts` and `organizations`.
