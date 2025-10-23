"""Job error handling for XSArena."""

import asyncio
import logging

import aiohttp

logger = logging.getLogger(__name__)


def map_exception_to_error_code(exception: Exception) -> str:
    """Map exceptions to standardized error codes."""

    # Check for specific HTTP status codes if it's a response error
    if isinstance(exception, aiohttp.ClientResponseError):
        status = getattr(exception, "status", None)
        status_error_map = {
            401: "AUTH_ERROR",
            403: "FORBIDDEN_ERROR",
            429: "RATE_LIMIT_ERROR",
        }
        if status in status_error_map:
            return status_error_map[status]
        elif 500 <= status < 600:
            return "SERVER_ERROR"
        else:
            return "HTTP_ERROR"

    # Map specific exception types to error codes
    exception_type = type(exception).__name__
    error_map = {
        # aiohttp related errors
        "ClientError": "NETWORK_ERROR",
        "ClientConnectorError": "CONNECTION_ERROR",
        "ClientOSError": "CONNECTION_ERROR",
        "ServerTimeoutError": "TIMEOUT_ERROR",
        "ClientPayloadError": "PAYLOAD_ERROR",
        "ServerConnectionError": "CONNECTION_ERROR",
        "ServerDisconnectedError": "CONNECTION_ERROR",
        # asyncio related errors
        "CancelledError": "CANCELLED_ERROR",
    }

    # Direct mapping
    error_code = error_map.get(exception_type)
    if error_code:
        return error_code

    # Check if it's an asyncio timeout error specifically
    if isinstance(exception, asyncio.TimeoutError):
        return "TIMEOUT_ERROR"

    # Check if it's an aiohttp error by module
    if hasattr(exception, "__class__") and hasattr(exception.__class__, "__module__"):
        module = exception.__class__.__module__
        if module.startswith("aiohttp"):
            return "NETWORK_ERROR"

    # Generic fallback for timeout errors
    if "TimeoutError" in exception_type:
        return "TIMEOUT_ERROR"

    # Return unknown error if no specific mapping found
    return "UNKNOWN_ERROR"


def get_user_friendly_error_message(error_code: str) -> str:
    """Get user-friendly error message for an error code."""
    message_map = {
        "NETWORK_ERROR": "Network connection failed. Please check your internet connection and try again.",
        "CONNECTION_ERROR": "Unable to connect to the server. Please check if the bridge is running.",
        "TIMEOUT_ERROR": "Request timed out. The server took too long to respond. Please try again.",
        "HTTP_ERROR": "An HTTP error occurred. Please check your configuration and try again.",
        "AUTH_ERROR": "Authentication failed. Please check your API key and try again.",
        "FORBIDDEN_ERROR": "Access forbidden. You don't have permission to perform this action.",
        "RATE_LIMIT_ERROR": "Rate limit exceeded. Please wait before making more requests.",
        "SERVER_ERROR": "Server error occurred. The remote service had an internal problem.",
        "PAYLOAD_ERROR": "Data payload error. There was an issue with the request data.",
        "CANCELLED_ERROR": "Request was cancelled.",
        "UNKNOWN_ERROR": "An unknown error occurred. Please check logs for more details.",
    }
    return message_map.get(error_code, "An unknown error occurred")
