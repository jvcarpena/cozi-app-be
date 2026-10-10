# Decisions

The important design choices in COZI: what the options were, what was chosen, why, and what it costs.

> **Status: draft.** The decisions come from how the project was actually built. Where the reason is marked **(confirm)**, it is an inference and not something recorded at the time, so replace it with your own reasoning. Add a new entry whenever you make a choice you could be asked to defend.

## Contents

1. [Everyone who signs up as a manager is a master, admins are invited](#1-everyone-who-signs-up-as-a-manager-is-a-master-admins-are-invited)
2. [One users table with joined-table inheritance](#2-one-users-table-with-joined-table-inheritance)
3. [Credentials travel as encrypted payloads](#3-credentials-travel-as-encrypted-payloads)
4. [Stateless JWT, one token type per user type](#4-stateless-jwt-one-token-type-per-user-type)
5. [Password reset: signed link plus a request table](#5-password-reset-signed-link-plus-a-request-table)
6. [The reset page is served by the backend](#6-the-reset-page-is-served-by-the-backend)
7. [Forgot password never reveals whether an email exists](#7-forgot-password-never-reveals-whether-an-email-exists)
8. [ULIDs for user ids](#8-ulids-for-user-ids)
9. [Password length rule](#9-password-length-rule)
10. [A booking blocks its dates when it is created](#10-a-booking-blocks-its-dates-when-it-is-created)
11. [Emails are sent by a Celery worker](#11-emails-are-sent-by-a-celery-worker)
12. [Integration tests run on real PostgreSQL and RabbitMQ](#12-integration-tests-run-on-real-postgresql-and-rabbitmq)
13. [One ownership check, and a 404 for any resort that is not yours](#13-one-ownership-check-and-a-404-for-any-resort-that-is-not-yours)
14. [New resorts are drafts, and only an active resort is bookable](#14-new-resorts-are-drafts-and-only-an-active-resort-is-bookable)
15. [Prices have their own master-only endpoint](#15-prices-have-their-own-master-only-endpoint)
16. [A live resort can't be closed while it has upcoming bookings](#16-a-live-resort-cant-be-closed-while-it-has-upcoming-bookings)
17. [Resort names are unique inside an organization](#17-resort-names-are-unique-inside-an-organization)
18. [An admin is invited through the set-password link, with an explicit purpose](#18-an-admin-is-invited-through-the-set-password-link-with-an-explicit-purpose)
19. [Removing an admin keeps the row and frees the identifiers](#19-removing-an-admin-keeps-the-row-and-frees-the-identifiers)

---

## 1. Everyone who signs up as a manager is a master, admins are invited

**Problem.** Resort owners need accounts. Some own one resort, some own several (in Pansol, Calamba, owners of several resorts put an admin in each). Someone has to manage each resort day to day.

**Options**
1. A separate `Manager` user type next to `Admin` and `Master` (the first version built).
2. Ask at sign up "how many resorts do you own?" and create an admin for one, or a master for more than one.
3. **Everyone who signs up is a master.** A master creates resorts and invites an admin for each one if they want to delegate (chosen).

**Chosen.** Option 3. A master owns an organization. A resort belongs to one master (through the organization) and has zero or one admin. A master can do everything an admin can. An admin only sees the resort they manage and never signs up: a master invites them.

**Why**
- There is one sign-up path. A solo owner and an owner of three resorts use the same screen.
- Option 2 would need a way to upgrade an admin to a master when an owner opens a second resort. The two types are separate tables, so that is hard. With option 3 nobody upgrades.
- It also left the admins that a master hires with no way to get an account, because they don't own resorts. Invites solve that.
- The permissions form a simple hierarchy, and the same endpoints can serve both roles, scoped by resort.
- A resort does not need an admin: the master can run it alone until they delegate.

**The sign-up question.** One required field, `organization_name`. A manager with several resorts enters the organization name, a manager with one resort enters the resort name. The server treats both the same, so the different wording is only in the client.

**Trade-offs**
- A person who manages two resorts for a master needs two accounts, because an admin has exactly one resort.
- A solo owner still has an organization. It is hidden behind the one field.
- An admin that hasn't opened the invite link has no password, so login must handle a missing password.
- No foreign key stopped an admin from being linked to a resort of another master, so that rule is checked in the code that scopes resources (a later step).

**Decided, built in later steps**
- *Inviting an admin.* The master enters the admin's email and details. The admin gets a link to set a password, using the password reset flow. Using the link also marks the email verified. The master never sees the password.
- *Removing an admin.* Set `deleted_at`, rename them `DELETED ADMIN`, and also clear their email, phone, password and resort, and mark any open links as used. Clearing the email frees it for a new invite, clearing the resort frees the resort for a new admin, and nothing reads `deleted_at` on its own, so login and the token check refuse a removed user explicitly.
- *Prices.* Only the master edits base prices and calendar price overrides. Everything else is open to both roles.

## 2. One users table with joined-table inheritance

**Problem.** Guests, admins and masters all log in with an email and password.

**Options**
- One `users` table with the common columns, and one table per type for its own columns (joined-table inheritance on `user_type`).
- A completely separate table per type.

**Chosen.** One `users` table plus one table per type.

**Why (confirm).** Email, password and ids are shared, and login code can load any user by id from the token.

**Trade-offs**
- Every load joins two tables.
- A subclass must really extend `User`. `Admin` and `Master` originally did not, so their `user_type` values had no mapper and loading them would have failed.
- Rows that both roles need (`manager_verifications`, `manager_password_reset_requests`) point at the shared `users.id`, not at one role's table.
- All types share one id space, which is one reason ids need to be globally unique (see 8).

## 3. Credentials travel as encrypted payloads

**Problem.** Sign up, login and forgot password carry emails and passwords.

**Chosen.** The client sends `{"data": "<AES-256-GCM encrypted JSON>"}`, using a shared key (`COZI_ENCRYPTION_KEY`), instead of plain JSON.

**Why (confirm).** Credentials are not readable in request logs or by anything in front of the app, even before TLS is in place.

**Trade-offs**
- The key must live in the client too, so this is obfuscation on top of TLS, not a replacement for it.
- Key rotation is not designed.
- A payload that cannot be decrypted returns `400 INVALID_PAYLOAD`, and one with missing or invalid fields returns `422 INVALID_PAYLOAD`. Both used to be a `500`.
- The password reset page is the one exception (see 6).

## 4. Stateless JWT, one token type per user type

**Problem.** Keep users logged in, and make sure a guest can never act as a manager or the other way round.

**Chosen.** A 7-day JWT with the user id. A dependency (`AutoGuestUser`, `AutoManagerUser`) loads the user and rejects the wrong type with `401`.

**Why.** No session store to run, and the type check at the dependency means every endpoint is protected the same way. Plain `AutoUser` had let any user type use guest booking endpoints, which this closed.

**Trade-offs**
- Tokens cannot be revoked. They stay valid for 7 days, even after a password reset.
- The one exception is a removed user. The token check looks at `deleted_at`, so a removed user is refused even with a token that has not expired.
- Fix when needed: a `password_changed_at` check, or a token version, plus refresh tokens.

## 5. Password reset: signed link plus a request table

**Problem.** Let a guest or manager set a new password after forgetting it.

**Options**
1. A 6-digit **OTP** stored (hashed) and typed into the app. Needs attempt counting, hashing, and the email in every request.
2. A **stateless signed token** whose key includes the current password hash, so it dies when the password changes. No table.
3. A **request table** plus a signed token that only carries the request id (chosen).

**Chosen.** Option 3: a row in `guest_password_reset_requests` (or `manager_password_reset_requests`) with `expires_at` and `request_consumed_at`, and an emailed link with a signed token holding the row id.

**Why**
- The OTP was ruled out: it was more machinery than wanted and a worse experience.
- With a row, "expired" and "already used" are answered by the database, and one request can be locked while it is consumed, so two simultaneous submits cannot both succeed.
- The token only holds an id, so it leaks nothing about the account.

**Trade-offs**
- One more table per user type, and a migration.
- The token is in a URL, so it can appear in browser history and logs (see 6).
- The link works for 1 hour. A shorter window is safer.

**Related decision: separate signing keys.** The guest and manager request tables both start counting at 1, so a guest token could have pointed at a manager's request. Each purpose (`password_reset`, `manager_password_reset`) has its own key derived from `TOKEN_SECRET_KEY`. This also stops a reset token from being accepted as a login token.

## 6. The reset page is served by the backend

**Problem.** The emailed link has to open a page with a new-password form.

**Options**
- A frontend route that posts encrypted JSON to the API.
- A page served by the API (`reset_password.html`), like the existing verification page.

**Chosen.** The backend serves the page and accepts a normal form post.

**Why.** No dependency on a frontend, and it follows how email verification already works.

**Trade-offs**
- The password is sent as a plain form field, so the page **must** be served over HTTPS.
- The request logging middleware would have logged the password and token, so it now redacts `/auth/reset-password` requests. Any new route that carries a secret needs the same treatment.
- It is the one place where credentials are not encrypted payloads (see 3).

## 7. Forgot password never reveals whether an email exists

**Problem.** A reset endpoint can be used to find out which emails are registered.

**Chosen.** `forgot-password` always returns the same `200` and message, for unknown emails, unverified accounts and accounts that already have an active request. Only verified accounts get an email, and a new email is not sent while an unexpired request exists.

**Why.** It removes the enumeration signal for this endpoint.

**Trade-offs**
- Login and sign up still reveal whether an email exists (`EMAIL_NOT_EXISTS`, `EMAIL_REGISTERED`), so the protection is partial.
- There is no per-account cooldown, so someone could cause one reset email per hour to a victim's address.
- A user who deletes the email has to wait for the hour to pass to get a new link.

## 8. ULIDs for user ids

**Problem.** The old id was a random 10-character string. To keep it unique, sign up loaded **every** existing id into memory and looped until it found a free one.

**Options**
- Keep the random string and the check.
- UUID v4, or UUID v7.
- ULID: 128 bits, sortable by creation time.

**Chosen.** ULID, from one helper (`generate_user_id`) used by both sign up flows.

**Why.** No uniqueness query and no loading the whole table. A collision is practically impossible, and the primary key stays as the safety net. The id fits the existing `String(256)` column, so no migration was needed. Ids sort by creation time.

**Trade-offs**
- Old 10-character ids and new ULIDs now coexist.
- A ULID exposes roughly when the account was created.
- A collision would fail at the primary key with a `500` instead of being retried.

## 9. Password length rule

**Chosen.** 6 to 72 characters on guest sign up, manager sign up and password reset, from one validator. Login does not check the length.

**Why**
- 72 is the **bcrypt** limit. bcrypt 5 raises an error above 72 bytes, so without the check a long password would be a `500`.
- Login is excluded so that anyone who signed up with a shorter password can still log in.

**Trade-offs**
- Six characters is a low minimum, and there is no complexity rule.
- A user with an older short password can log in but cannot reset to a password like it.

## 10. A booking blocks its dates when it is created

**Problem.** Two guests must not book the same resort on the same dates.

**Chosen.** Creating a booking writes one `BOOKED` row in `resort_availabilities` for each night, in the same commit as the booking. Cancelling sets the booking to `CANCELLED` and deletes those rows. The same function (`get_booking_dates`) decides which dates a booking occupies for both the conflict check and the blocking.

- An overnight stay occupies check-in up to, but not including, the check-out date, so the next guests can arrive that day.
- A day-use booking occupies its single date.

**Why.** Before this, the availability table was only read, never written, so the check could never fail for a booking made through the API.

**Trade-offs**
- **Race condition.** Two requests for the same dates at the same moment can both pass the check. The proper fix is a unique constraint on `(resort_id, date)` (and turning the resulting error into a `400`), which needs a migration.
- **No expiry.** A `PENDING` booking holds its dates until it is cancelled. Once payments exist, unpaid bookings need an expiry job.
- Dates are taken from the datetimes the client sends, so the client's time zone decides which calendar day a booking falls on.

## 11. Emails are sent by a Celery worker

**Problem.** Sending an email over SMTP is slow and can fail, and should not block a request.

**Chosen.** The API queues `send_email_task` through RabbitMQ and a worker sends the email. SMTP settings come from environment variables.

**Why.** Requests return immediately, and a slow or failed mail server does not slow the API.

**Trade-offs**
- A worker must be running, or emails silently never go out.
- The task catches every error and only logs it, so the configured retries never happen and a failed email is lost.
- The old SMTP password was committed to git. It is now read from the environment, but it must still be rotated because it remains in the history.

## 12. Integration tests run on real PostgreSQL and RabbitMQ

**Chosen.** Tests start throwaway PostgreSQL and RabbitMQ containers (testcontainers) and call the real FastAPI app. The only common mock is `send_email_task`, when a test just needs to check what was queued.

**Why.** The behaviour that matters here (row locks, joined inheritance, constraints, date handling) is not reproduced by SQLite or by mocking the session. The tests catch problems the unit-level mocks would hide.

**Trade-offs**
- Docker must be running, and the suite is slower.
- There is no CI pipeline yet, so the suite is only as reliable as the last time someone ran it.

## 13. One ownership check, and a 404 for any resort that is not yours

**Problem.** A master has several resorts and an admin has one. Every resort endpoint must make sure the caller may touch that resort, and the check was copy-pasted in each service. Two of them had forgotten it (any manager could read any resort, any admin could change any resort's status).

**Options**
- Check ownership in every service, answering `403 NOT_YOUR_RESORT` for another manager's resort.
- One shared check (`get_managed_resort`) that every endpoint calls, answering `404` for anything that is not yours (chosen).

**Why.** A single function cannot be forgotten in one endpoint, and a new endpoint only has to call it. The same `404` for "doesn't exist", "removed" and "not yours" means a manager can't learn which resort ids exist, and the response never contains data about someone else's resort.

**Trade-offs**
- A manager who mistypes an id gets "does not exist" instead of "not yours". It's less helpful, and also less revealing.
- Role limits (like prices) are still separate: a master-only endpoint refuses an admin with `403 MASTER_ONLY` before any resort is looked up, because the token is valid and only the role is wrong.

## 14. New resorts are drafts, and only an active resort is bookable

**Problem.** A master creates a resort in one request, but it isn't ready for guests until its details, prices and (later) photos are right.

**Chosen.** A new resort starts as `INACTIVE` (a draft). The manager activates it. Guests only see and book what is ready:
- the guest list shows `ACTIVE` resorts
- details and reviews work for `ACTIVE` and `MAINTENANCE`, and answer `404` for a draft, the same as a missing resort
- only an `ACTIVE` resort can be booked

**Why.** Before this, a resort created by a manager would have been visible to guests by id at once, and a resort under maintenance could still be booked. Making the draft look like a missing resort also stops guests from discovering unfinished resorts.

**Trade-offs**
- A resort that needs no review step (a single owner with everything ready) still has one extra call to go live.
- `MAINTENANCE` keeps its page visible but is closed to new bookings.

## 15. Prices have their own master-only endpoint

**Problem.** Only the master may change prices. An admin may change everything else about a resort.

**Options**
- One edit endpoint that checks the role field by field.
- A separate pricing endpoint that only masters can call, and an edit endpoint that rejects price fields (chosen).

**Why.** The permission is clear from the URL and the dependency, not from reading the body. The edit endpoint rejects unknown fields with a `422`, so an admin who sends a price is told it wasn't accepted instead of getting a `200` that did nothing.

**Trade-offs**
- Two calls when a master wants to change both details and prices.
- Existing bookings keep the price they were made with, because each booking stores its own total.

## 16. A live resort can't be closed while it has upcoming bookings

**Problem.** Closing a resort (`INACTIVE` or `MAINTENANCE`) stops new bookings, but guests who already booked would be left with a resort that is closed.

**Options**
- Allow it and leave the bookings.
- Allow it and cancel the bookings automatically.
- **Block it until the bookings are handled** (chosen).

**Why.** Cancelling for the manager would refund money and message guests, and that flow doesn't exist yet. Blocking is the safe choice that forces the manager to handle each booking.

**Rule.** Moving from `ACTIVE` to `INACTIVE` or `MAINTENANCE` is refused while a `PENDING` or `CONFIRMED` booking has not ended yet. Moving between closed statuses, and reopening, are never blocked.

**Trade-offs**
- A `PENDING` booking that is never paid blocks the closing until it's cancelled. A job that expires unpaid bookings is still to be built.
- A guest booking at the very same moment as the status change can slip through.

## 17. Resort names are unique inside an organization

**Problem.** A master with several resorts shouldn't end up with two of the same name, but different masters can legitimately use the same name.

**Chosen.** A unique constraint on `(organization_id, name)`, plus a check before saving that gives a clear `400 RESORT_NAME_ALREADY_EXISTS`. If two requests pass the check together, the constraint stops the second and the same error is returned.

**Why.** The first version of the check searched every organization, which blocked valid names and revealed other masters' resort names. The database constraint is the real guarantee, the check is only for the friendly error.

**Trade-offs**
- Names are compared exactly after trimming, so `Sunrise` and `sunrise` are different.
- A removed resort still holds its name, because the constraint doesn't ignore `deleted_at`. Removing resorts isn't built yet.

## 18. An admin is invited through the set-password link, with an explicit purpose

**Problem.** A master has to give an admin access to one resort. The admin must end up with a password only they know, and a verified email.

**Options**
1. The master chooses a password for the admin.
2. A separate invite mechanism with its own table and page.
3. **Reuse the password reset flow** (chosen): create the admin with no password and email a link to the page where a password is set.

**Why option 3.** The master never sees the password. Opening the emailed link proves the email is theirs, so setting the password also verifies the account. The table, token, page and rules already exist and are tested.

**Why a `purpose` column.** An invite and a password reset are different: an invite lasts 7 days (a reset 1 hour), uses a different email, and the page should say "set" a password, not "reset" it. The first idea was to guess the difference from the account being unverified. A `purpose` (`RESET` or `INVITE`) on the request is explicit and doesn't depend on that coincidence. It needs a migration with a default of `RESET` for the rows that already exist.

**Trade-offs**
- A pending admin who uses forgot password gets the generic answer and no email (they have no password to forget). They have to ask the master to resend.
- Resending is limited to once every 5 minutes so a master can't flood an inbox, and it closes the older link.
- The email is queued after the commit and the Celery task logs errors without retrying, so a lost email is recovered with resend.

## 19. Removing an admin keeps the row and frees the identifiers

**Problem.** When a master removes an admin, that person must lose access at once, and the resort and the email must be usable again.

**Options**
- Hard delete the row.
- **Keep the row, mark it deleted, and clear the person's data** (chosen).

**Chosen.** Set `deleted_at`, rename them `DELETED ADMIN`, and clear the email, phone, password, picture, stored token and `resort_id`. All open links are marked used. Inviting the same person again creates a new account.

**Why**
- The row stays as a record for anything that refers to the user later, such as audit history.
- Clearing the email frees it for a new invite or a sign up. Clearing `resort_id` frees the unique link, so the resort can get a new admin.
- Nothing reads `deleted_at` on its own, so the token check refuses a removed user explicitly. That makes the removal take effect immediately, even for a token that has not expired.
- Open links are closed so an old invite or password reset can't bring the account back.

**Trade-offs**
- Anything that will show a removed admin later (for example a history of who did what) must expect a missing email and the name `DELETED ADMIN`.
- Nothing links the old and new account of the same person.
