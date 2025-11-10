from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .services import email
from .routers import csv as csv_router

# Create the FastAPI app. Disable automatic docs UI (user requested no interactive UI).
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
