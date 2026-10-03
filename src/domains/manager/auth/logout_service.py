from core.models.admin import Admin
from core.models.master import Master


def logout(manager: Master | Admin):
    """
    Because the app uses stateless JWT authentication, logout is handled entirely on the client side
    by discarding the token. No server-side invalidation occurs. The endpoint only verifies that the
    Authorization header holds a valid token that belongs to a manager (a master or an admin) — if the header is missing,
    FastAPI automatically returns a 401 Unauthenticated error, and a token that does not belong to
    a manager is rejected.
    """

    return
