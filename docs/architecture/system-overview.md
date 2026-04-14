# System Overview

This diagram shows the runtime topology of WACH Insight: how the frontend, backend, and data stores connect, and where the LLM sits relative to the Docker boundary.

```mermaid
flowchart TD
    USER["Hospital Staff / Engineer\n(Browser — HTTPS)"]

    subgraph Docker ["Docker Compose"]
        FE["Frontend\nReact + Vite + TypeScript\nNginx (prod) / Vite dev server (local :3000)"]
        BE["Backend\nFastAPI + Gunicorn\nport 8081"]
        IDB[("InfluxDB\nAHU sensor time-series\npower, current, THD, PF, voltage")]
        DDB[("DuckDB\nETL analytics store\nFAIR scores, forecasts, heatmaps")]
        CDB[("ChromaDB\nVector store\nRAG knowledge base")]
    end

    LLM["Qwen LLM\nInference server\n(external host or local)"]

    USER -->|"HTTPS — port 443 / 3000"| FE
    FE -->|"REST /api/* — Bearer auth"| BE
    BE -->|"Flux queries"| IDB
    BE -->|"SQL (DuckDB SQL dialect)"| DDB
    BE -->|"Vector similarity search (top-k)"| CDB
    BE <-->|"HTTP chat completions"| LLM
```

## Component Responsibilities

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | React 18, Vite, TypeScript, Tailwind v3, Zustand | Dashboard UI, level selector, chatbot panel |
| Backend | FastAPI, Python 3.10, Gunicorn | REST API, business logic, LLM orchestration |
| InfluxDB | InfluxDB v2, Flux query language | Raw AHU electrical measurements (time-series) |
| DuckDB | DuckDB (file-backed) | FAIR score computation, forecasts, heatmaps (analytics layer over CSV/parquet) |
| ChromaDB | ChromaDB (embedded) | RAG document embeddings for the chatbot knowledge base |
| Qwen LLM | Qwen (via HTTP) | Chat completions, NL→structured query translation |

## Docker Boundary

In production, all components except the Qwen LLM run inside a single Docker Compose stack. The LLM can be co-located or on a separate host — the backend connects to it via `LLM_BASE_URL` (see `.env.example`).

In local development, the Vite dev server proxies `/api` to `localhost:8081`, so the frontend and backend can run independently without Docker.
