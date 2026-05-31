import math
from decimal import Decimal

from core.models.resort import Resort


def compute_booking_price(resort: Resort, duration_hours: float) -> tuple[str, int | None, Decimal]:

    if duration_hours <= 12:
        return "day_use", None, resort.base_price_per_day_use

    nights = math.ceil(duration_hours / 24)

    return "overnight", nights, resort.base_price_per_night * nights
