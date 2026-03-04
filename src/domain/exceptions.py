"""
Domain exceptions for the users service.
"""


class DomainError(Exception):
    """Base domain error."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class UserNotFoundError(DomainError):
    def __init__(self, message: str = "No existe un usuario con ese ID") -> None:
        super().__init__(code="USER_NOT_FOUND", message=message)


class ClientNotFoundError(DomainError):
    def __init__(self, message: str = "No existe un cliente con ese ID") -> None:
        super().__init__(code="CLIENT_NOT_FOUND", message=message)


class EmailAlreadyExistsError(DomainError):
    def __init__(self, message: str = "Ya existe un registro con ese email") -> None:
        super().__init__(code="EMAIL_ALREADY_EXISTS", message=message)


class ForbiddenError(DomainError):
    def __init__(self, message: str = "No tiene permisos para esta acción") -> None:
        super().__init__(code="FORBIDDEN", message=message)
