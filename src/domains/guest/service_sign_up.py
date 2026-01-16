import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.guest import Guest


def generate_unique_guest_id(session: Session):

    guest_ids = session.scalars(select(Guest.id)).all()

    while True:

        generated_guest_id = "".join(random.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(10))

        if generated_guest_id not in guest_ids:

            return generated_guest_id


def sign_up():
    pass
