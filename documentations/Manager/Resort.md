# Manager · Resort

How masters and admins create and manage resorts. Routes are under `/<STAGE>/api/v1/manager/resorts` (see `/docs` for request shapes). Amenities, photos and the availability calendar are not built yet. See [Manager · Auth](Auth.md) for the two roles.

## Who can do what

| Action | Master | Admin |
| --- | --- | --- |
| Create a resort | Yes, in their own organization | No (`403 MASTER_ONLY`) |
| List resorts | All the resorts of the organization | Only the one they manage |
| See one resort | Yes, with its admin's name and email | Yes (prices included, read only) |
| Edit details (name, description, capacity, address, coordinates) | Yes | Yes, their own resort |
| **Change prices** | **Yes** | **No (`403 MASTER_ONLY`)** |
| Change status (`ACTIVE`, `INACTIVE`, `MAINTENANCE`) | Yes | Yes, their own resort |
| **Invite, resend and remove the admin** | **Yes** | **No (`403 MASTER_ONLY`)** |

Every response is the resort in the same shape (`{"resort": {...}}`), so a client always gets the new state back.

## How a resort is reached

Every endpoint that takes a resort id goes through one check, `get_managed_resort`:

```mermaid
sequenceDiagram
    autonumber
    participant C as Client app
    participant A as API
    participant D as Database

    C->>A: Request for resort {id} with a manager token
    Note over A: Token checks first: guest 401, removed user 401, admin on a master-only endpoint 403
    A->>D: Find the resort that is not removed AND belongs to this manager
    Note over D: Master: its organization is the resort's organization. Admin: its resort_id is this id
    alt No such resort for this manager
        A-->>C: 404 RESORT_DOES_NOT_EXIST
    else
        A-->>C: The endpoint runs
    end
```

A resort that doesn't exist, was removed, or belongs to another master or to a different admin all give the **same 404**, so nobody can discover which resort ids exist.

## Creating a resort

`POST /manager/resorts` (master only).

- The resort is always created in the master's own organization and always starts as a **draft** (`INACTIVE`). The client can't send `organization_id` or `status` (the body rejects unknown fields with a 422).
- Fields: name, description, address, both base prices, currency (`PHP` only), `max_guests`, bedrooms, bathrooms, and optional coordinates.
- A resort name is **unique inside its organization**. Another master can use the same name. The code checks it first and the database enforces it with a unique constraint, so two simultaneous requests can't both succeed.
- Nothing is saved when any rule fails.

| Field | Rule |
| --- | --- |
| `name` | 1 to 256 characters, trimmed |
| `description` | 1 to 5000 characters, trimmed |
| `address` | 1 to 500 characters, trimmed |
| `base_price_per_night`, `base_price_per_day_use` | Above 0, below 10,000,000, at most 4 decimals |
| `max_guests` | 1 to 1000 |
| `num_bedrooms`, `num_bathrooms` | 1 to 100 |
| `latitude`, `longitude` | -90 to 90 and -180 to 180, and both or neither |

## Editing

- **Details** (`PATCH /{id}`): send only the fields to change. An empty body, a `null` for a required field, or any field that isn't listed is a 422. Prices and status can't be changed here. Coordinates can be removed by sending both as `null`. A rename keeps the name rule above.
- **Prices** (`PUT /{id}/pricing`, master only): night price, day-use price and currency. Bookings that already exist keep the price they were made with.
- **Status** (`PUT /{id}/status`, both roles): see below.

## Status and bookings

```mermaid
sequenceDiagram
    autonumber
    participant C as Client app
    participant A as API
    participant D as Database

    C->>A: PUT /resorts/{id}/status {status}
    A->>D: Find the resort of this manager (404 if not theirs)
    alt Resort is ACTIVE and the new status is INACTIVE or MAINTENANCE
        A->>D: Any PENDING or CONFIRMED booking that has not ended yet?
        alt Yes
            A-->>C: 400 RESORT_HAS_UPCOMING_BOOKINGS
        end
    end
    A->>D: Save the status
    A-->>C: 200 with the resort
```

- A live resort can't be closed while guests still have `PENDING` or `CONFIRMED` bookings that haven't ended. They have to be cancelled or finished first.
- Cancelled, completed and expired bookings, and bookings that already ended, don't count.
- Going from `INACTIVE` to `MAINTENANCE` (or back) and reopening to `ACTIVE` are never blocked.

