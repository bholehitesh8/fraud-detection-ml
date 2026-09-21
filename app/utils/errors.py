"""
Centralized Error Handling and Application Exception Module
------------------------------------------------------------
Implements robust, enterprise-grade centralized error handlers for:
- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found
- 405 Method Not Allowed
- 409 Conflict
- 422 Validation Error
- 429 Too Many Requests
- 500 Internal Server Error

Supports intelligent content negotiation (JSON for REST APIs, styled HTML for browser views).
Ensures zero stack trace or internal implementation leakage in production responses.
"""

from datetime import datetime, timezone
import logging
from flask import jsonify, render_template, request, Flask
from werkzeug.exceptions import HTTPException

logger = logging.getLogger("fraud_detection.errors")


class AppError(Exception):
    """Base application exception."""
    status_code = 500
    error_type = "InternalServerError"

    def __init__(self, message: str = "An unexpected error occurred.", status_code: int = None, details=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.details = details


class BadRequestError(AppError):
    status_code = 400
    error_type = "BadRequest"


class AuthenticationError(AppError):
    status_code = 401
    error_type = "AuthenticationRequired"


class AuthorizationError(AppError):
    status_code = 403
    error_type = "Forbidden"


class NotFoundError(AppError):
    status_code = 404
    error_type = "NotFound"


class ConflictError(AppError):
    status_code = 409
    error_type = "Conflict"


class ValidationError(AppError):
    status_code = 422
    error_type = "ValidationError"


class RateLimitExceededError(AppError):
    status_code = 429
    error_type = "TooManyRequests"


def wants_json_response() -> bool:
    """
    Determines whether the client expects a JSON error response based on
    URL prefix (/api/*), request Content-Type, or Accept header preferences.
    """
    if request.path.startswith("/api/"):
        return True
    if request.is_json:
        return True
    best = request.accept_mimetypes.best_match(["application/json", "text/html"])
    return best == "application/json" and request.accept_mimetypes[best] > request.accept_mimetypes.get("text/html", 0)


ERROR_METADATA = {
    400: {
        "type": "BadRequest",
        "title": "400 - Bad Request",
        "message": "The server could not understand the request due to malformed syntax or invalid parameters."
    },
    401: {
        "type": "AuthenticationRequired",
        "title": "401 - Unauthorized Access",
        "message": "Authentication is required to access this protected system resource."
    },
    403: {
        "type": "Forbidden",
        "title": "403 - Access Forbidden",
        "message": "You do not have administrative or analyst permissions to perform this operation."
    },
    404: {
        "type": "NotFound",
        "title": "404 - Resource Not Found",
        "message": "The requested endpoint or record could not be found on the server."
    },
    405: {
        "type": "MethodNotAllowed",
        "title": "405 - Method Not Allowed",
        "message": "The HTTP method used is not supported for this requested endpoint."
    },
    409: {
        "type": "Conflict",
        "title": "409 - Conflict",
        "message": "The request could not be completed due to a conflict with the current state of the target resource."
    },
    422: {
        "type": "UnprocessableEntity",
        "title": "422 - Validation Failed",
        "message": "The request was well-formed but contained semantic errors or failed domain validation constraints."
    },
    429: {
        "type": "TooManyRequests",
        "title": "429 - Rate Limit Exceeded",
        "message": "Too many requests have been submitted in a given amount of time. Please retry after a cooldown period."
    },
    500: {
        "type": "InternalServerError",
        "title": "500 - Server Error",
        "message": "An internal server error occurred while processing the transaction. The incident has been recorded."
    }
}


def create_error_response(status_code: int, error_type: str = None, message: str = None, details=None):
    """
    Generates consistent HTTP responses with proper JSON formatting for APIs
    and styled Jinja2 HTML templates for browser clients.
    """
    meta = ERROR_METADATA.get(status_code, {
        "type": "Error",
        "title": f"{status_code} - Error",
        "message": "An error occurred."
    })

    err_type = error_type or meta["type"]
    err_message = message or meta["message"]
    err_title = meta.get("title", f"{status_code} Error")

    if wants_json_response():
        payload = {
            "success": False,
            "status": "error",
            "error": {
                "code": status_code,
                "type": err_type,
                "message": err_message
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if details:
            payload["error"]["details"] = details
        return jsonify(payload), status_code

    return render_template(
        "errors/error.html",
        status_code=status_code,
        error_type=err_type,
        error_title=err_title,
        error_message=err_message
    ), status_code


def register_error_handlers(app: Flask) -> None:
    """
    Registers comprehensive HTTP error handlers and custom application exception handlers on the Flask application factory.
    """
    for code in [400, 401, 403, 404, 405, 409, 422, 429, 500]:
        def make_handler(c):
            def handler(error):
                msg = None
                if isinstance(error, HTTPException):
                    msg = error.description
                if c >= 500:
                    logger.error("HTTP %d error on %s: %s", c, request.path, error, exc_info=True)
                else:
                    logger.warning("HTTP %d on %s: %s", c, request.path, error)
                return create_error_response(c, message=msg)
            return handler

        app.register_error_handler(code, make_handler(code))

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        logger.warning("Application error (%s, %d) on %s: %s", error.error_type, error.status_code, request.path, error.message)
        return create_error_response(
            status_code=error.status_code,
            error_type=error.error_type,
            message=error.message,
            details=error.details
        )

    @app.errorhandler(Exception)
    def handle_uncaught_exception(error: Exception):
        # Allow HTTPExceptions to bubble to their status handlers
        if isinstance(error, HTTPException):
            return create_error_response(error.code, message=error.description)

        logger.critical("Uncaught exception on %s: %s", request.path, error, exc_info=True)
        return create_error_response(
            status_code=500,
            error_type="InternalServerError",
            message="An internal server error occurred while processing the request."
        )
