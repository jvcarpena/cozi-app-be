# Manager · Auth

How managers sign up, log in and recover a password. Routes are under `/<STAGE>/api/v1/manager/auth`.

The flow is a copy of the guest one. See [Guest · Auth](../Guest/Auth.md) for encrypted payloads, tokens and emails. Only the differences are here.

## Two roles

| Role | Who | How the account is created | Resorts |
| --- | --- | --- | --- |
| **Master** | The owner. Whoever signs up as a manager, with one resort or many | Signs up | Owns an **organization** that holds all their resorts |
| **Admin** | The person in charge of one resort day to day | **Invited by a master** (see [Manager · Resort](Resort.md#the-admin-of-a-resort)) | Manages exactly **one** resort |

- A master can do everything an admin can. A master also creates resorts, sets their prices and invites the admins. An admin only sees the resort they manage.
- A resort belongs to one master (through the organization) and has zero or one admin. A master can run a resort alone until they invite an admin.
- An admin never signs up. Their email can't be used to sign up as a master.

The database model:

```mermaid
erDiagram
    ORGANIZATION ||--|| MASTER : "owned by"
    ORGANIZATION ||--o{ RESORT : has
    RESORT ||--o| ADMIN : "managed by"
```

| `user_type` | Model | Extra data |
| --- | --- | --- |
| `master` | `Master` | `organization_id` (unique), name, phone |
| `admin` | `Admin` | `resort_id` (unique, empty once removed), name, phone |

Both share the `users` table, plus `manager_verifications` and `manager_password_reset_requests`, which point at `users.id`.

## 1. Sign up and verify (creates a master)

The decrypted payload is the guest one plus `organization_name`. It is required (1 to 256 characters). A manager with several resorts enters the name of their organization. A manager with one resort enters the name of the resort. The server treats both the same.

```mermaid
sequenceDiagram
    autonumber
    participant C as Client app
    participant A as API
    participant D as Database
    participant W as Celery worker

    C->>A: POST /signup {data: encrypted}
    Note over A: Decrypt (400 or 422 INVALID_PAYLOAD if bad), check name, password 6-72, organization name
    A->>D: Find a master or admin with that email (removed ones are ignored)
    alt Email belongs to an admin, or to a verified master
        A-->>C: 400 EMAIL_REGISTERED
    else Unverified master, last email under 24h ago
        A-->>C: 400 CHECK_YOUR_EMAIL
    else New, or unverified master and over 24h ago
        A->>D: Save organization, master and manager_verifications row in one transaction
        A->>W: Queue the verification email
        A-->>C: 200
        W-->>C: Email with link to /manager/auth/verify?d=token
    end

    C->>A: Open the link GET /verify, then click POST /verify
    alt Not a master 400 ACCOUNT_DOES_NOT_EXISTS, or older than 24h 400 LINK_EXPIRED
        A-->>C: 400
    else
        A->>D: Set verified_at
        A-->>C: "Account Verified" page
    end
```

## 2. Login (master or admin)

`POST /login` finds the master or admin by email and returns the role, so the client knows which screens to show.

| Field | Master | Admin |
| --- | --- | --- |
| `role` | `"master"` | `"admin"` |
| `organization_id`, `organization_name` | The organization | `null` |
| `resort_id` | `null` | The resort they manage |

Errors: `EMAIL_NOT_EXISTS` (unknown, or the account was removed), `EMAIL_NOT_VERIFIED`, `INVALID_CREDENTIALS`. An admin who was invited but has not set a password yet also gets `INVALID_CREDENTIALS`.

## 3. Forgot and reset password (master or admin)

Same flow as [guest forgot and reset password](../Guest/Auth.md#4-forgot-password), with its own request table, links and tokens, and for both roles. The reset page is the same HTML page, posting to `/manager/auth/reset-password`.

```mermaid
sequenceDiagram
    autonumber
    participant C as Client app
    participant A as API
    participant D as Database
    participant W as Celery worker
    participant U as Manager (browser)

    C->>A: POST /forgot-password {data: encrypted email}
    A->>D: Find the master or admin and the latest reset request
    alt Not a manager, removed, unverified, or an active request already exists
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
        A->>D: If the account is not verified yet, mark it verified
        A-->>U: "Password Updated" page
    end
```

- **Guest and manager reset tokens are not interchangeable.** The token only holds a request id, so each type is signed with its own key (`password_reset` for guests, `manager_password_reset` for managers).
- **Using the link also verifies the email.** The link was sent to the address, so using it proves the address is theirs. This is how an invited admin will get started: the invite link sets their password and verifies them in one step.
- A **removed** manager can't use a link that was sent before they were removed.
- **Reset or invite.** Every link request has a `purpose`: `RESET` (forgot password, lives 1 hour) or `INVITE` (a master invited an admin, lives 7 days). Both open this same page and use the same token. The page says "Set your password" for an invite and "Reset your password" otherwise, and the success page changes the same way. Forgot password only looks at `RESET` requests.

## 4. Who can call what

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant A as API
    participant D as Database

    C->>A: Request with Authorization: JWT
    A->>D: Load user by the id in the token
    alt User was removed (deleted_at is set)
        A-->>C: 401 INVALID_SESSION
    else Endpoint needs a master and the user is a Master
        A-->>C: Allowed
    else Endpoint needs an admin and the user is an Admin
        A-->>C: Allowed
    else Endpoint is for any manager and the user is a Master or Admin
        A-->>C: Allowed
    else Guest endpoint and the user is a Guest
        A-->>C: Allowed
    else Wrong user type
        A-->>C: 401 INVALID_SESSION
    end
```

The dependencies are in `src/core/services/auto_user.py`: `AutoMasterUser`, `AutoAdminUser`, `AutoManagerUser` (a master or an admin, used by logout) and `AutoGuestUser`. A removed user is refused even with a token that has not expired.

## Where things are

| What | Where |
| --- | --- |
| Routes and services | `src/domains/manager/auth/` |
| Find a manager by email | `get_manager_by_email.py` (masters and admins, never removed ones) |
| Manager sign up payload | `src/domains/manager/dtos/sign_up_dto.py` |
| Error names | `src/domains/manager/enums.py` (plus the shared `INVALID_NAME`, `INVALID_PASSWORD_LENGTH`, and `INVALID_PAYLOAD` from `secure_payload_handler.py`) |
| Models | `src/core/models/master.py`, `admin.py`, `organization.py`, `manager_verification.py`, `manager_password_reset_request.py` |
| Reset token | `PasswordResetTokenHandler` (with `MANAGER_PURPOSE`) in `src/core/services/password_reset_token_handler.py` |
| Pages and email | Shared with guest: `reset_password.html`, `password_reset_success.html`, `emails/password_reset_email.html` |
| Tests (need Docker) | `tests/domains/manager/auth/` |

## Not built yet

- Amenities, photos and the availability calendar of a resort (see [Manager · Resort](Resort.md)).
- Moving an admin to another resort. Today it is remove, then invite again.
