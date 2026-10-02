from ulid import ULID


def generate_user_id() -> str:
    """
    Generates a ULID (26 characters, sortable by creation time) to be used as the primary key of the
    users table. The collision chance is negligible, and the primary key constraint remains the safety net.
    """

    return str(ULID())
