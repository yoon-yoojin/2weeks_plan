class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ModelNotReadyError(AppError):
    def __init__(self):
        super().__init__(
            code="MODEL_UNAVAILABLE",
            message="Model is not ready to serve requests",
            status_code=503,
        )


class BadRequestError(AppError):
    def __init__(self, message: str = "Bad request"):
        super().__init__(
            code="BAD_REQUEST",
            message=message,
            status_code=400,
        )
