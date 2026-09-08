# Document Q&A Bot - Development Guide

## Project Overview
RAG-based document Q&A system: Python FastAPI + FAISS + React frontend, with a
pluggable chat-provider layer (OpenAI / Anthropic / Gemini / Azure OpenAI).
Supports PDF/TXT/DOCX with hallucination prevention and 3-layer prompt injection defense.

**Where the product is going:** a single app with three tiles — **RAG**,
**Tool Calling**, **Guardrails** — that share one chat shell and differ only in
the backend pipeline behind them. RAG and Tool Calling ship today; Guardrails is described
under [Three-Tile Architecture](#three-tile-architecture-target-state).

## Directory Structure (Key Files Only)
```
app.sh                               # start/stop/restart/status for the whole stack (single-instance lock)
backend/
├── app/
│   ├── config.py                    # ALL configuration (CRITICAL - tuned values)
│   ├── crypto.py                    # Encrypt/decrypt stored API keys + mask() for display
│   ├── sanitizer.py                 # Injection defense layers 1 & 2
│   ├── sse.py                       # AI SDK v4 part formatter, shared by every pipeline
│   ├── middleware.py                # Rate limiting
│   ├── routers/
│   │   ├── upload.py                # POST /upload, GET /documents, DELETE /documents/{name}
│   │   ├── query.py                 # POST /query (legacy, non-streaming)
│   │   ├── chat.py                  # POST /chat - SSE stream in AI SDK v4 format
│   │   ├── tools.py                 # GET /tools (catalog) + POST /tools/chat
│   │   ├── chats.py                 # Chat history: list / read / rename / delete
│   │   └── settings.py              # Provider config CRUD + activate + live key test
│   ├── services/
│   │   ├── document_processor.py    # Parse files + chunk text
│   │   ├── embedding_service.py     # OpenAI embedding calls (batched)
│   │   ├── context_builder.py       # Token-budgeted context assembly + count_tokens()
│   │   ├── qa_service.py            # QA orchestration, non-streaming
│   │   ├── qa_service_streaming.py  # QA orchestration, streaming (MOST COMPLEX)
│   │   ├── tool_service.py          # Tool-calling loop (max 4 iterations)
│   │   ├── chat_history.py          # Persistence tap around every stream
│   │   ├── tools/
│   │   │   ├── registry.py          # TOOLS dict - single source of truth for model AND UI
│   │   │   ├── weather.py           # get_weather via Open-Meteo (keyless)
│   │   │   ├── calculator.py        # AST-sandboxed arithmetic (never eval)
│   │   │   └── documents.py         # search_documents / list_documents (RAG as a tool)
│   │   └── providers/
│   │       ├── __init__.py          # PROVIDER_CATALOG + registry/resolution logic
│   │       ├── base.py              # ChatProvider ABC, ProviderError, usage_dict()
│   │       ├── openai_provider.py   # OpenAI + Azure OpenAI
│   │       ├── anthropic_provider.py
│   │       └── gemini_provider.py
│   └── store/
│       ├── vector_store.py          # FAISS index management
│       ├── settings_store.py        # SQLite: provider settings + THE one active provider
│       ├── chat_store.py            # SQLite: chat sessions + messages (same app.db)
│       └── bootstrap.py             # ONE-TIME import of legacy .env keys into the DB
├── data/                            # Local app DB (runtime, gitignored)
│   ├── app.db                       # provider settings + encrypted keys + chat history
│   └── .secret_key                  # Master key, 0600
├── uploads/                         # Uploaded files (runtime)
├── faiss_index/                     # index.faiss + metadata.json (runtime)
└── .env.example                     # No keys — documents the optional APP_SECRET_KEY only

frontend/src/
├── App.jsx                          # Tile router: null | 'rag' | 'tools' | 'guardrails'
├── modes.jsx                        # The three tiles' metadata (see Three-Tile Architecture)
├── api.js
├── pages/ (LandingPage, RagMode, ToolsMode, PlaceholderMode)
├── hooks/useDocumentChat.js         # Wraps AI SDK useChat + owns the tile's chat history
└── components/ (ChatShell, ChatHistory, DocumentsModal, SettingsPanel, ProviderIcon, FileUpload, ChatWindow, MessageInput)
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
- Key resolution: **SQLite (encrypted), and nothing else**. Nothing on the request
  path reads `OPENAI_API_KEY` & co. Keys are never returned to the client, only a
  mask like `sk-...b3f9`.
- **Exactly one provider is active** at a time (`app_state.active_chat_provider`).
  Activating requires a stored key; deleting the active provider hands "active" to
  another configured one so chat never points at a keyless provider.
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

### 7. API Key Storage — local file only, no `.env`
Keys live encrypted in `backend/data/app.db` (`crypto.py`), unlocked by
`APP_SECRET_KEY` or a generated `data/.secret_key`. `data/` is gitignored.
The settings API returns `masked_key` only — never the plaintext key.

**`.env` is no longer a key source.** Provider keys are configured exclusively
through the Settings UI, so there is one place to look and one active provider.
`store/bootstrap.py` copies a key still present in the environment into the
database **once**, on the first start after this change, then writes the
`legacy_env_keys_imported` flag and never reads the environment again — an
upgrade path, not a fallback. A key re-added to `.env` afterwards is ignored.
`APP_SECRET_KEY` remains the one meaningful env var (it unlocks the store).

## Three-Tile Architecture (Target State)

One landing page, three tiles, **one shared chat shell**. Do not build three apps —
the tiles differ only in which pipeline the chat endpoint runs.

| Tile | Route | Pipeline | Endpoint |
|------|-------|----------|----------|
| **RAG** | `/chat` | question → retrieve → LLM → text | `/api/chat` (exists) |
| **Tool Calling** | `/tools` | question → LLM picks tool → execute → feed result back → LLM → readable text | `/api/tools/chat` (exists) |
| **Guardrails** | `/guardrails` | question → sanitize → injection check → RAG → output check → text + verdict | `/api/guardrails/chat` (new) |

The landing page with the three tiles is `/`. Unknown paths redirect to `/`.

### Frontend layout (BUILT)
```
frontend/src/
├── main.jsx                 # wraps <App/> in <BrowserRouter>
├── App.jsx                  # <Routes>: one route per tile, built from MODES
├── modes.jsx                # MODES registry: path, title, tagline, steps, endpoint, icon, accent classes
├── pages/
│   ├── LandingPage.jsx      # the three tiles
│   ├── RagMode.jsx          # sidebar: chat history + recent docs → "View all documents" popup
│   ├── ToolsMode.jsx        # sidebar: live tool catalog from GET /api/tools
│   └── PlaceholderMode.jsx  # preview for a tile with no backend yet (composer disabled)
├── components/
│   ├── ChatShell.jsx        # shared layout: <aside>{history}{sidebar}{sidebarFooter}</aside> + ChatWindow + MessageInput
│   ├── ChatHistory.jsx      # new chat / open / rename / delete, in every tile's sidebar
│   ├── DocumentsModal.jsx   # RAG tile popup: upload + session stats + full index + delete
│   ├── SettingsPanel.jsx    # provider modal, mounted once in App.jsx (global to all tiles)
│   └── ToolCallCard.jsx     # renders one tool invocation: name, args, raw result
└── hooks/useDocumentChat.js # useDocumentChat({ api }) — defaults to '/api/chat'
```
Routing is `react-router-dom` v7 (`BrowserRouter` in `main.jsx`). Each tile is a
real, shareable URL — the routes are generated by mapping over `MODES`, so
adding a tile means adding one registry entry with a `path`. Tiles on the
landing page are `<Link>`s (right-click / open-in-new-tab work) and the sidebar
back button links to `/`.

**Deep links need an SPA fallback.** The Vite dev server does this by default;
any production host must also rewrite unknown paths to `index.html`, or
`/chat` will 404 on refresh.

`SettingsPanel` is mounted outside `<Routes>` so the modal survives navigation.

`modes.jsx` is the single source of truth for the tiles. Accent colours are
written out as **complete class strings** (`bg-violet-600`, not
``bg-${accent}-600``) because Tailwind cannot see dynamically built names; the
violet tokens used by the Tool Calling tile are defined in `index.css` `@theme`.

Replacing `PlaceholderMode` with a real tile means: add the page, point it at
the mode's `endpoint`, and switch on `mode.id` in the route element in `App.jsx`. `ChatShell`,
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

**How it is wired (BUILT):** `ChatProvider` keeps its single-turn
`complete()` / `stream()` untouched; tool calling is a third method so the RAG
path could not regress:

```python
def stream_tools(self, system: str, messages: list[dict],
                 tools: list[dict]) -> Iterator[dict]:
    """Yield {"type": "text"|"tool_call"|"usage", ...}.
    Base implementation raises ProviderError('<label> tool calling is not wired up yet').
    """
```
`messages` uses a neutral, OpenAI-ish shape that each provider maps onto its own
wire format — `{"role","content"}`, `{"role":"assistant","tool_calls":[{id,name,args}]}`,
`{"role":"tool","tool_call_id","content"}`. Only **OpenAI/Azure implements it**;
Anthropic and Gemini inherit the clear error, and the Tools tile tells the user
to switch provider under Settings.

Each provider normalizes its own wire format into that shared event shape:
- **OpenAI** — `tools=[...]`, accumulate streamed `delta.tool_calls` argument fragments, reply with `{"role": "tool", "tool_call_id": ...}`
- **Anthropic** — `tools=[...]`, `stop_reason == "tool_use"`, reply with a `tool_result` content block
- **Gemini** — `function_declarations`, `functionCall` / `functionResponse` parts

⚠️ OpenAI streams tool-call arguments as **fragments addressed by `index`, not by
id** — accumulate per index across chunks and only `json.loads` once the stream
ends. Parsing early yields truncated JSON.

**Surfacing tool calls in the UI (BUILT):** `app/sse.py` speaks AI SDK v4 part
codes (`0:` text, `8:` annotation, `d:` finish, `3:` error) plus
`9:{"toolCallId","toolName","args"}` and `a:{"toolCallId","result"}`, which
`useChat` exposes as `message.toolInvocations` — rendered by `ToolCallCard.jsx`
with no custom stream parsing on the frontend.

### The tool registry (`services/tools/registry.py`)

One dict is the single source of truth: the schemas sent to the model, the
executor, and the list the UI shows are all derived from it, so the sidebar can
never claim a tool the model doesn't have.

| Tool | kind | What it does |
|------|------|--------------|
| `get_weather` | `api` | Live current weather via Open-Meteo — **keyless**, so the tile demos a real external API without a second key to configure. Two hops: name → coordinates → forecast. |
| `calculator` | `local` | Arithmetic, **AST-sandboxed** |
| `search_documents` | `rag` | Semantic FAISS search — same embedding, same `SIMILARITY_THRESHOLD` filter as the RAG tile |
| `list_documents` | `rag` | Uploaded filenames + chunk counts |

Adding a tool = one entry (`schema`, `fn`, `label`, `kind`, `example`). `kind`
drives the UI badge, `example` becomes the clickable "Try:" prompt.

🛡️ **`calculator` must never use `eval()`.** The model will pass it arbitrary
strings straight from the chat box, so an `eval` there is remote code execution
reachable by any user. It parses to an AST and walks a whitelist of node types,
with an exponent cap so `2**99999999` can't pin a core. Verified blocked:
`__import__("os").system(...)`, `open(...)`.

**`run_tool()` never raises.** A tool failure returns `{"error": ...}` as data so
the model can explain it. A raised exception would drop the SSE stream with no
`d:` finish frame and hang the UI.

**Tool results are untrusted input.** They are appended to the conversation, so
the tool-calling system prompt states that results are DATA to report on, never
commands to obey — a document passage or an API response could otherwise carry an
injection.

### RAG tile: the documents popup

Everything document-related lives in `DocumentsModal`, not the sidebar: the
upload dropzone, the session stats (documents / chunks indexed / questions
asked), the full index with a filename filter once there are more than 5 files,
and delete. The sidebar keeps the conversation — chat history, plus a preview of
the 3 newest uploads (`SIDEBAR_DOCS` in `RagMode.jsx`) — and one button into the
popup, labelled **Upload a document** while the index is empty and
**View all documents (N)** once it isn't. That button sits in `ChatShell`'s
`sidebarFooter` slot, pinned under the scrolling area and above the provider
badge, so it stays reachable however long the chat history grows.

The modal renders from the `documents` state the tile already holds and calls the
tile's `handleUploadSuccess` / `handleDelete`, so there is one source of truth:
the preview, the stats and the popup can never disagree, and opening it costs no
extra fetch. `FileUpload` takes a `className` prop (default `p-4`) so the modal
can supply its own spacing.

### Chat history (BUILT)

Every turn on every tile is stored, so a conversation survives a reload, can be
re-opened from the sidebar, and can be continued where it left off.

```
POST /api/chat | /api/tools/chat  {messages, chatId?}
  └─ ensure_session(chatId, mode)   → opens one if the client didn't send it
  └─ save_message(user)             → the raw question, before sanitization
  └─ record_stream(session, pipeline)
        passes every event through untouched, then writes the assistant
        message (text + annotations + tool invocations) when the stream ends
```

- **Storage:** `store/chat_store.py` — `chat_sessions` + `chat_messages` in the
  same `backend/data/app.db` as provider settings. One local file, no server.
- **Scoped by tile:** a session's `mode` ('rag' / 'tools') is the history bucket,
  so each sidebar lists only its own conversations. A new tile gets history for
  free by passing its `mode.id` to the hook.
- **Titles** come from the first user message (`make_title`, 60 chars); the
  sidebar can rename.
- **Stored in the AI SDK's shape** — `annotations` (sources / provider / usage)
  and `toolInvocations` are saved as JSON, so a reloaded turn renders with its
  citations and tool cards exactly like the live stream did.
- **`chatId` travels in the request body**, passed per turn via
  `append(msg, { body: { chatId } })`, so the answer lands in the chat the user
  is actually looking at. A turn sent without one opens a conversation and
  returns its id on the `X-Chat-Id` header (`expose_headers` in main.py).

⚠️ **History must never be able to break an answer.** `chat_history.py` catches
its own write failures and degrades to "this turn isn't saved"; the assistant
message is written in a `finally`, so a client that disconnects mid-answer still
keeps what was generated. `add_message` returns None for a session deleted
mid-stream rather than recreating it.

Blocked injection attempts are stored too — the transcript shows what was asked
and what the guard replied.

Reading history is exempt from the rate limiter (`middleware.py`,
GET `/api/chats*` only): browsing local SQLite must not consume the budget that
protects the paid endpoints. Create / rename / delete still count.

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
1. ~~Extract `ChatShell` + landing page → RAG tile works immediately~~ **DONE** — landing page, `modes.jsx`, `ChatShell`, `RagMode`, `PlaceholderMode`, per-tile routes; RAG behaviour unchanged
2. ~~Extract `app/sse.py`; add `stream_tools` to `base.py` (raising default) + OpenAI implementation~~ **DONE**
3. ~~Tool registry with 4 tools + `/api/tools/chat` + `ToolCallCard`~~ **DONE**
4. Guardrails router + verdict panel
5. Anthropic / Gemini tool support last

**Resolved:** `search_documents` and `list_documents` ARE registered, so the Tools
tile can also answer document questions. The model choosing between retrieval and
an external API is the better demo. The tiles still differ clearly: RAG always
retrieves, Tools decides whether to.

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
- `POST /api/chat` - {messages:[{role,content}], chatId?} → SSE stream (AI SDK v4 format)
- `GET /api/documents` - → {documents:[{filename, chunks}]}
- `DELETE /api/documents/{filename}` - → {message, filename}
- `GET /api/providers` - → {active, providers:[...]}  (keys masked)
- `PUT /api/providers/{provider}` - update api_key / model / base_url / api_version
- `POST /api/providers/{provider}/activate` - switch the active chat provider
- `POST /api/providers/{provider}/test` - validate credentials with a live call
- `DELETE /api/providers/{provider}` - remove stored settings
- `GET /api/tools` - → {count, tools:[{name, label, kind, description, parameters, example}]}
- `POST /api/tools/chat` - {messages:[...], chatId?} → SSE stream with tool call/result parts
- `GET /api/chats?mode=rag` - → {count, chats:[{id, mode, title, updated_at, message_count, preview}]}
- `POST /api/chats` - {mode, title?} → the new chat (titled by its first question)
- `GET /api/chats/{id}` - → {chat, messages:[{id, role, content, createdAt, annotations, toolInvocations}]}
- `PATCH /api/chats/{id}` - {title} → rename
- `DELETE /api/chats/{id}` - → {message, id}
- *(planned)* `POST /api/guardrails/chat`

## Troubleshooting Quick Reference

| Problem | Check |
|---------|-------|
| Bot refuses to answer | 1. SIMILARITY_THRESHOLD=1.8 (not lower)<br>2. System prompt is balanced V3<br>3. Documents uploaded |
| Hallucinated numbers | 1. System prompt has "NEVER guess numbers"<br>2. SUMMARY_PATTERNS includes "how many"<br>3. TEMPERATURE=0.3 |
| Summary queries incomplete | 1. Query matches SUMMARY_PATTERNS<br>2. get_all_chunks() called<br>3. MAX_CONTEXT_TOKENS not truncating |
| Prompt injection works | 1. INJECTION_PATTERNS covers phrase<br>2. detect_injection() called in the router<br>3. XML tags in prompt |
| "Chat provider is not ready" | 1. Key saved via the Settings UI / `PUT /api/providers` — `.env` is NOT read<br>2. Model name set<br>3. Azure also needs base_url + api_version |
| Stream dies mid-answer | Malformed SSE part — every part needs its code prefix and trailing `\n`; `d:` needs a finishReason |
| "tool calling is not wired up yet" | Only OpenAI/Azure implements `stream_tools()` — switch provider under Settings |
| Tool cards don't render | Parts must be `9:` then `a:` with matching `toolCallId`; `useChat` drops unpaired ones |
| Model answers without calling a tool | Schema `description` is what it selects on — say when to use the tool, not just what it does |
| Tool loop stops early | `MAX_ITERATIONS = 4` in `tool_service.py` |
| Answers stop but UI hangs | The `d:` finish frame was never emitted |
| Chat not saved | Backend log shows "Chat history..." — the write failed but the answer still streamed; check `backend/data/app.db` is writable |
| Re-opened chat lost its tool cards | `toolInvocations` are stored on the assistant row — a turn that never finished streaming has none |
| Sidebar list not updating | `refreshChats()` runs in the hook's `onFinish`; a stream that errored never fires it |

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

### Tool Calling (Latest)
- Added `app/sse.py`; `chat.py` now imports it instead of formatting parts inline (RAG behaviour unchanged)
- Added `stream_tools()` to `ChatProvider` (raising default) + the OpenAI/Azure implementation
- Added `services/tools/` (registry + weather/calculator/documents) and `services/tool_service.py`
- Added `routers/tools.py`: `GET /api/tools`, `POST /api/tools/chat` — same sanitize + injection check as `/api/chat`
- Frontend: `ToolsMode.jsx`, `ToolCallCard.jsx`, `getTools()`; `ChatWindow` renders `message.toolInvocations`
- `ChatWindow` empty-state icon is now parameterized (`EmptyIcon` / `emptyAccent`), fed from `mode.accent.gradient`
- `modes.jsx`: Tool Calling `status: 'live'`, added `accent.gradient` to all three tiles

### RAG Documents Popup (Latest)
- Added `components/DocumentsModal.jsx` (Escape / backdrop close, upload, stats,
  filter, delete)
- `RagMode.jsx`: FileUpload and the Session Overview block moved out of the sidebar
  into the popup; the sidebar keeps a 3-item preview and the button that opens it
- `FileUpload.jsx`: outer padding is now a `className` prop so it can sit in the modal
- `ChatShell.jsx`: added the `sidebarFooter` slot (pinned, below the scroll area)
  and RagMode's documents button moved into it
- `ChatWindow.jsx` / `MessageInput.jsx`: transcript and composer share one centred
  `max-w-4xl` column with `px-6 md:px-10 lg:px-16` gutters, so messages no longer
  stretch edge to edge on a wide screen

### Chat History (Latest)
- Added `store/chat_store.py` (sessions + messages) and `services/chat_history.py`
  (`ensure_session` / `save_message` / `record_stream`)
- Added `routers/chats.py`; `main.py` initializes the tables and exposes `X-Chat-Id`
- `chat.py` / `tools.py`: optional `chatId` on the request, turns persisted around
  the unchanged pipelines — the security layers run exactly as before
- `middleware.py`: GET `/api/chats*` exempt from the per-IP rate limit
- Frontend: `useDocumentChat` gained `send` / `chats` / `chatId` / `newChat` /
  `openChat` / `removeChat` / `renameChat`; new `components/ChatHistory.jsx`;
  `ChatShell` gained a `history` slot above the mode sidebar; both tiles call
  `send()` instead of `append()`

### Provider Storage (Latest)
- `config.py`: dropped `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY`; added `LEGACY_ENV_KEYS`, read only by the migration
- `providers/__init__.py`: removed `_ENV_KEYS` and `api_key_from_env`; added an `icon` slug per catalog entry and `is_configured()`
- Added `store/bootstrap.py` + `settings_store.get_state()/set_state()`; `main.py` runs the one-time import at startup and logs what it imported
- `routers/settings.py`: returns `icon`, drops `key_from_env`; deleting the active provider reassigns "active" to a still-configured one
- Deleted `backend/.env`; `.env.example` now documents only the optional `APP_SECRET_KEY`
- Frontend: added `components/ProviderIcon.jsx` (OpenAI / Anthropic / Gemini / Azure brand marks); `SettingsPanel` gained an "Active for chat" strip and per-row badges and lost the "from .env" pill; `App.jsx` owns the active provider and passes it to every tile so `ChatShell` and `LandingPage` show it

### Multi-Provider Support
- Added `services/providers/` (OpenAI, Azure OpenAI, Anthropic, Gemini) behind a `ChatProvider` ABC
- Added `store/settings_store.py` (SQLite) + `crypto.py` (encrypted keys, masked display)
- Added `routers/settings.py` for provider CRUD / activate / live key test
- Embeddings deliberately pinned to OpenAI (index compatibility)
- `.env` fallback removed later — see [Provider Storage](#provider-storage-latest)
- Added `app.sh` for single-instance start/stop of both services

## When to Modify What

### ✅ Safe to change:
- Frontend styling, UI text, log messages
- Adding a model name to `PROVIDER_CATALOG["…"]["models"]`
- Adding a tool to `TOOLS` (registry.py) — the UI list follows automatically

### ⚠️ Requires user testing:
- SIMILARITY_THRESHOLD, TEMPERATURE, TOP_K_RESULTS, CHUNK_SIZE/OVERLAP, MAX_CONTEXT_TOKENS
- System prompt wording, SUMMARY_PATTERNS regex

### 🛡️ Requires security review:
- INJECTION_PATTERNS (could miss attacks)
- System prompt security instructions, input sanitization
- Anything touching `crypto.py` or key storage/masking
- `calculator.py`'s AST whitelist — it evaluates attacker-controlled strings
- Any new tool that touches the filesystem, network or shell
- The guardrails demo toggles (must never disable defenses on the real endpoints)

### 🚫 NEVER change without user approval:
- Remove prompt injection defenses
- Disable similarity threshold filtering
- Weaken anti-hallucination guidelines
- Expose system prompts or plaintext API keys to the client
- Re-introduce an environment-variable fallback for provider keys (one storage
  location, one active provider — see [API Key Storage](#7-api-key-storage--local-file-only-no-env))
- Change EMBEDDING_MODEL (invalidates the FAISS index)

## Quick Reference for AI Assistants

**Bot not answering?** SIMILARITY_THRESHOLD=1.8 → system prompt is V3 → documents uploaded → provider configured.
**Hallucination reported?** SUMMARY_PATTERNS covers the query type → "NEVER guess numbers" present → TEMPERATURE=0.3.
**New feature request?** Check security impact → identify affected files above → test with user before finalizing.
**Security issue?** INJECTION_PATTERNS coverage → detect_injection() called in the router → test defenses off vs on.

**Common pitfalls:**
- Empty results? Check the FAISS index exists and documents are uploaded
- Provider errors? `GET /api/providers` shows which are `configured` and which one `is_active`; keys come from `data/app.db` only, never `.env`
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
- React + Vite + Tailwind + Vercel AI SDK v4 + react-router-dom v7 (frontend)

## Multi-Provider Chat (Added)

Chat runs on OpenAI, Anthropic, Google Gemini, or Azure OpenAI — selected in the
Settings panel and stored in `backend/data/app.db` (SQLite, gitignored). Keys are
Fernet-encrypted at rest and only ever returned masked.

**Embeddings are deliberately NOT switchable.** The FAISS index holds 1536-dim
ada-002 vectors and `SIMILARITY_THRESHOLD=1.8` is calibrated to that model's L2
distances, so changing embedding models would invalidate every stored vector.
An OpenAI key is required even when chat runs elsewhere.

**Key resolution:** the local database, full stop — `backend/data/app.db`, one
active provider, managed in the Settings UI. Environment variables are read only
by the one-time `store/bootstrap.py` migration described under
[API Key Storage](#7-api-key-storage--local-file-only-no-env), so an older
`.env`-only install upgrades cleanly and `backend/.env` can then be deleted.

**Provider icons.** Each `PROVIDER_CATALOG` entry carries an `icon` slug
(`openai` / `anthropic` / `gemini` / `azure`) that `GET /api/providers` returns and
`components/ProviderIcon.jsx` maps to a brand SVG. Adding a provider means adding
the slug in both places; an unknown slug falls back to a neutral plug glyph. The
active provider's badge appears in the landing header and in every tile's sidebar
footer — that badge *is* the button that opens the settings panel, so the running
integration is visible from anywhere in the app.

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
# Keys: Settings UI only (stored encrypted in backend/data/app.db)
```

---

**Remember:** Values in config.py were tuned through iterative user testing with screenshots. The system prompt went through 3 versions to balance helpfulness vs hallucination prevention. Prompt injection defenses were added after user pentesting. Don't undo this work without explicit approval.
