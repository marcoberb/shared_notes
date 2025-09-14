"""Common output schemas for API responses.

This module contains shared Pydantic models for common API responses
like error messages and status information.
"""

from pydantic import BaseModel
from typing import Optional, Any


class ErrorResponse(BaseModel):
    """Schema for error responses across all endpoints.
    
    Attributes:
        detail (str): Detailed error message.
        error_code (str, optional): Specific error code for categorization.
        
    Example:
        >>> error_response = ErrorResponse(
        ...     detail="Resource not found",
        ...     error_code="NOT_FOUND"
        ... )
    """
    detail: str
    error_code: Optional[str] = None


class MessageResponse(BaseModel):
    """Schema for simple message responses.
    
    Attributes:
        message (str): Success or informational message.
        data (Any, optional): Additional response data.
        
    Example:
        >>> message_response = MessageResponse(
        ...     message="Operation completed successfully",
        ...     data={"id": "123"}
        ... )
    """
    message: str
    data: Optional[Any] = None


class HealthResponse(BaseModel):
    """Schema for health check responses.
    
    Attributes:
        status (str): Service health status.
        service (str): Service name identifier.
        
    Example:
        >>> health_response = HealthResponse(
        ...     status="healthy",
        ...     service="notes-service"
        ... )
    """
    status: str
    service: str
