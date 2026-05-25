from pydantic import BaseModel, AwareDatetime


class CreateBookingPreviewRequestDTO(BaseModel):
    resort_id: int
    guest_id: str
    check_in: AwareDatetime
    check_out: AwareDatetime
    num_guests: int


def create_booking_preview():
    pass
