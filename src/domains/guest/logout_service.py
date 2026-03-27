def logout(auth_token: str):
    """
    Because the app uses stateless JWT authentication, logout is handled entirely on the client side
    by discarding the token. No server-side invalidation occurs. The endpoint simply verifies the
    presence of the Authorization header — if it's missing, FastAPI automatically returns a 401
    Unauthenticated error.
    """

    return
