# Guest · Auth

How a guest signs up, logs in and recovers a password. Routes are under `/<STAGE>/api/v1/guest/auth` (see `/docs` for request shapes).

## Key ideas

- **Encrypted credentials.** Sign up, login and forgot password send `{"data": "<encrypted>"}`, encrypted with AES-256-GCM (`SecurePayloadHandler`, key `COZI_ENCRYPTION_KEY`). The verify and reset pages are plain HTML forms.
- **Stateless JWT.** Login returns a 7-day token (`TOKEN_SECRET_KEY`) that the client sends in the `Authorization` header. Logout just means the client drops it.
- **Emails go through Celery.** The API only queues `send_email_task`. A worker sends the email over SMTP, so a running worker is required.
- **Passwords** are bcrypt-hashed and must be 6 to 72 characters (sign up and reset).

## 1. Sign up

```mermaid
sequenceDiagram
    autonumber
    participant C as Client app
    participant A as API
    participant D as Database
    participant W as Celery worker

    C->>A: POST /sign-up {data: encrypted}
    Note over A: Decrypt, check name and password length
    A->>D: Find guest by email
    alt Guest already verified
        A-->>C: 400 EMAIL_REGISTERED
    else Unverified, last email sent under 24h ago
        A-->>C: 400 CHECK_YOUR_EMAIL
    else New guest, or unverified and over 24h ago
        A->>D: Save guest and verification row (or update the existing ones)
        A->>W: Queue the verification email
        A-->>C: 200
        W-->>C: Email with a verification link, valid 24h
    end
```

## 2. Email verification

```mermaid
sequenceDiagram
    autonumber
    participant U as Guest (browser)
    participant A as API
    participant D as Database

    U->>A: Open the emailed link GET /verification?d=token
    A-->>U: Page with a "Verify My Account" button
    U->>A: Click the button POST /verification (token)
    Note over A: Decrypt the token
    A->>D: Find guest
    alt Guest not found
        A-->>U: 400 ACCOUNT_DOES_NOT_EXISTS
    else Link older than 24h
        A-->>U: 400 LINK_EXPIRED
    else
        A->>D: Set verified_at
        A-->>U: "Account Verified" page
    end
```

## 3. Login and using the token

```mermaid
sequenceDiagram
    autonumber
    participant C as Client app
    participant A as API
    participant D as Database

    C->>A: POST /login {data: encrypted}
    A->>D: Find guest by email
    alt Not found
        A-->>C: 400 EMAIL_NOT_EXISTS
    else Email not verified
        A-->>C: 400 EMAIL_NOT_VERIFIED
    else Wrong password
        A-->>C: 400 INVALID_CREDENTIALS
    else
        A-->>C: 200 profile + JWT (7 days)
    end

    Note over C,A: Later requests
    C->>A: Any guest endpoint with Authorization: JWT
    A->>D: Load user by the id in the token
    alt Token invalid or expired, or the user is not a guest
        A-->>C: 401 INVALID_SESSION
    else
        A-->>C: Normal response
    end
```

## 4. Forgot password

```mermaid
sequenceDiagram
    autonumber
    participant C as Client app
    participant A as API
    participant D as Database
    participant W as Celery worker

    C->>A: POST /forgot-password {data: encrypted email}
    A->>D: Find guest and the latest reset request
    alt Guest missing, unverified, or an active request already exists
        Note over A: Do nothing, no email
    else
        A->>D: Insert reset request (expires in 1 hour)
        Note over A: Build a signed token that holds the request id
        A->>W: Queue the reset email with the link
        W-->>C: Email with the reset link
    end
    A-->>C: 200 with the same generic message in every case
```

The same response for every case is what stops the endpoint from revealing which emails are registered.

## 5. Reset password

```mermaid
sequenceDiagram
    autonumber
    participant U as Guest (browser)
    participant A as API
    participant D as Database

    U->>A: Open the emailed link GET /reset-password?d=token
    A->>D: Check the token and its request (not expired, not used)
    alt Link not usable
        A-->>U: 400 "Link Expired" page
    else
        A-->>U: Form with new and confirm password
    end

    U->>A: Submit POST /reset-password (token, new, confirm)
    alt Passwords differ, or not 6 to 72 characters
        A-->>U: 400 form shown again with the message
    else
        A->>D: Lock the request and re-check it
        A->>D: Save the new password hash, mark the request consumed
        A-->>U: "Password Updated" page
    end
```

The token is signed with a key derived from `TOKEN_SECRET_KEY` and only holds the request id, so it can never be used as a login token. The database row decides if the link is expired or used, so each link works once.

## Data

`users` (ULID id, email, `user_type`, hashed password) is the base table. `guests` extends it with name and phone (SQLAlchemy joined inheritance). Related tables: `guest_verifications`, `guest_password_reset_requests`.

## Where things are

| What | Where |
| --- | --- |
| Routes and services | `src/domains/guest/auth/` |
| DTOs and validators | `src/domains/guest/dtos/sign_up_login_dto.py` |
| Error names (`{"detail": "<NAME>"}`) | `src/domains/guest/enums.py` |
| Models | `src/core/models/guest*.py`, `user.py` |
| Encryption and tokens | `src/core/services/` (`secure_payload_handler.py`, `auth_token_handler.py`, `password_reset_token_handler.py`) |
| Pages and emails | `src/templates/` |
| Tests (need Docker) | `tests/domains/guest/auth/` |

Env vars: `STAGE`, `DB_URL`, `TOKEN_SECRET_KEY`, `COZI_ENCRYPTION_KEY`, `SMTP_*`, `RABBITMQ_URL`, and optionally `API_BASE_URL` (base of the reset link).

## Known limitations

- A malformed encrypted payload returns `500` instead of `400`.
- Login and sign up reveal whether an email is registered. Only forgot password hides it.
- Login tokens are not revoked after a password reset.
- `otel_handler` redacts the query and body of `/auth/reset-password`, so the token and password are not logged. Serve that page over HTTPS in production.
