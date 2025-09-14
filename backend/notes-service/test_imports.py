#!/usr/bin/env python3
"""Quick test script to verify imports work correctly."""

import sys

# Add the notes-service directory to Python path
sys.path.insert(0, "/app")

try:
    print("Testing import of main...")
    import main

    print("✅ main imported successfully")

    print("Testing import of router_tags...")
    from application.rest.routers.router_tags import router

    print("✅ router_tags imported successfully")

    print("Testing import of domain entities...")
    from domain.entities.tag import TagEntity

    print("✅ TagEntity imported successfully")

    print("Testing import of infrastructure models...")
    from infrastructure.models.tag_orm import TagORM

    print("✅ TagORM imported successfully")

    print("Testing import of utils...")
    from utils.dependencies import get_db

    print("✅ get_db imported successfully")

    print("\n🎉 All imports working correctly!")

except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Other error: {e}")
    sys.exit(1)
