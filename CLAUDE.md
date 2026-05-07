# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (Python/FastAPI)

```bash
cd backend
pip install -r requirements.txt
python main.py                           # Start dev server on :8000 with auto-reload
# or: uvicorn main:app --reload --host 0.0.0.0 --port 8000
python reindex_knowledge_base.py         # Full KB rebuild (re-parse + re-embed)
python reindex_knowledge_base.py --fast  # Re-embed only (keep existing chunks)
```

### Frontend (Vue 3/Vite)

```bash
cd frontend
npm install
npm run dev      # Dev server on :5173, proxies /api and /health to :8000
npm run build    # Production build
```

No test suite or linting is configured in this project.

## Architecture

This is a full-stack AI chat application — "智能助手" (Smart Assistant) — that generates work reports and answers questions from a knowledge base. It uses **three-intent routing**: report generation, knowledge base Q&A (RAG), and casual chat.

### Backend (`backend/`)

**Entry**: `main.py` — mounts all routers under `/api` prefix, sets CORS (allow all origins), exposes `/health`.

**Intent routing** (`routers/chat.py`): User messages are routed by keyword regex matching (`_is_report_intent`). When `kb_mode` is true (frontend toggle ON), RAG is forced regardless of intent. Reports use a two-stage pipeline: extract structured JSON from user input (non-streaming) → generate formatted markdown (streaming SSE).

**Streaming**: All chat and report generation uses SSE via `sse_starlette`. Frontend reads the raw `ReadableStream` with a manual SSE line parser (no `EventSource` API).

**AI client** (`services/ai_service.py`): Uses `aiohttp` for HTTP calls (no SDK). Calls any OpenAI-compatible `/v1/chat/completions` endpoint. Supports both streaming (`generate_stream`) and non-streaming (`generate`). Note: `httpx` has TLS compatibility issues with some Windows/Python versions, so the codebase uses `aiohttp` for async and `urllib` (stdlib) for sync HTTP.

**RAG pipeline** (`services/vector_store.py`, `services/rag_service.py`): Hybrid retrieval using Reciprocal Rank Fusion (RRF) combining:
- Cosine similarity over vector embeddings (`sqlite-vec` extension, falls back to JSON)
- BM25 keyword search (`rank-bm25` with Chinese 2-4 char n-gram tokenization)

**Embedding** (`services/embedding_service.py`): Calls an external OpenAI-compatible `/embeddings` endpoint. No local model — requires a separately deployed embedding service.

**Document chunking** (`services/document_parser.py`): Semantic chunking on sentence boundaries (。！？), ~350 chars per chunk, 50-char overlap. Parses `.txt` (multi-encoding detection with chardet), `.docx`, and `.pdf`.

**Sessions**: In-memory Python dict (not persisted across restarts).

### Frontend (`frontend/`)

**App shell** (`App.vue`): Header with health indicator, clear-chat button, KB panel toggle. Main area is chat view + optional KB sidebar. When the KB panel is closed, `kbMode` is automatically set to `false`.

**Chat state** (`composables/useChatStream.js`): Manages session creation, message list, SSE stream reading with manual line parsing. Handles `kb_context`, `stage`, `token`, and `error` SSE events. KB context chunks are buffered until the first real token to avoid UI flicker.

**Message rendering** (`components/ChatMessage.vue`): Markdown via `marked` (GFM + line breaks). Shows streaming typing indicator, two-stage report progress, export buttons (Word/PDF), and expandable KB reference chunks with relevance scores.

**KB toggle**: Two controls — the header "知识库" button opens the KB management sidebar; the input toggle switch enables RAG mode for chat. Both are synchronized: closing the sidebar disables RAG mode.

### Key Architecture Decisions

- **No LLM SDK** — raw httpx calls to OpenAI-compatible APIs, both for chat and embeddings
- **Intent detection by keyword**, not by LLM call — fast and deterministic
- **Two separate embedding services** possible — the LLM API and embedding API are independently configured
- **SSE for all streaming** — both chat tokens and report generation progress
- **Manual SSE parsing on frontend** — `fetch` + `ReadableStream` reader, not `EventSource`, to support POST requests with JSON bodies

## Configuration

Backend config is in `backend/.env` (contains real API keys — never commit this file):

```
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_API_KEY=<key>
OPENAI_MODEL=deepseek-chat
EMBEDDING_BASE_URL=http://localhost:8001/v1
EMBEDDING_API_KEY=<key>
EMBEDDING_MODEL=text-embedding-3-small
```

The embedding service must be deployed separately as an OpenAI-compatible API.

## Data Directory

- `backend/knowledge_base/vectors.db` — SQLite database (documents, chunks, vectors)
- `backend/knowledge_base/archives/` — Uploaded documents stored for reindexing
- `backend/knowledge_base/uploads/` — Temporary upload directory
- `backend/templates/word_template.docx` — Optional Word export template
- `backend/fonts/SourceHanSansCN.ttf` — CJK font for PDF export
