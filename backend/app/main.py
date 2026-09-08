from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import upload, query, chat, chats, settings, tools
from app.middleware import RateLimitMiddleware
from app.store.bootstrap import import_legacy_env_keys
from app.store.chat_store import init_db as init_chat_db
from app.store.settings_store import init_db

app = FastAPI(title="Document Q&A Bot", version="1.1.0")

init_db()
init_chat_db()  # chat history tables, same local app.db

# One-time upgrade path: copy any key still sitting in .env into the encrypted
# local store, then never read the environment again. See store/bootstrap.py.
_imported = import_legacy_env_keys()
if _imported:
    print(
        "Imported API keys from .env into backend/data/app.db for: "
        + ", ".join(_imported)
        + ". You can delete backend/.env now — provider settings live in the app."
    )

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # The chat endpoints return the conversation id of a turn on this header.
    expose_headers=["X-Chat-Id"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(chat.router, prefix="/api")  # Streaming endpoint for AI SDK
app.include_router(settings.router, prefix="/api")  # AI provider configuration
app.include_router(tools.router, prefix="/api")  # Tool Calling tile
app.include_router(chats.router, prefix="/api")  # Stored conversations


@app.get("/")
async def root():
    return {"message": "Document Q&A Bot API"}
