import logging
import os

import httpx
import jwt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SharedNotes API Gateway",
    description="API Gateway for SharedNotes microservices with Keycloak",
    version="1.0.0",
    redirect_slashes=False,
)

# No CORS needed - all requests come through frontend nginx proxy
# Add minimal CORS for preflight requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Only accessible through nginx proxy anyway
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "sharednotes")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "sharednotes-api")
KEYCLOAK_CLIENT_SECRET = os.getenv(
    "KEYCLOAK_CLIENT_SECRET", "sharednotes-api-secret-key-2024"
)
NOTES_SERVICE_URL = os.getenv("NOTES_SERVICE_URL", "http://localhost:8002")
SHARE_SERVICE_URL = os.getenv("SHARE_SERVICE_URL", "http://localhost:8004")

# Keycloak configuration
KEYCLOAK_REALM_URL = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
KEYCLOAK_JWKS_URL = f"{KEYCLOAK_REALM_URL}/protocol/openid-connect/certs"
KEYCLOAK_TOKEN_URL = f"{KEYCLOAK_REALM_URL}/protocol/openid-connect/token"


# HTTP client
http_client = httpx.AsyncClient(timeout=30.0)

# JWT verification setup
security = HTTPBearer()


# Authentication helpers
async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Verify JWT token with Keycloak"""
    try:
        # Get Keycloak public key and verify token
        jwks_client = PyJWKClient(KEYCLOAK_JWKS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(credentials.credentials)

        payload = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256"],
            options={
                "verify_aud": False,
                "verify_iss": False,
            },  # Skip audience and issuer validation for now
        )

        return payload
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(payload: dict = Depends(verify_token)) -> dict:
    """Extract user info from verified token"""
    return {
        "id": payload.get("sub"),
        "username": payload.get("preferred_username"),
        "email": payload.get("email"),
        "name": payload.get("name"),
        "roles": payload.get("realm_access", {}).get("roles", []),
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "api-gateway"}


# Proxy endpoints with authentication
async def proxy_request(
    request: Request,
    target_url: str,
    backend_path: str,
    user: dict = Depends(get_current_user),
):
    """Proxy request to microservice with user context and path mapping"""
    try:
        # Prepare headers
        headers = dict(request.headers)
        headers["X-User-ID"] = user["id"]
        headers["X-User-Username"] = user["username"]
        headers["X-User-Email"] = user.get("email", "")

        # Remove host header to avoid conflicts
        headers.pop("host", None)

        # Get request body
        body = await request.body()

        # Make request to target service with mapped backend path
        response = await http_client.request(
            method=request.method,
            url=f"{target_url}{backend_path}",
            params=request.query_params,
            headers=headers,
            content=body,
        )

        # Get response content safely
        try:
            if response.headers.get("content-type", "").startswith("application/json"):
                content = response.json()
            else:
                content = response.text
        except Exception:
            # Fallback to raw content if parsing fails
            content = response.content.decode("utf-8", errors="ignore")

        # Create clean headers without problematic ones
        response_headers = {}
        for key, value in response.headers.items():
            # Skip headers that might cause issues
            if key.lower() not in [
                "content-length",
                "content-encoding",
                "transfer-encoding",
            ]:
                response_headers[key] = value

        return JSONResponse(
            status_code=response.status_code, content=content, headers=response_headers
        )

    except Exception as e:
        logger.error(f"Proxy error: {e}")
        raise HTTPException(status_code=500, detail="Service unavailable")


@app.api_route("/api/notes", methods=["GET", "POST", "PUT", "DELETE"])
@app.api_route("/api/notes/", methods=["GET", "POST", "PUT", "DELETE"])
async def notes_proxy_root(request: Request, user: dict = Depends(get_current_user)):
    return await proxy_request(request, NOTES_SERVICE_URL, "/notes", user)


@app.api_route("/api/notes/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def notes_proxy(
    request: Request, path: str, user: dict = Depends(get_current_user)
):
    return await proxy_request(request, NOTES_SERVICE_URL, f"/notes/{path}", user)


@app.api_route("/api/search", methods=["GET"])
async def search_proxy_root(request: Request, user: dict = Depends(get_current_user)):
    return await proxy_request(request, NOTES_SERVICE_URL, "/search", user)


@app.api_route("/api/search/{path:path}", methods=["GET"])
async def search_proxy(
    request: Request, path: str, user: dict = Depends(get_current_user)
):
    return await proxy_request(request, NOTES_SERVICE_URL, f"/search/{path}", user)


@app.api_route("/api/tags", methods=["GET"])
@app.api_route("/api/tags/", methods=["GET"])
async def tags_proxy_root(request: Request, user: dict = Depends(get_current_user)):
    return await proxy_request(request, NOTES_SERVICE_URL, "/tags", user)


@app.api_route("/api/tags/{path:path}", methods=["GET"])
async def tags_proxy(
    request: Request, path: str, user: dict = Depends(get_current_user)
):
    return await proxy_request(request, NOTES_SERVICE_URL, f"/tags/{path}", user)


@app.api_route("/api/share", methods=["GET", "POST", "PUT", "DELETE"])
@app.api_route("/api/share/", methods=["GET", "POST", "PUT", "DELETE"])
async def share_proxy_root(request: Request, user: dict = Depends(get_current_user)):
    return await proxy_request(request, SHARE_SERVICE_URL, "/share/", user)


@app.api_route("/api/share/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def share_proxy(
    request: Request, path: str, user: dict = Depends(get_current_user)
):
    return await proxy_request(request, SHARE_SERVICE_URL, f"/share/{path}", user)
