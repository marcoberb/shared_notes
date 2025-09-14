from fastapi import FastAPI

from application.rest.routers.router_health import router as health_router
from application.rest.routers.router_tags import router as tags_router
from application.rest.routers.router_search import router as search_router
from application.rest.routers.router_notes import router as notes_router

app = FastAPI(
    title="SharedNotes Notes Service",
    description="Notes management service for SharedNotes",
    version="1.0.0"
)

app.include_router(health_router)
app.include_router(tags_router)
app.include_router(search_router)
app.include_router(notes_router)
