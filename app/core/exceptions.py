from fastapi import HTTPException


class HermesBaseException(HTTPException):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        self.code = code
        self.detail = message
        super().__init__(status_code=status_code, detail=message)


class AuthenticationError(HermesBaseException):
    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(code="AUTH_ERROR", message=message, status_code=401)


class SignatureError(HermesBaseException):
    def __init__(self, message: str = "Signature verification failed") -> None:
        super().__init__(code="SIGNATURE_ERROR", message=message, status_code=401)


class NonceExpiredError(HermesBaseException):
    def __init__(self, message: str = "Nonce expired or already used") -> None:
        super().__init__(code="NONCE_EXPIRED", message=message, status_code=401)


class PermissionDeniedError(HermesBaseException):
    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(code="PERMISSION_DENIED", message=message, status_code=403)


class ResourceNotFoundError(HermesBaseException):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(code="NOT_FOUND", message=message, status_code=404)


class AlreadyExistsError(HermesBaseException):
    def __init__(self, message: str = "Resource already exists") -> None:
        super().__init__(code="ALREADY_EXISTS", message=message, status_code=409)


class ConflictError(HermesBaseException):
    def __init__(self, message: str = "Resource conflict") -> None:
        super().__init__(code="CONFLICT", message=message, status_code=409)


class FileValidationError(HermesBaseException):
    def __init__(self, message: str = "File validation failed") -> None:
        super().__init__(code="FILE_VALIDATION_ERROR", message=message, status_code=400)


class StorageError(HermesBaseException):
    def __init__(self, message: str = "Storage operation failed") -> None:
        super().__init__(code="STORAGE_ERROR", message=message, status_code=500)
