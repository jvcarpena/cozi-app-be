from fastapi import HTTPException

from core.models.resort import Resort
from domains.guest.enums import GuestErrorMessage


def validate_guest_capacity(resort: Resort, num_guests: int):

    if num_guests > resort.max_guests:

        raise HTTPException(status_code=400, detail=GuestErrorMessage.NUMBER_OF_GUESTS_EXCEEDS_RESORT_CAPACITY.name)
