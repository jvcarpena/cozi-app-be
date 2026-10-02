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
    A->>D: Any BOOKED / BLOCKED / MAINTENANCE day in the dates?
    alt Conflict found
        A-->>C: 400 RESORT_IS_NOT_AVAILABLE
    end
    Note over A: Compute type, nights and total price (see Pricing)
    alt Preview
        A-->>C: 200 price details, nothing saved
    else Create (guest token required)
        A->>D: Insert booking with status PENDING
        A-->>C: 200 booking
    end
```

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
    else Cancel
        A->>D: Set cancelled_at and cancel_reason
        A-->>C: 200
    end
```

## Pricing

| Duration (check_out - check_in) | Type | Price |
| --- | --- | --- |
| 12 hours or less | `day_use` | `base_price_per_day_use` |
| More than 12 hours | `overnight` | `base_price_per_night × ceil(hours / 24)` |

## Rules worth knowing

- Send timezone-aware datetimes. They are stored in UTC and most responses show Asia/Manila time.
- New bookings are `PENDING`. `CONFIRMED`, `COMPLETED`, `CANCELLED` and `EXPIRED` exist but nothing in the guest API sets them yet.
- The `payments` table (PayMongo) exists but is not connected to bookings.

## Where things are

| What | Where |
| --- | --- |
| Routes and services | `src/domains/guest/booking/` |
| Shared checks | `src/domains/guest/booking/services/` (resort, capacity, availability, price) |
| Models | `src/core/models/booking.py`, `resort_availability.py`, `payments.py` |
| Tests (need Docker) | `tests/domains/guest/booking/` |

## Known limitations

- Creating a booking does **not** write availability rows, so the same dates can be booked twice.
- Cancelling only sets `cancelled_at`. The status stays `PENDING`, so a cancelled booking still shows in the `PENDING` history, and nothing frees the dates.
- A day-use booking on a single date never conflicts, because the availability date range is empty.
