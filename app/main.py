import os
from urllib.parse import urlparse
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .services import email
from .routers import csv as csv_router

# Create the FastAPI app. Disable automatic docs UI (user requested no interactive UI).
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# Build allowed CORS origins
# Always allow localhost for local development
origins = [
    "http://localhost:3000",
    "http://localhost",
    "http://127.0.0.1:3000",
    "http://127.0.0.1",
    "https://localhost:3000",
    "https://localhost",
    "https://127.0.0.1:3000",
    "https://127.0.0.1",
]

# Optionally allow the deployed frontend origin via env var FRONTEND_BASE_URL
_frontend_base = os.getenv("FRONTEND_BASE_URL")
if _frontend_base:
    try:
        parsed = urlparse(_frontend_base)
        if parsed.scheme and parsed.netloc:
            # Only scheme://host[:port] is relevant for CORS origin
            origin = f"{parsed.scheme}://{parsed.netloc}"
            if origin not in origins:
                origins.append(origin)
    except Exception:
        # ignore malformed env var
        pass

# Also support comma-separated FRONTEND_ALLOWED_ORIGINS for flexibility
_extra_origins = os.getenv("FRONTEND_ALLOWED_ORIGINS")
if _extra_origins:
    for item in _extra_origins.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            p = urlparse(item)
            origin = f"{p.scheme}://{p.netloc}" if p.scheme and p.netloc else item
            if origin not in origins:
                origins.append(origin)
        except Exception:
            if item not in origins:
                origins.append(item)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # Keep a permissive regex for localhost; remote origins should be explicitly added via env vars above
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include CSV router and the example router
app.include_router(csv_router.router)
app.include_router(email.router, prefix="/emails", tags=["emails"])


@app.on_event("startup")
async def app_startup():
    # call csv module startup to initialize optional Redis client
    try:
        await csv_router.startup_event()
    except Exception:
        # if startup fails, let the app continue running (startup logging handled in module)
        pass


@app.on_event("shutdown")
async def app_shutdown():
    try:
        await csv_router.shutdown_event()
    except Exception:
        pass
