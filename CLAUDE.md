# Document Q&A Bot - Development Guide

## Project Overview
RAG-based document Q&A system: Python FastAPI + FAISS + React frontend, with a
pluggable chat-provider layer (OpenAI / Anthropic / Gemini / Azure OpenAI).
Supports PDF/TXT/DOCX with hallucination prevention and 3-layer prompt injection defense.

**Where the product is going:** a single app with three tiles — **RAG**,
**Tool Calling**, **Guardrails** — that share one chat shell and differ only in
the backend pipeline behind them. RAG ships today; the other two are described
under [Three-Tile Architecture](#three-tile-architecture-target-state).

## Directory Structure (Key Files Only)
```
app.sh                               # start/stop/restart/status for the whole stack (single-instance lock)
backend/
├── app/
│   ├── config.py                    # ALL configuration (CRITICAL - tuned values)
│   ├── crypto.py                    # Encrypt/decrypt stored API keys + mask() for display
│   ├── sanitizer.py                 # Injection defense layers 1 & 2
│   ├── middleware.py                # Rate limiting
│   ├── routers/
│   │   ├── upload.py                # POST /upload, GET /documents, DELETE /documents/{name}
│   │   ├── query.py                 # POST /query (legacy, non-streaming)
│   │   ├── chat.py                  # POST /chat - SSE stream in AI SDK v4 format
│   │   └── settings.py              # Provider config CRUD + activate + live key test
│   ├── services/
│   │   ├── document_processor.py    # Parse files + chunk text
│   │   ├── embedding_service.py     # OpenAI embedding calls (batched)
│   │   ├── context_builder.py       # Token-budgeted context assembly + count_tokens()
│   │   ├── qa_service.py            # QA orchestration, non-streaming
│   │   ├── qa_service_streaming.py  # QA orchestration, streaming (MOST COMPLEX)
│   │   └── providers/
│   │       ├── __init__.py          # PROVIDER_CATALOG + registry/resolution logic
│   │       ├── base.py              # ChatProvider ABC, ProviderError, usage_dict()
│   │       ├── openai_provider.py   # OpenAI + Azure OpenAI
│   │       ├── anthropic_provider.py
│   │       └── gemini_provider.py
│   └── store/
│       ├── vector_store.py          # FAISS index management
│       └── settings_store.py        # SQLite: provider settings + active provider
├── data/                            # app.db (encrypted keys) + .secret_key  [gitignored]
├── crypto.py                        # Fernet encryption for stored API keys
│   ├── services/providers/          # Multi-provider chat connectors
│   │   ├── base.py                  # ChatProvider interface
│   │   ├── openai_provider.py       # OpenAI + Azure OpenAI
│   │   ├── anthropic_provider.py    # Claude
│   │   └── gemini_provider.py       # Google Gemini
│   ├── store/settings_store.py      # SQLite: provider config + encrypted keys
├── data/                            # Local app DB (runtime, gitignored)
│   ├── app.db
│   └── .secret_key                  # Master key, 0600
├── uploads/                         # Uploaded files (runtime)
├── faiss_index/                     # index.faiss + metadata.json (runtime)
└── .env                             # Optional API keys (fallback when DB has none)

frontend/src/
├── App.jsx                          # Tile router: null | 'rag' | 'tools' | 'guardrails'
├── modes.jsx                        # The three tiles' metadata (see Three-Tile Architecture)
├── api.js
├── pages/ (LandingPage, RagMode, PlaceholderMode)
├── hooks/useDocumentChat.js         # Wraps AI SDK useChat, endpoint is a parameter
└── components/ (ChatShell, SettingsPanel, FileUpload, ChatWindow, MessageInput)
```

## Critical Configuration (`backend/app/config.py`)
**These values were carefully tuned through user testing - don't change without good reason:**

```python
# Tuned values (modification history below)
SIMILARITY_THRESHOLD = 1.8   # L2 distance cutoff (was 1.2 → too strict → raised to 1.8)
TEMPERATURE = 0.3            # LLM temperature (was 0.1 → too rigid → raised to 0.3)
TOP_K_RESULTS = 8            # Chunks retrieved (was 4 → 5 → 8 for better context)

# Stable values
CHUNK_SIZE = 1000            # Text chunk size
CHUNK_OVERLAP = 200          # Overlap between chunks
MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_QUESTION_LENGTH = 1000   # Input length limit
RATE_LIMIT_REQUESTS = 20     # Per 60 seconds per IP
EMBEDDING_MODEL = "text-embedding-ada-002"  # 1536 dimensions
EMBEDDING_BATCH_SIZE = 100   # OpenAI caps inputs per embeddings request
LLM_MODEL = "gpt-3.5-turbo"  # Default OpenAI chat model
DEFAULT_CHAT_PROVIDER = "openai"
MAX_ANSWER_TOKENS = 1500
MAX_CONTEXT_TOKENS = 12000   # Leaves room for system prompt + answer in a 16k window

# Paths
UPLOAD_DIR, FAISS_INDEX_DIR, DATA_DIR   # created on import
DATABASE_FILE = data/app.db             # provider settings + encrypted keys
SECRET_KEY_FILE = data/.secret_key      # generated on first run if APP_SECRET_KEY unset
```

## RAG Pipeline Flow
```
UPLOAD: File → Parse → Chunk (1000 chars, 200 overlap) → Embed (ada-002) → FAISS IndexFlatL2
QUERY:  Question → Sanitize → Inject detection → Embed → FAISS search → Filter (≤1.8 distance)
        → build_context() token budget → active provider → stream
        └─> If summary query detected: retrieve ALL chunks instead of top-k
```

## Provider Layer (Multi-Model Support)

Chat runs through `ChatProvider` implementations; **embeddings always stay on OpenAI**
because the FAISS index holds 1536-dim ada-002 vectors and `SIMILARITY_THRESHOLD=1.8`
is calibrated to that model's distances. Switching the embedding model invalidates
the entire index.

- `PROVIDER_CATALOG` (providers/__init__.py) describes each provider's required
  fields and suggested models. `model` is always free text so a newer model works
  without a code change.
- Key resolution order: **SQLite (encrypted) → environment variable**. Keys are
  never returned to the client, only a mask like `sk-...b3f9`.
- `base.py` contract: `complete(system, user)` and `stream(system, user)`, both
  receiving the *already built* system prompt and XML-delimited user prompt. A
  provider must never alter RAG behaviour.
- Provider calls are blocking, so the streaming path wraps them in
  `run_in_threadpool` / `iterate_in_threadpool` to keep the event loop free.

## Key Design Decisions (Critical Context)

### 1. SIMILARITY_THRESHOLD = 1.8 (NOT 1.2)
**Why:** Ada-002 produces normalized embeddings with L2 distance 0-2. Initially 1.2 was too strict - user reported bot refusing ALL questions despite relevant context. Raised to 1.8 after user testing with screenshots.

### 2. System Prompt Evolution (3 Versions)
- **V1 (Too Loose):** "Answer based on context" → Hallucinated freely
- **V2 (Too Strict):** "ONLY use explicit info, NEVER add knowledge" → Refused to answer "what weighed around 83kg?" when context said "Sputnik: 83.6kg"
- **V3 (Balanced - CURRENT):** "Synthesize across passages. Don't invent facts. NEVER guess numbers." → Allows "83.6kg ≈ around 83kg" but prohibits invented statistics

**Location:** `qa_service.py` and `qa_service_streaming.py` — the prompt is duplicated in both; change them together.

### 3. Summary Query Detection
Specific questions ("When was Sputnik launched?") use top-k retrieval.
Broad queries ("summarise", "list all", "how many chapters") send ALL chunks.
**Why:** Without this, "list all launches" only retrieved 8 chunks similar to "launches", missing most content.

**Implementation:** `SUMMARY_PATTERNS` regex + `_is_summary_query()` in both QA services.

### 4. Token-Budgeted Context (context_builder.py)
The summary path can pull every chunk of a document, which easily overflows the
model's window. `build_context()` fills up to `MAX_CONTEXT_TOKENS` and returns
**both** the context string and the chunks that actually fit, so sources cite only
passages the model really saw.

### 5. 3-Layer Prompt Injection Defense
**Layer 1 (sanitizer.py):** Strip control chars, enforce MAX_QUESTION_LENGTH
**Layer 2 (sanitizer.py):** Regex blocks known patterns ("ignore instructions", "reveal prompt", etc.)
**Layer 3 (qa_service*.py):** System prompt hardening + XML tags (`<document_context>`, `<user_question>`)

Active on **both** `/api/query` and `/api/chat`. Layer 2 blocks before any LLM call is made.

**Evidence:** User tested with defenses disabled (prompt leakage occurred) vs enabled (all attacks blocked).

### 6. FAISS Index Deletion
FAISS IndexFlatL2 doesn't support deletion → rebuild entire index without deleted doc's vectors.
**Performance:** O(n) rebuild acceptable because deletions are infrequent.

### 7. API Key Storage
Keys live encrypted in `backend/data/app.db` (`crypto.py`), unlocked by
`APP_SECRET_KEY` or a generated `data/.secret_key`. `data/` is gitignored.
The settings API returns `masked_key` only — never the plaintext key.

## Three-Tile Architecture (Target State)

One landing page, three tiles, **one shared chat shell**. Do not build three apps —
the tiles differ only in which pipeline the chat endpoint runs.

| Tile | Pipeline | Endpoint |
|------|----------|----------|
| **RAG** | question → retrieve → LLM → text | `/api/chat` (exists) |
| **Tool Calling** | question → LLM picks tool → execute → feed result back → LLM → readable text | `/api/tools/chat` (new) |
| **Guardrails** | question → sanitize → injection check → RAG → output check → text + verdict | `/api/guardrails/chat` (new) |

### Frontend layout (BUILT)
```
frontend/src/
├── App.jsx                  # mode state: null | 'rag' | 'tools' | 'guardrails'
├── modes.jsx                # MODES registry: title, tagline, steps, endpoint, icon, accent classes
├── pages/
│   ├── LandingPage.jsx      # the three tiles
│   ├── RagMode.jsx          # sidebar: FileUpload + session stats + document list
│   └── PlaceholderMode.jsx  # preview for a tile with no backend yet (composer disabled)
├── components/
│   ├── ChatShell.jsx        # shared layout: <aside>{sidebar}</aside> + ChatWindow + MessageInput
│   ├── SettingsPanel.jsx    # provider modal, mounted once in App.jsx (global to all tiles)
│   └── ToolCallCard.jsx     # (planned) renders one tool invocation: name, args, result
└── hooks/useDocumentChat.js # useDocumentChat({ api }) — defaults to '/api/chat'
```
A `mode` state variable plus a back button is enough — no router needed for a POC.

`modes.jsx` is the single source of truth for the tiles. Accent colours are
written out as **complete class strings** (`bg-violet-600`, not
``bg-${accent}-600``) because Tailwind cannot see dynamically built names; the
violet tokens used by the Tool Calling tile are defined in `index.css` `@theme`.

Replacing `PlaceholderMode` with a real tile means: add the page, point it at
the mode's `endpoint`, and switch on `mode.id` in `App.jsx`. `ChatShell`,
`ChatWindow` (`emptyTitle` / `emptyText`) and `MessageInput` (`placeholder`)
are already parameterized for it.

### Tool Calling: the two-pass loop
"Tool call first, then readable text" means two LLM passes per turn:

```
Pass 1 — LLM sees question + tool schemas → returns tool_calls, no prose
         e.g. get_weather(city="Chennai")
Backend executes the Python function locally → raw JSON {"temp_c": 31, ...}
Pass 2 — same conversation + tool results appended as tool-role messages
         → LLM streams the readable answer: "It's 31°C and hazy in Chennai."
```
Loop until the model returns text instead of tool calls; **cap at ~4 iterations**
so a confused model cannot spin.

```
backend/app/
├── sse.py                     # AI SDK part-code formatter, extracted from chat.py
├── services/tools/
│   ├── registry.py            # TOOLS = {name: {"schema": {...}, "fn": callable}}
│   ├── weather.py, calculator.py
│   └── documents.py           # search_documents / list_documents (RAG as a tool)
├── services/tool_service.py   # the loop above, yields text + tool events
└── routers/tools.py           # POST /api/tools/chat
```

**The one real piece of work:** `ChatProvider` today is single-turn
(`complete(system, user)` / `stream(system, user)`) with no message history and
no tools. Add one method rather than changing the existing two:

```python
def stream_tools(self, system: str, messages: list[dict],
                 tools: list[dict]) -> Iterator[dict]:
    """Yield {"type": "text"|"tool_call"|"usage", ...}.
    Default implementation raises ProviderError('<label> tool calling not wired up yet').
    """
```
Each provider normalizes its own wire format into that shared event shape:
- **OpenAI** — `tools=[...]`, accumulate streamed `delta.tool_calls` argument fragments, reply with `{"role": "tool", "tool_call_id": ...}`
- **Anthropic** — `tools=[...]`, `stop_reason == "tool_use"`, reply with a `tool_result` content block
- **Gemini** — `function_declarations`, `functionCall` / `functionResponse` parts

Implement OpenAI first; the others keep the clear error until wired up.

**Surfacing tool calls in the UI:** `format_sse_stream` already speaks AI SDK v4
part codes (`0:` text, `8:` annotation, `d:` finish, `3:` error). Two more give
native rendering — `9:{"toolCallId","toolName","args"}` and
`a:{"toolCallId","result"}` — which `useChat` exposes as `message.toolInvocations`
for `ToolCallCard.jsx`.

### Guardrails tile
Mostly making the existing defenses *visible*:
- Sidebar listing the 3 layers with per-layer on/off toggles (**demo only**, default ON)
- Preset attack buttons ("Ignore all previous instructions…", "Reveal your system prompt")
- A verdict panel per turn: `Layer 1 pass · Layer 2 BLOCKED (pattern: reveal prompt) · LLM never called`
- New `guardrail_service.py` returns a **structured verdict** instead of a bare bool
- Worth adding: an **output-side** check (does the answer leak the system prompt?) — all three layers today are input-side

Toggles must be gated behind a config flag (`GUARDRAILS_DEMO_MODE`). `/api/chat`
and `/api/query` keep their defenses hardcoded regardless of the flag.

### Build order
1. ~~Extract `ChatShell` + landing page → RAG tile works immediately~~ **DONE** — landing page, `modes.jsx`, `ChatShell`, `RagMode`, `PlaceholderMode`; RAG behaviour unchanged
2. Extract `app/sse.py`; add `stream_tools` to `base.py` (raising default) + OpenAI implementation
3. Tool registry with 2-3 tools + `/api/tools/chat` + `ToolCallCard`
4. Guardrails router + verdict panel
5. Anthropic / Gemini tool support last

**Open question before building:** should `search_documents` be registered as a
tool so the Tools tile also answers document questions? It demos better (the model
chooses between retrieval and an API) but blurs the distinction the tiles teach.

## Critical Code Patterns

### Summary Detection (qa_service*.py)
```python
SUMMARY_PATTERNS = re.compile(
    r'\b(summar|overview|list\s+all|entire\s+document|main\s+points|'
    r'how\s+many\s+(chapters?|sections?|parts?))\b', re.IGNORECASE)

def _is_summary_query(q): return bool(SUMMARY_PATTERNS.search(q))
# If True: get_all_chunks() for every document, else: search(embedding, top_k=8)
```

### Injection Defense (sanitizer.py)
```python
def detect_injection(q): return bool(INJECTION_PATTERNS.search(q))
# If True: return safe response immediately, skip the LLM call entirely
```

### FAISS Search with Threshold (vector_store.py)
```python
distances, indices = self.index.search(query_vector, top_k)
results = [self.metadata[idx] for dist, idx in zip(distances[0], indices[0])
           if dist <= SIMILARITY_THRESHOLD]  # CRITICAL FILTER
```

### AI SDK v4 Stream Parts (routers/chat.py)
```python
f"0:{json.dumps(text)}\n"        # text chunk
f"8:{json.dumps([data])}\n"      # annotation (sources, provider, usage)
"d:" + json.dumps({"finishReason": "stop", "usage": {...}}) + "\n"
f"3:{json.dumps(msg)}\n"         # error
# A malformed part aborts the stream client-side — validated by @ai-sdk/ui-utils
```

## API Endpoints
- `POST /api/upload` - multipart/form-data → {message, filename, chunks_added}
- `POST /api/query` - {question} → {answer, sources} (legacy, non-streaming)
- `POST /api/chat` - {messages:[{role,content}]} → SSE stream (AI SDK v4 format)
- `GET /api/documents` - → {documents:[{filename, chunks}]}
- `DELETE /api/documents/{filename}` - → {message, filename}
- `GET /api/providers` - → {active, providers:[...]}  (keys masked)
- `PUT /api/providers/{provider}` - update api_key / model / base_url / api_version
- `POST /api/providers/{provider}/activate` - switch the active chat provider
- `POST /api/providers/{provider}/test` - validate credentials with a live call
- `DELETE /api/providers/{provider}` - remove stored settings
- *(planned)* `POST /api/tools/chat`, `POST /api/guardrails/chat`

## Troubleshooting Quick Reference

| Problem | Check |
|---------|-------|
| Bot refuses to answer | 1. SIMILARITY_THRESHOLD=1.8 (not lower)<br>2. System prompt is balanced V3<br>3. Documents uploaded |
| Hallucinated numbers | 1. System prompt has "NEVER guess numbers"<br>2. SUMMARY_PATTERNS includes "how many"<br>3. TEMPERATURE=0.3 |
| Summary queries incomplete | 1. Query matches SUMMARY_PATTERNS<br>2. get_all_chunks() called<br>3. MAX_CONTEXT_TOKENS not truncating |
| Prompt injection works | 1. INJECTION_PATTERNS covers phrase<br>2. detect_injection() called in the router<br>3. XML tags in prompt |
| "Chat provider is not ready" | 1. Key saved via /api/providers or in .env<br>2. Model name set<br>3. Azure also needs base_url + api_version |
| Stream dies mid-answer | Malformed SSE part — every part needs its code prefix and trailing `\n`; `d:` needs a finishReason |
| Answers stop but UI hangs | The `d:` finish frame was never emitted |

## File Modification History (What Changed and Why)

### config.py
- `SIMILARITY_THRESHOLD`: 1.2 → 1.8 (user testing: bot refused all questions)
- `TEMPERATURE`: 0.1 → 0.3 (too rigid → balanced)
- `TOP_K_RESULTS`: 4 → 5 → 8 (insufficient context → adequate)
- Added DATA_DIR / DATABASE_FILE / SECRET_KEY_FILE for provider settings
- Added MAX_CONTEXT_TOKENS, MAX_ANSWER_TOKENS, EMBEDDING_BATCH_SIZE

### qa_service.py / qa_service_streaming.py
- System prompt: V1→V2→V3 (loose→strict→balanced)
- Added SUMMARY_PATTERNS regex for broad query detection
- Added XML tag delimiters for injection defense
- Switched from a direct OpenAI call to `get_active_chat_provider()`
- Context assembly moved to `context_builder.build_context()` (token budget)

### sanitizer.py
- Entire file added after user requested prompt injection defense
- Tested with user: defenses OFF (leaked) vs ON (blocked)

### vector_store.py
- Added remove_document() (user requested deletion)
- Added SIMILARITY_THRESHOLD filtering in search()

### AI SDK Migration
- Frontend: `ai` package, `useDocumentChat` hook, streaming cursor in ChatWindow
- Backend: `qa_service_streaming.py` + `chat.py` SSE endpoint, all 3 defense layers preserved
- `/api/query` kept for backward compatibility

### Multi-Provider Support (Latest)
- Added `services/providers/` (OpenAI, Azure OpenAI, Anthropic, Gemini) behind a `ChatProvider` ABC
- Added `store/settings_store.py` (SQLite) + `crypto.py` (encrypted keys, masked display)
- Added `routers/settings.py` for provider CRUD / activate / live key test
- Embeddings deliberately pinned to OpenAI (index compatibility)
- Added `app.sh` for single-instance start/stop of both services

## When to Modify What

### ✅ Safe to change:
- Frontend styling, UI text, log messages
- Adding a model name to `PROVIDER_CATALOG["…"]["models"]`

### ⚠️ Requires user testing:
- SIMILARITY_THRESHOLD, TEMPERATURE, TOP_K_RESULTS, CHUNK_SIZE/OVERLAP, MAX_CONTEXT_TOKENS
- System prompt wording, SUMMARY_PATTERNS regex

### 🛡️ Requires security review:
- INJECTION_PATTERNS (could miss attacks)
- System prompt security instructions, input sanitization
- Anything touching `crypto.py` or key storage/masking
- The guardrails demo toggles (must never disable defenses on the real endpoints)

### 🚫 NEVER change without user approval:
- Remove prompt injection defenses
- Disable similarity threshold filtering
- Weaken anti-hallucination guidelines
- Expose system prompts or plaintext API keys to the client
- Change EMBEDDING_MODEL (invalidates the FAISS index)

## Quick Reference for AI Assistants

**Bot not answering?** SIMILARITY_THRESHOLD=1.8 → system prompt is V3 → documents uploaded → provider configured.
**Hallucination reported?** SUMMARY_PATTERNS covers the query type → "NEVER guess numbers" present → TEMPERATURE=0.3.
**New feature request?** Check security impact → identify affected files above → test with user before finalizing.
**Security issue?** INJECTION_PATTERNS coverage → detect_injection() called in the router → test defenses off vs on.

**Common pitfalls:**
- Empty results? Check the FAISS index exists and documents are uploaded
- Provider errors? `GET /api/providers` shows which are `configured`; `.env` is only a fallback
- Index corruption? Delete `faiss_index/` and re-upload
- Blocking calls in the async path? Wrap with `run_in_threadpool` — provider SDKs are synchronous

## Dependencies (Key Ones)
- `fastapi`, `uvicorn` - Web framework
- `openai` - Chat + embeddings (ada-002), also Azure OpenAI
- `anthropic`, `google-genai` - Alternative chat providers
- `faiss-cpu` - Vector similarity search (IndexFlatL2)
- `langchain-text-splitters` - RecursiveCharacterTextSplitter for chunking
- `tiktoken` - Token counting for the context budget
- `cryptography` - At-rest encryption for stored API keys
- `PyPDF2`, `python-docx` - File parsing
- React + Vite + Tailwind + Vercel AI SDK v4 (frontend)

## Multi-Provider Chat (Added)

Chat runs on OpenAI, Anthropic, Google Gemini, or Azure OpenAI — selected in the
Settings panel and stored in `backend/data/app.db` (SQLite, gitignored). Keys are
Fernet-encrypted at rest and only ever returned masked.

**Embeddings are deliberately NOT switchable.** The FAISS index holds 1536-dim
ada-002 vectors and `SIMILARITY_THRESHOLD=1.8` is calibrated to that model's L2
distances, so changing embedding models would invalidate every stored vector.
An OpenAI key is required even when chat runs elsewhere.

**Key resolution order:** database → environment variable (`OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`). Existing `.env`-only setups keep working.

### ⚠️ Anthropic model gotcha
`temperature` was REMOVED on `claude-opus-5`, `claude-sonnet-5`, `claude-opus-4-8/4-7`
and the Fable models — sending it returns HTTP 400. `anthropic_provider.py` gates
sampling via `NO_SAMPLING_MODELS` and steers cost with `output_config.effort` instead.
Do not "restore" `temperature=0.3` for those models.

**Run commands:**
```bash
./app.sh start        # backend :8000 + frontend :5173 (single instance, logs in logs/)
./app.sh status|stop|restart

# Or manually:
# cd backend && uvicorn app.main:app --reload
# cd frontend && npm run dev
# Keys: Settings UI (stored encrypted) or backend/.env as fallback
```

---

**Remember:** Values in config.py were tuned through iterative user testing with screenshots. The system prompt went through 3 versions to balance helpfulness vs hallucination prevention. Prompt injection defenses were added after user pentesting. Don't undo this work without explicit approval.
