from __future__ import annotations


class EmailAlreadyRegisteredError(Exception):
    """Raised when a registration attempt uses an already-registered email."""

    def __init__(self, email: str) -> None:
        super().__init__(f"Email already registered: {email}")
        self.email = email


class InvalidCredentialsError(Exception):
    """Raised when login credentials do not match any user record."""
