from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import example
from .services import email

app = FastAPI()

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

app.include_router(example.router)
app.include_router(email.router, prefix="/emails", tags=["emails"])