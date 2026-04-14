# Chat Pipeline

This diagram traces a single `POST /api/chat` request from the browser through every processing layer to the final JSON response.

```mermaid
flowchart TD
    REQ["POST /api/chat\nbody: {message, history, persona?}"]

    AUTH["API Key Auth Middleware\nChecks Authorization: Bearer header\nor ?api_key= query param"]
    RL["Global Rate Limiter\n100 req / 60s per IP\n(in-memory sliding window)"]
    PD["Persona Detector\nAuto-detect from message + history,\nor use explicit persona override\ngeneral · technical · technician · financial"]
    QC["Query Complexity Classifier\nInspects message length, keywords, history depth\nRoutes to /think (deep) or /no_think (fast)"]
    TOOLS["Tool-Augmented Generation\nQwenClient.generate_with_tools()\n5 callable tools during generation:"]
    T1["HealthDB Tool\nFAIR scores from DuckDB"]
    T2["InfluxDB Tool\nRaw measurements from InfluxDB"]
    T3["RAG Tool\nSemantic search in ChromaDB\n(WACH domain knowledge base)"]
    T4["Financial Tool\nEnergy costs, penalties, tariff config"]
    T5["Site Summary Tool\nFleet-wide health overview"]
    LLM["Qwen LLM\nGenerates reply using\ncontext + tool results + history"]
    RESP["JSON Response\n{reply, navigate, thinking_mode}"]

    ERR_AUTH["401 Unauthorized"]
    ERR_RATE["429 Too Many Requests"]
    ERR_LLM["503 AI Unavailable"]

    REQ --> AUTH
    AUTH -->|"invalid / missing key"| ERR_AUTH
    AUTH --> RL
    RL -->|"limit exceeded"| ERR_RATE
    RL --> PD
    PD --> QC
    QC --> TOOLS
    TOOLS <--> T1
    TOOLS <--> T2
    TOOLS <--> T3
    TOOLS <--> T4
    TOOLS <--> T5
    TOOLS --> LLM
    LLM --> RESP
    LLM -->|"client unavailable"| ERR_LLM
```

## Key Design Decisions

**Persona detection is automatic.** The system reads the message and conversation history to select a persona. Explicit `persona` overrides are honoured. The selected persona changes the system prompt and available tools.

**Tool calls happen inside the LLM generation loop.** Qwen can invoke any of the five tools zero or more times before producing its final reply. Results from each tool call are appended to the context window before the next generation step.

**Thinking mode is a prefix, not a separate model.** The `QC` step prepends `/think` or `/no_think` to the user message before it reaches the LLM. This controls Qwen's internal reasoning chain depth.

**No per-endpoint rate limiter.** Unlike `POST /api/query`, the `/api/chat` endpoint relies solely on the global 100 req/60s middleware in `main.py`. If you need tighter per-session limits, add a `SlowAPI` limiter to `routes/chat.py`.

## Related Components

| File | Role |
|------|------|
| `backend/routes/chat.py` | FastAPI route handler — entry point |
| `backend/core/persona_detector.py` | Persona auto-detection logic |
| `backend/core/query_classifier.py` | Complexity routing logic |
| `backend/ai/qwen_client.py` | LLM client with tool call loop |
| `backend/tools/` | Individual tool implementations |
| `backend/middleware/` | Auth and rate limiting middleware |
