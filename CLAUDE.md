# Document Q&A Bot - Development Guide

## Project Overview
RAG-based document Q&A system: Python FastAPI + OpenAI (GPT-3.5 + ada-002) + FAISS + React frontend.
Supports PDF/TXT/DOCX with hallucination prevention and 3-layer prompt injection defense.

## Directory Structure (Key Files Only)
```
backend/
├── app/
│   ├── config.py                    # ALL configuration (CRITICAL - tuned values)
│   ├── sanitizer.py                 # Injection defense layers 1 & 2
│   ├── middleware.py                # Rate limiting
│   ├── routers/
│   │   ├── upload.py                # POST /upload, GET /documents, DELETE /documents/{name}
│   │   └── query.py                 # POST /query
│   ├── services/
│   │   ├── document_processor.py    # Parse files + chunk text
│   │   ├── embedding_service.py     # OpenAI embedding calls
│   │   └── qa_service.py            # QA orchestration (MOST COMPLEX)
│   └── store/
│       └── vector_store.py          # FAISS index management
├── uploads/                         # Uploaded files (runtime)
├── faiss_index/                     # FAISS index + metadata (runtime)
│   ├── index.faiss
│   └── metadata.json
└── .env                             # OPENAI_API_KEY

frontend/src/
├── App.jsx, api.js
└── components/ (FileUpload, ChatWindow, MessageInput)
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
MAX_QUESTION_LENGTH = 1000   # Input length limit
RATE_LIMIT_REQUESTS = 20     # Per 60 seconds per IP
EMBEDDING_MODEL = "text-embedding-ada-002"  # 1536 dimensions
LLM_MODEL = "gpt-3.5-turbo"

# Paths
UPLOAD_DIR = "uploads"
FAISS_INDEX_PATH = "faiss_index"
FAISS_INDEX_FILE = "faiss_index/index.faiss"
METADATA_FILE = "faiss_index/metadata.json"
```

## RAG Pipeline Flow
```
UPLOAD: File → Parse → Chunk (1000 chars, 200 overlap) → Embed (ada-002) → FAISS IndexFlatL2
QUERY: Question → Sanitize → Inject detection → Embed → FAISS search → Filter (≤1.8 distance) → GPT-3.5
        └─> If summary query detected: retrieve ALL chunks instead of top-k
```

## Key Design Decisions (Critical Context)

### 1. SIMILARITY_THRESHOLD = 1.8 (NOT 1.2)
**Why:** Ada-002 produces normalized embeddings with L2 distance 0-2. Initially 1.2 was too strict - user reported bot refusing ALL questions despite relevant context. Raised to 1.8 after user testing with screenshots.

### 2. System Prompt Evolution (3 Versions)
- **V1 (Too Loose):** "Answer based on context" → Hallucinated freely
- **V2 (Too Strict):** "ONLY use explicit info, NEVER add knowledge" → Refused to answer "what weighed around 83kg?" when context said "Sputnik: 83.6kg" (interpreted as word-for-word match required)
- **V3 (Balanced - CURRENT):** "Synthesize across passages. Don't invent facts. NEVER guess numbers." → Allows "83.6kg ≈ around 83kg" but prohibits invented statistics

**Location:** `qa_service.py` - system prompt with XML delimiters

### 3. Summary Query Detection
Specific questions ("When was Sputnik launched?") use top-k retrieval.
Broad queries ("summarise", "list all", "how many chapters") send ALL chunks.
**Why:** Without this, "list all launches" only retrieved 8 chunks similar to "launches", missing most content.

**Implementation:** `qa_service.py::SUMMARY_PATTERNS` regex + `_is_summary_query()`

### 4. 3-Layer Prompt Injection Defense
**Layer 1 (sanitizer.py):** Strip control chars, enforce MAX_QUESTION_LENGTH
**Layer 2 (sanitizer.py):** Regex blocks known patterns ("ignore instructions", "reveal prompt", etc.)
**Layer 3 (qa_service.py):** System prompt hardening + XML tags (`<document_context>`, `<user_question>`)

**Evidence:** User tested with defenses disabled (prompt leakage occurred) vs enabled (all attacks blocked).

### 5. FAISS Index Deletion
FAISS IndexFlatL2 doesn't support deletion → rebuild entire index without deleted doc's vectors.
**Performance:** O(n) rebuild acceptable because deletions are infrequent.

## Critical Code Patterns

### Summary Detection (qa_service.py)
```python
SUMMARY_PATTERNS = re.compile(
    r'\b(summari[sz]e|overview|list\s+all|entire\s+document|'
    r'how\s+many\s+(chapters?|sections?|parts?))\b', re.IGNORECASE)

def _is_summary_query(q): return bool(SUMMARY_PATTERNS.search(q))
# If True: get_all_chunks(), else: vector_store.search(embedding, top_k=8)
```

### Injection Defense (sanitizer.py)
```python
INJECTION_PATTERNS = re.compile(
    r'ignore\s+(all\s+)?previous\s+instructions|you\s+are\s+now\s+a|'
    r'reveal\s+(your|the)\s+(system\s+)?prompt|pretend\s+(you\s+are|to\s+be)|'
    r'forget\s+(everything|all\s+previous)|new\s+instructions:', re.IGNORECASE)

def detect_injection(q): return bool(INJECTION_PATTERNS.search(q))
# If True: return safe response immediately, skip LLM call
```

