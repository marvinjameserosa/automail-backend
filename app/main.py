from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import example
from .routers import csv as csv_router

# Create the FastAPI app. Disable automatic docs UI (user requested no interactive UI).
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

origins = [
    "http://localhost:3000",
    "http://localhost",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include CSV router and the example router
app.include_router(csv_router.router)
app.include_router(example.router)


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