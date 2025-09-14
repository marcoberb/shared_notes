from application.rest.schemas.output.common_output import ErrorResponse, HealthResponse
from fastapi import APIRouter, status

router = APIRouter()


@router.get(
    path="/health",
    description="Health check endpoint for service monitoring and availability.",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": HealthResponse,
            "description": "Service is healthy and operational.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error - service unavailable.",
            "content": {
                "application/json": {
                    "example": {"detail": "Service temporarily unavailable."}
                }
            },
        },
    },
)
async def health_check() -> HealthResponse:
    """Health check endpoint for service monitoring.

    Returns:
        HealthResponse: Service status information containing status and service name.

    Example:
        >>> response = await health_check()
        >>> print(response)
        HealthResponse(status="healthy", service="notes-service")
    """
    return HealthResponse(status="healthy", service="notes-service")
