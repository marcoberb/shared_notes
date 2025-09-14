"""Keycloak integration utilities for user management.

This module provides functions to interact with Keycloak for user lookup
and management operations, including fetching user details by ID or email.

Functions:
    - get_user_email_by_id: Fetch user email from Keycloak by user ID
    - get_user_id_by_email: Find user ID in Keycloak by email address

Architecture:
    Keycloak integration is separated from other dependencies to follow
    single responsibility principle and make testing easier.
"""

import logging
from typing import Optional

import httpx

from .config import (
    KEYCLOAK_ADMIN_CLIENT_ID,
    KEYCLOAK_ADMIN_PASSWORD,
    KEYCLOAK_ADMIN_USERNAME,
    KEYCLOAK_REALM,
    KEYCLOAK_URL,
)

logger = logging.getLogger(__name__)


async def get_user_email_by_id(user_id: str) -> Optional[str]:
    """Get user email by ID from Keycloak.

    Args:
        user_id (str): Keycloak user UUID.

    Returns:
        str: User email address or None if not found.

    Raises:
        Exception: Logs errors but doesn't raise, returns None on failure.

    Example:
        >>> email = await get_user_email_by_id("keycloak-uuid")
        >>> print(email)
        "user@example.com"
    """
    try:
        # Get admin token
        admin_token_url = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
        admin_token_data = {
            "grant_type": "password",
            "client_id": KEYCLOAK_ADMIN_CLIENT_ID,
            "username": KEYCLOAK_ADMIN_USERNAME,
            "password": KEYCLOAK_ADMIN_PASSWORD,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(admin_token_url, data=admin_token_data)
            if response.status_code == 200:
                admin_token = response.json()["access_token"]
            else:
                logger.error(f"Failed to get admin token: {response.status_code}")
                return None

            # Get user data
            user_url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}"
            headers = {"Authorization": f"Bearer {admin_token}"}

            response = await client.get(user_url, headers=headers)
            if response.status_code == 200:
                user_data = response.json()
                return user_data.get("email")
            else:
                logger.error(f"Failed to get user data: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Error getting user email for ID {user_id}: {e}")
        return None


async def get_user_id_by_email(email: str) -> Optional[str]:
    """Get user ID by email from Keycloak.

    Args:
        email (str): User email address to search for.

    Returns:
        str: Keycloak user UUID or None if not found.

    Raises:
        Exception: Logs errors but doesn't raise, returns None on failure.

    Example:
        >>> user_id = await get_user_id_by_email("user@example.com")
        >>> print(user_id)
        "keycloak-user-uuid"
    """
    try:
        # Get admin token first
        admin_token_url = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
        admin_token_data = {
            "grant_type": "password",
            "client_id": KEYCLOAK_ADMIN_CLIENT_ID,
            "username": KEYCLOAK_ADMIN_USERNAME,
            "password": KEYCLOAK_ADMIN_PASSWORD,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(admin_token_url, data=admin_token_data)
            if response.status_code == 200:
                admin_token = response.json()["access_token"]
            else:
                logger.error(f"Failed to get admin token: {response.status_code}")
                return None

            # Search user by email
            search_url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users"
            headers = {"Authorization": f"Bearer {admin_token}"}
            params = {"email": email, "exact": "true"}

            response = await client.get(search_url, headers=headers, params=params)
            if response.status_code == 200:
                users = response.json()
                if users and len(users) > 0:
                    return users[0]["id"]
                else:
                    logger.error(f"User not found for email: {email}")
                    return None
            else:
                logger.error(f"Failed to search user by email: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Error getting user ID for email {email}: {e}")
        return None
