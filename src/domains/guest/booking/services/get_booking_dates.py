from datetime import date, timedelta


def get_booking_dates(check_in_date: date, check_out_date: date) -> list[date]:
    """
    The dates a booking occupies: from the check in date up to, but not including, the check out date,
    because the resort is free again on the day the guests leave.

    A day use booking starts and ends on the same date, so it occupies that one date.
    """

    if check_out_date <= check_in_date:

        return [check_in_date]

    return [check_in_date + timedelta(days=days) for days in range((check_out_date - check_in_date).days)]
