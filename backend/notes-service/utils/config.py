"""Configuration management for the Notes Service.

This module centralizes all configuration settings including database URLs,
Keycloak settings, and other environment-based configuration.

Architecture:
    Configuration is separated from dependencies to follow separation of concerns.
    All environment variables and configuration logic is centralized here.
"""

import os

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres123@localhost:5432/sharednotes"
)

# Keycloak configuration for user management
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "sharednotes")
KEYCLOAK_ADMIN_CLIENT_ID = os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", "admin-cli")
KEYCLOAK_ADMIN_USERNAME = os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin")
KEYCLOAK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