What the status means for guests:

| Status | In the guest list | Details and reviews | New bookings |
| --- | --- | --- | --- |
| `ACTIVE` | Yes | Yes | Yes |
| `MAINTENANCE` | No | Yes | No |
| `INACTIVE` (draft) | No | No (404, same as a missing resort) | No |

## The admin of a resort

A resort has zero or one admin. Only the master invites, resends and removes. The admin is never created by signing up.

| Endpoint | What it does |
| --- | --- |
| `POST /resorts/{id}/admin` | Invite: email, first name, last name and an optional phone |
| `POST /resorts/{id}/admin/resend` | Send a new link to an admin who has not set a password yet |
| `DELETE /resorts/{id}/admin` | Remove the admin |

Every response is the resort. A master sees the admin in it with a `status`: `PENDING` (invited, no password yet) or `ACTIVE`.

```mermaid
sequenceDiagram
    autonumber
    participant M as Master
    participant A as API
    participant D as Database
    participant W as Celery worker
    participant E as Admin (browser)

    M->>A: POST /resorts/{id}/admin {email, names, phone}
    A->>D: Resort is the master's? Resort has no admin? Email not used by a master or admin?
    alt Resort already has an admin
        A-->>M: 400 RESORT_ALREADY_HAS_ADMIN
    else Email is already a master or admin
        A-->>M: 400 EMAIL_REGISTERED
    else
        A->>D: Save admin (no password, not verified) and an INVITE link valid 7 days
        A->>W: Queue the invite email
        A-->>M: 200 resort, admin PENDING
        W-->>E: Email with the invite link
    end

    E->>A: Open the link GET /manager/auth/reset-password?d=token
    A-->>E: "Set your password" page
    E->>A: Submit the new password
    A->>D: Save the password, mark the link used and the admin verified
    A-->>E: "Your account is ready" page
    Note over E,A: The admin can now log in as role admin with their resort_id, and the master sees ACTIVE
```

**Resend.** Only for a `PENDING` admin (`ADMIN_ALREADY_ACTIVE` otherwise, `ADMIN_DOES_NOT_EXIST` if the resort has none). The old link stops working and a new one is sent. It can't be repeated within 5 minutes (`INVITE_RECENTLY_SENT`).

**Remove.** The row stays as a record, but the person is gone and the resort and the email are free:

| Field | After removal |
| --- | --- |
| `deleted_at` | Set, so the admin's token is refused straight away |
| `first_name`, `last_name` | `DELETED`, `ADMIN` |
| `email_address`, `phone_number`, `hashed_password`, `profile_picture`, `active_token` | Cleared |
| `resort_id` | Cleared, so the resort can get a new admin |
| Open invite and password reset links | Marked used, so they can't bring the account back |

The same person can be invited again (a new account with a new id), or sign up as a master. Moving an admin to another resort is remove, then invite.

## Where things are

| What | Where |
| --- | --- |
| Routes and services | `src/domains/manager/resort/` |
| "Is this my resort" check | `services/get_managed_resort.py` |
| Response shape | `services/build_resort_detail.py` |
| Field rules shared by create and edit | `services/resort_field_types.py` |
| Name rules and the unique constraint | `services/check_resort_name.py` and `UniqueConstraint` on `Resort` |
| Upcoming bookings check | `services/has_upcoming_bookings.py` |
| Invite, resend and remove the admin | `admin/` (`invite_admin_service.py`, `resend_admin_invite_service.py`, `remove_admin_service.py`) |
| Invite links and the email | `admin/services/admin_invite.py` and `src/templates/emails/admin_invite_email.html` |
| Master only / manager only dependencies | `src/core/services/auto_user.py` |
| Tests (need Docker) | `tests/domains/manager/resort/` |

## Not built yet

- Amenities, photos and the availability calendar of a resort.
- Moving an admin to another resort (remove, then invite again).
- A resort can be closed (`INACTIVE`) but not deleted.

## Known limitations

- Resort names are compared exactly after trimming, so `Sunrise` and `sunrise` count as different names.
- A resort that was closed while it had no upcoming bookings can still get a booking that was created at the very same moment.
- `PENDING` bookings that are never paid keep blocking the closing of a resort until they are cancelled. Nothing expires them yet.