### FAISS Search with Threshold (vector_store.py)
```python
distances, indices = self.index.search(query_vector, top_k)
results = [self.metadata[idx] for dist, idx in zip(distances[0], indices[0])
           if dist <= SIMILARITY_THRESHOLD]  # CRITICAL FILTER
```

## API Endpoints (Brief)
- `POST /api/upload` - multipart/form-data → {message, filename, chunks_added}
- `POST /api/query` - {question: str} → {answer: str, sources: [{doc, chunk_index}]} (Legacy, kept for compatibility)
- `POST /api/chat` - {messages: [{role, content}]} → SSE stream (AI SDK format) **[NEW: Streaming endpoint]**
- `GET /api/documents` - → {documents: [filenames]}
- `DELETE /api/documents/{filename}` - → {message, filename}

## Troubleshooting Quick Reference

| Problem | Check |
|---------|-------|
| Bot refuses to answer | 1. SIMILARITY_THRESHOLD=1.8 (not lower)<br>2. System prompt is balanced V3<br>3. Documents uploaded |
| Hallucinated numbers | 1. System prompt has "NEVER guess numbers"<br>2. SUMMARY_PATTERNS includes "how many"<br>3. TEMPERATURE=0.3 |
| Summary queries incomplete | 1. Query matches SUMMARY_PATTERNS<br>2. get_all_chunks() called |
| Prompt injection works | 1. INJECTION_PATTERNS covers phrase<br>2. detect_injection() called in query.py<br>3. XML tags in prompt |

## File Modification History (What Changed and Why)

### config.py
- `SIMILARITY_THRESHOLD`: 1.2 → 1.8 (user testing: bot refused all questions)
- `TEMPERATURE`: 0.1 → 0.3 (too rigid → balanced)
- `TOP_K_RESULTS`: 4 → 5 → 8 (insufficient context → adequate)

### qa_service.py
- System prompt: V1→V2→V3 (loose→strict→balanced)
- Added SUMMARY_PATTERNS regex for broad query detection
- Added XML tag delimiters for injection defense

### sanitizer.py
- Entire file added after user requested prompt injection defense
- Tested with user: defenses OFF (leaked) vs ON (blocked)

### vector_store.py
- Added remove_document() method (user requested deletion)
- Added SIMILARITY_THRESHOLD filtering in search()

### AI SDK Migration (Latest)
**Frontend:**
- Added Vercel AI SDK (`ai` package) for streaming support
- Created `useDocumentChat` hook wrapping AI SDK's useChat
- Modified App.jsx to use streaming state management
- Updated ChatWindow.jsx with streaming cursor animation
- Source citations via AI SDK's StreamData API (message.data.sources)

**Backend:**
- Created `qa_service_streaming.py` - streaming version preserving all RAG logic and security
- Created `chat.py` router - SSE endpoint compatible with AI SDK format
- New `/api/chat` endpoint - accepts AI SDK message format, returns streaming response
- Original `/api/query` kept for backward compatibility
- **Security preserved:** All 3 layers (sanitization, injection detection, prompt hardening) active in streaming path

## When to Modify What

### ✅ Safe to change:
- Frontend styling, UI text, log messages

### ⚠️ Requires user testing:
- SIMILARITY_THRESHOLD, TEMPERATURE, TOP_K_RESULTS, CHUNK_SIZE/OVERLAP
- System prompt wording
- SUMMARY_PATTERNS regex

### 🛡️ Requires security review:
- INJECTION_PATTERNS (could miss attacks)
- System prompt security instructions
- Input sanitization logic

### 🚫 NEVER change without user approval:
- Remove prompt injection defenses
- Disable similarity threshold filtering
- Weaken anti-hallucination guidelines
- Expose system prompts to users

## Quick Reference for AI Assistants

**Bot not answering?**
1. Check SIMILARITY_THRESHOLD=1.8 in config.py
2. Check system prompt is balanced (V3) in qa_service.py
3. Ask for screenshot/example

**Hallucination reported?**
1. Verify SUMMARY_PATTERNS includes query type (e.g., "how many")
2. Check system prompt has "NEVER guess numbers"
3. Verify TEMPERATURE=0.3

**New feature request?**
1. Check if it impacts security (injection/hallucination guards)
2. Identify affected files from structure above
3. Test with user before finalizing

**Security issue?**
1. Check INJECTION_PATTERNS coverage in sanitizer.py
2. Verify detect_injection() called in query.py before QA
3. Test with defenses disabled vs enabled

**Common pitfalls:**
- Empty results? Check FAISS index exists and documents uploaded
- API errors? Check .env has OPENAI_API_KEY
- Index corruption? Delete faiss_index/ directory and re-upload

## Dependencies (Key Ones)
- `fastapi` - Web framework
- `openai==1.3.0` - OpenAI API (ada-002 + GPT-3.5)
- `faiss-cpu` - Vector similarity search (IndexFlatL2)
- `langchain` - RecursiveCharacterTextSplitter for chunking
- `PyPDF2`, `python-docx` - File parsing
- React + Vite + Tailwind (frontend)

## Documentation
- **LEARNING.md** - Educational guide (RAG concepts, prompt injection testing, lessons learned)
- **This file** - Implementation reference for AI assistants

**Run commands:**
```bash
# Backend: cd backend && uvicorn app.main:app --reload
# Frontend: cd frontend && npm run dev
# API key: backend/.env → OPENAI_API_KEY=sk-...
```

---

**Remember:** Values in config.py were tuned through iterative user testing with screenshots. The system prompt went through 3 versions to balance helpfulness vs hallucination prevention. Prompt injection defenses were added after user pentesting. Don't undo this work without explicit approval.
