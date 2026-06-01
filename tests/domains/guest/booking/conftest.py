from datetime import timezone, datetime, timedelta
from decimal import Decimal

import pytest

from core.models.booking import Booking, BookingStatusEnum


@pytest.fixture
def booking(db_session, guest, resort):
    db_session.add(
        fake_booking := Booking(
            guest_id=guest.id,
            resort_id=resort.id,
            status=BookingStatusEnum.PENDING,
            check_in=datetime.now(timezone.utc) - timedelta(days=1),
            check_out=datetime.now(timezone.utc) + timedelta(days=2),
            num_guests=24,
            nights=3,
            total_price=Decimal(75000),
            currency="PHP",
        )
    )

    db_session.commit()

    yield fake_booking
