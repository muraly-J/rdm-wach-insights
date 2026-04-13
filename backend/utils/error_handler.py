"""
utils/error_handler.py
──────────────────────
Centralized error handling for WACH Insight.

All API endpoints should use these utilities to:
1. Catch errors and return generic messages to users
2. Log detailed error information server-side only

Example usage in FastAPI routes:
    from backend.utils.error_handler import handle_error

    try:
        result = some_operation()
    except Exception as e:
        return handle_error(e, "Failed to process query")
"""

import traceback

from core.logger import get_logger
from fastapi import HTTPException

logger = get_logger(__name__)


def log_error(error: Exception, context: str = "") -> None:
    """
    Log a detailed error message server-side only.

    Args:
        error: The exception that occurred
        context: Description of what operation was being performed
    """
    logger.error(
        f"Error during {context}: {str(error)}\n"
        f"Traceback:\n{traceback.format_exc()}"
    )


def create_generic_error_message(detail: str = "") -> dict:
    """
    Create a generic error message safe for user consumption.

    Args:
        detail: Optional specific detail to include (still sanitized)

    Returns:
        Dictionary with error message suitable for user
    """
    if detail:
        return {"error": f"We encountered an issue processing your request: {detail}"}
    return {
        "error": "We encountered an unexpected error processing your request. "
                "Please try again in a moment."
    }


def create_error_response(
    status_code: int,
    user_message: str = "",
    log_context: str = "",
    error: Exception | None = None,
) -> HTTPException:
    """
    Create an HTTPException with generic user message and detailed server logging.

    Args:
        status_code: HTTP status code for the response
        user_message: Custom message for user (if empty, generic message used)
        log_context: Description of what operation was being performed (for logging)
        error: The exception that occurred (if available)

    Returns:
        HTTPException with generic message and logged details
    """
    # Log the detailed error
    if error:
        log_context = f"{log_context}: {str(error)}"

    # Create user-facing message
    if not user_message:
        user_message = "We encountered an unexpected error processing your request. Please try again in a moment."

    # Log with traceback if we have an error object
    if error:
        logger.error(
            f"HTTP {status_code} Error during {log_context}: {str(error)}\n"
            f"Traceback:\n{traceback.format_exc()}"
        )
    else:
        logger.warning(f"HTTP {status_code} Error: {log_context}")

    return HTTPException(status_code=status_code, detail={"error": user_message})


def handle_query_error(error: Exception, session_id: str | None = None) -> HTTPException:
    """
    Handle errors that occur during query processing.
    Returns a 502 error with generic user message.

    Args:
        error: The exception that occurred
        session_id: Optional session ID for logging

    Returns:
        HTTPException for the response
    """
    context = "query processing"
    if session_id:
        context += f" (session: {session_id})"

    return create_error_response(
        status_code=502,
        user_message="Could not retrieve data. Please try again in a moment.",
        log_context=context,
        error=error
    )


def handle_forecast_error(error: Exception, device_id: str | None = None) -> HTTPException:
    """
    Handle errors that occur during forecast processing.
    Returns a 500 error with generic user message.

    Args:
        error: The exception that occurred
        device_id: Optional device ID for logging

    Returns:
        HTTPException for the response
    """
    context = "forecast generation"
    if device_id:
        context += f" (device: {device_id})"

    return create_error_response(
        status_code=500,
        user_message="Could not generate forecast. Please try again later.",
        log_context=context,
        error=error
    )


def handle_llm_error(error: Exception) -> tuple[None, str]:
    """
    Handle errors that occur during LLM processing.
    Returns (None, user_message) tuple for translator compatibility.

    Args:
        error: The exception that occurred

    Returns:
        Tuple of (None, user_message)
    """
    logger.error(
        f"LLM processing error: {str(error)}\n"
        f"Traceback:\n{traceback.format_exc()}"
    )

    return None, "Could not reach the server. Please try again in a moment."


def handle_validation_error(error: Exception) -> HTTPException:
    """
    Handle validation errors.
    Returns a 422 error with generic user message.

    Args:
        error: The exception that occurred

    Returns:
        HTTPException for the response
    """
    return create_error_response(
        status_code=422,
        user_message="Invalid request. Please check your input and try again.",
        log_context="input validation",
        error=error
    )
