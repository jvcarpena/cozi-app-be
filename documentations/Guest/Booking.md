# Guest · Booking

How a guest previews, books, views and cancels a stay. Routes are under `/<STAGE>/api/v1/guest/bookings` (see `/docs` for request shapes). Everything needs a guest token except the preview.

## 1. Preview and create a booking

The preview and the create call run the same checks. The preview stops before saving anything.

```mermaid
sequenceDiagram
    autonumber
    participant C as Client app
    participant A as API
    participant D as Database

    C->>A: POST /bookings/preview or POST /bookings {resort, check_in, check_out, guests}
    alt check_out not after check_in, or fewer than 1 guest
        A-->>C: 422
    end
    A->>D: Load the resort
    alt Resort not found
        A-->>C: 400 RESORT_DOES_NOT_EXIST
    else Resort is INACTIVE
        A-->>C: 400 RESORT_IS_NOT_AVAILABLE
    else Guests more than max_guests
        A-->>C: 400 NUMBER_OF_GUESTS_EXCEEDS_RESORT_CAPACITY
    end
    A->>D: Any BOOKED / BLOCKED / MAINTENANCE row for the booking dates?
    alt Conflict found
        A-->>C: 400 RESORT_IS_NOT_AVAILABLE
    end
    Note over A: Compute type, nights and total price (see Pricing)
    alt Preview
        A-->>C: 200 price details, nothing saved
    else Create (guest token required)
        A->>D: Insert booking with status PENDING
        A->>D: Insert one BOOKED availability row per booking date
        A-->>C: 200 booking
    end
```

The booking and its availability rows are saved in one commit, so a booking never exists without its blocked dates.

### Which dates a booking blocks

| Booking | Dates blocked |
| --- | --- |
| Overnight, e.g. check in 10 Jan, check out 12 Jan | 10 Jan and 11 Jan. The check out date stays free, so the next guests can arrive on 12 Jan |
| Day use (same check in and check out date) | That one date |

The same dates are used for the conflict check and for blocking (`get_booking_dates`).

## 2. View and cancel

```mermaid
sequenceDiagram
    autonumber
    participant C as Client app
    participant A as API
    participant D as Database

    C->>A: GET /bookings?status=PENDING (status is required)
    A->>D: The guest's bookings with that status, newest first
    A-->>C: List

    C->>A: GET /bookings/{id} or PUT /bookings/{id}/cancel {reason}
    A->>D: Find the booking by id AND the current guest
    alt Not found, or it belongs to another guest
        A-->>C: 404 BOOKING_DOES_NOT_EXIST
    else Details
        A-->>C: Booking with resort info
    else Cancel, booking already CANCELLED
        A-->>C: 200, nothing changes
    else Cancel
        A->>D: Set status CANCELLED, cancelled_at and cancel_reason
        A->>D: Delete the booking's BOOKED availability rows
        A-->>C: 200
    end
```

Cancelling frees the dates, so they can be booked again straight away.

## Pricing

| Duration (check_out - check_in) | Type | Price |
| --- | --- | --- |
| 12 hours or less | `day_use` | `base_price_per_day_use` |
| More than 12 hours | `overnight` | `base_price_per_night × ceil(hours / 24)` |

## Rules worth knowing

- Send timezone-aware datetimes. They are stored in UTC and most responses show Asia/Manila time.
- New bookings are `PENDING`, and cancelling sets `CANCELLED`. `CONFIRMED`, `COMPLETED` and `EXPIRED` exist but nothing in the guest API sets them yet.
- A cancelled booking is listed under `status=CANCELLED`, not under `PENDING`.
- The `payments` table (PayMongo) exists but is not connected to bookings.

## Where things are

| What | Where |
| --- | --- |
| Routes and services | `src/domains/guest/booking/` |
| Shared checks | `src/domains/guest/booking/services/` (resort, capacity, availability, price) |
| Models | `src/core/models/booking.py`, `resort_availability.py`, `payments.py` |
| Tests (need Docker) | `tests/domains/guest/booking/` |

## Known limitations

- Two requests for the same dates at the same moment can both pass the availability check, because the database has no unique constraint on `(resort_id, date)`. Adding one (with a migration, and turning the resulting error into a `400`) would close this.
- A `PENDING` booking holds its dates and nothing expires it yet, so unpaid bookings keep the dates blocked until they are cancelled.
