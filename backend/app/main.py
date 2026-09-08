from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import upload, query, chat
from app.middleware import RateLimitMiddleware

app = FastAPI(title="Document Q&A Bot", version="1.0.0")

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(chat.router, prefix="/api")  # Streaming endpoint for AI SDK


@app.get("/")
async def root():
    return {"message": "Document Q&A Bot API"}
