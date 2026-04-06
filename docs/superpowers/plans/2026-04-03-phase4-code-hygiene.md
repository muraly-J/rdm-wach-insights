# Phase 4: Code Hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every backend module self-documenting, remove dead code, consolidate all configuration into one typed `Settings` object, clean up the frontend, and gate CI on ruff + prettier so the codebase stays clean.

**Architecture:** `config.py` becomes the single source of truth for all environment-sourced configuration via a `pydantic-settings` `Settings` model. All other modules import `settings` from there — no raw `os.getenv` outside `config.py`. Ruff replaces any scattered pylint/flake8 usage. Prettier enforces consistent TypeScript/TSX formatting.

**Tech Stack:** `pydantic-settings>=2.0`, `ruff>=0.4`, `mypy>=1.10`, `prettier` (npm), Python `typing` module

---

## Codebase audit (pre-work facts)

**Module docstrings**: 4 production files are missing docstrings — `models/schemas.py`, `rag/__init__.py`, `routes/__init__.py`, `tools/__init__.py`. All other production modules already have docstrings.

**Type hints**: Missing return annotations on route handlers across `routes/`, and on several helpers in `config.py`, `main.py`, `llm/client_factory.py`.

**Dead code**:
- `routes/update_level_endpoint.py` — is a debug script (modifies another file in-place), not a route. Not registered in `main.py`. Safe to delete.
- `sys.path.insert(0, os.path.dirname(__file__))` in `main.py:26` — redundant; `pyproject.toml` handles this via `pythonpath = ["."]`.
- `logging.basicConfig` in `routes/forecast.py:31–35` — missed in Phase 3 migration.

**Raw `os.getenv` outside `config.py`**: `tools/health_tools.py`, `llm/qwen_client.py`, `llm/prompts.py`, `llm/translator.py`, `core/csv_reader.py`, `routes/forecast.py`, `main.py`.

**Frontend**: `console.log` / `console.error` in `App.tsx` (3 calls), `api/client.ts` (1 call), `ScoreCardWithSelector.tsx` (1 `.catch(console.error)`). Zustand store actions in `useAppStore.ts` have inline comments but no JSDoc.

**Prettier**: Not installed. No `.prettierrc`. Must be added.

**Ruff / mypy**: Not in any requirements. No config. Must be added.

---

## File Structure

**Modified files:**
```
backend/requirements.txt                    — add pydantic-settings
backend/requirements-dev.txt               — add ruff, mypy
backend/config.py                          — replace getter functions with Settings model + singleton
pyproject.toml                             — add [tool.ruff] + [tool.mypy] sections
backend/main.py                            — remove sys.path.insert + use settings.*
backend/routes/forecast.py                — remove logging.basicConfig + use settings.*
backend/llm/translator.py                 — use settings.enable_llm
backend/llm/qwen_client.py               — use settings.lms_timeout
backend/llm/prompts.py                   — use settings.ward_config_path
backend/core/csv_reader.py               — use settings.csv_debug
backend/tools/health_tools.py            — use settings.chroma_persist_dir + rag_collection
backend/models/schemas.py                — add module docstring
backend/rag/__init__.py                  — add module docstring
backend/routes/__init__.py               — add module docstring
backend/tools/__init__.py                — add module docstring
backend/routes/chat.py                   — add return type hint to route handler
backend/routes/health_scores.py         — add return type hints to 4 route handlers
backend/routes/query.py                  — add return type hint to route handler
backend/llm/client_factory.py           — add return type hint
backend/config.py                        — add return type hints to getter functions
.github/workflows/ci.yml                — add ruff + prettier + mypy steps (create if absent)
frontend/package.json                    — add prettier devDependency
frontend/.prettierrc                     — create prettier config
frontend/src/App.tsx                     — remove console.log / console.error
frontend/src/api/client.ts              — remove console.error
frontend/src/components/dashboard/derivation/ScoreCardWithSelector.tsx — remove .catch(console.error)
frontend/src/store/useAppStore.ts       — add JSDoc to all store actions
```

**Deleted files:**
```
backend/routes/update_level_endpoint.py
```

---

## Task 1: Create `Settings` model in `config.py`

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/config.py`
- Test: `backend/tests/unit/test_settings.py`

Replace the current collection of standalone getter functions with a single `pydantic-settings` `Settings` class and a module-level singleton `settings`. Keep the existing getter functions as thin one-liners that delegate to `settings` — this avoids breaking 30+ callers in one go and is the minimal-risk path.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_settings.py`:

```python
"""
Unit tests for the centralised Settings model.

Tests:
- Settings is importable as a pydantic-settings BaseSettings subclass
- All expected fields exist with correct types and defaults
- settings singleton is already instantiated at import time
- No raw os.getenv calls remain outside config.py
"""
import ast
import pathlib
import pytest


class TestSettingsModel:
    def test_settings_importable(self):
        from config import settings
        assert settings is not None

    def test_settings_is_pydantic_model(self):
        from pydantic_settings import BaseSettings
        from config import Settings
        assert issubclass(Settings, BaseSettings)

    def test_required_fields_exist(self):
        from config import settings
        fields = [
            "influx_url", "influx_token", "influx_org", "influx_bucket",
            "lms_base_url", "lms_model", "lms_api_key", "lms_timeout",
            "enable_llm", "chroma_persist_dir", "rag_collection",
            "api_key", "dev_api_key", "cors_origins",
            "app_env", "rate_limit_requests", "rate_limit_window",
            "alert_webhook_url", "csv_debug",
            "wach_building_name", "wach_department", "hospital_id",
        ]
        for field in fields:
            assert hasattr(settings, field), f"Settings missing field: {field}"

    def test_cors_origins_list_property(self):
        from config import Settings
        s = Settings(cors_origins="http://localhost:3000,http://localhost:5173")
        origins = s.cors_origins_list
        assert "http://localhost:3000" in origins
        assert "http://localhost:5173" in origins

    def test_no_raw_getenv_outside_config(self):
        """No module other than config.py may call os.getenv directly."""
        backend = pathlib.Path("backend")
        violations = []
        skip = {"venv", "__pycache__", "tests", "scripts"}
        for p in sorted(backend.rglob("*.py")):
            if any(s in p.parts for s in skip):
                continue
            if p.name == "config.py":
                continue
            try:
                src = p.read_text()
                tree = ast.parse(src)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if (
                            isinstance(node.func, ast.Attribute)
                            and node.func.attr == "getenv"
                            and isinstance(node.func.value, ast.Name)
                            and node.func.value.id == "os"
                        ):
                            violations.append(str(p))
                            break
            except Exception:
                pass
        assert violations == [], (
            f"Raw os.getenv found in non-config files: {violations}\n"
            "Move these to config.py Settings and access via `from config import settings`."
        )
```

- [ ] **Step 2: Run to confirm it fails**

```bash
pytest backend/tests/unit/test_settings.py -v 2>&1 | head -20
```

Expected: `ImportError: cannot import name 'Settings' from 'config'`.

- [ ] **Step 3: Add `pydantic-settings` to `requirements.txt`**

```bash
echo "pydantic-settings>=2.0.0" >> backend/requirements.txt
pip install -r backend/requirements.txt
```

- [ ] **Step 4: Replace `config.py` with the new implementation**

Rewrite `backend/config.py` entirely:

```python
"""
config.py
─────────
Single source of truth for all environment-sourced configuration.

All modules should import the `settings` singleton:

    from config import settings
    url = settings.influx_url

No module other than this file may call os.getenv() directly.
Backward-compatible getter functions are provided for callers that
haven't been migrated yet — they delegate to `settings`.
"""

import logging
from pathlib import Path
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.logger import get_logger

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """
    All WACH Insight configuration, sourced from environment variables
    and .env files. Field names map to uppercased env var names
    (e.g. `influx_url` → `INFLUX_URL`).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── InfluxDB ──────────────────────────────────────────────────────────────
    influx_url: str = "http://localhost:8086"
    influx_token: str = ""
    influx_org: str = "wach"
    influx_bucket: str = "wach_bucket_3"
    influx_skip_tls: bool = False

    # ── LLM (LM Studio / Qwen) ───────────────────────────────────────────────
    lms_base_url: str = "http://localhost:1234/v1"
    lms_model: str = "qwen/qwen3-8b"
    lms_api_key: str = "lm-studio"
    lms_timeout: float = 60.0
    enable_llm: bool = False

    # ── RAG / Vector store ────────────────────────────────────────────────────
    chroma_persist_dir: str = "data/chroma"
    rag_collection: str = "wach_docs"
    ward_config_path: Optional[str] = None

    # ── Auth & Security ───────────────────────────────────────────────────────
    api_key: Optional[str] = None
    dev_api_key: str = "dev-key-change-in-production"
    cors_origins: str = "http://localhost:3000"

    # ── Application ───────────────────────────────────────────────────────────
    app_env: str = "development"
    debug: bool = False
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # ── Observability ─────────────────────────────────────────────────────────
    alert_webhook_url: str = ""

    # ── Building identity ─────────────────────────────────────────────────────
    wach_building_name: str = "Healthcare Facility"
    wach_department: str = "Department"
    hospital_id: str = "wach"

    # ── Debug flags ───────────────────────────────────────────────────────────
    csv_debug: bool = False

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list (splits the comma-separated string)."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def effective_api_key(self) -> str:
        """Return the active API key, preferring API_KEY over DEV_API_KEY."""
        key = self.api_key or self.dev_api_key
        if not key:
            raise RuntimeError(
                "API_KEY environment variable is required. "
                "Set it in your .env file before starting the server."
            )
        return key

    @model_validator(mode="after")
    def warn_on_insecure_influx(self) -> "Settings":
        """Warn (not crash) if InfluxDB uses plain HTTP on a non-localhost host."""
        url = self.influx_url
        is_local = url.startswith("http://localhost") or url.startswith("http://127.0.0.1")
        if not is_local and not self.influx_skip_tls and url.startswith("http://"):
            logger.warning(
                "INFLUX_URL uses plain HTTP on a non-localhost host. "
                "Set INFLUX_SKIP_TLS=true to suppress this warning, "
                "or switch to HTTPS for production.",
                extra={"influx_url": url},
            )
        return self

    # ── Data paths (derived from BASE_DIR) ───────────────────────────────────

    @property
    def data_dir(self) -> Path:
        """Absolute path to the backend data directory."""
        return BASE_DIR / "data"

    @property
    def exports_dir(self) -> Path:
        """Absolute path to the backend exports directory."""
        return BASE_DIR / "exports"


# ── Module-level singleton ────────────────────────────────────────────────────
# Import this in other modules: `from config import settings`
settings = Settings()

# Ensure runtime directories exist
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.exports_dir.mkdir(parents=True, exist_ok=True)


# ── Backward-compatible getters ───────────────────────────────────────────────
# These exist so callers written before this refactor still work.
# New code should use `settings.field_name` directly.

def get_influx_url() -> str:
    return settings.influx_url

def get_influx_token() -> str:
    if not settings.influx_token:
        raise ValueError(
            "INFLUX_TOKEN environment variable is required. "
            "Set to a valid InfluxDB API token with read access."
        )
    return settings.influx_token

def get_influx_org() -> str:
    return settings.influx_org

def get_influx_bucket() -> str:
    return settings.influx_bucket

def get_influx_skip_tls() -> bool:
    return settings.influx_skip_tls

def get_lms_base_url() -> str:
    return settings.lms_base_url

def get_lms_model() -> str:
    return settings.lms_model

def get_lms_api_key() -> str:
    return settings.lms_api_key

def get_building_name() -> str:
    return settings.wach_building_name

def get_hospital_id() -> str:
    return settings.hospital_id

def get_department() -> str:
    return settings.wach_department

def get_app_env() -> str:
    return settings.app_env

def get_cors_origins() -> list[str]:
    return settings.cors_origins_list

def get_debug_mode() -> bool:
    return settings.debug

def get_rate_limit_requests() -> int:
    return settings.rate_limit_requests

def get_rate_limit_window() -> int:
    return settings.rate_limit_window

def get_data_dir() -> Path:
    return settings.data_dir

def get_exports_dir() -> Path:
    return settings.exports_dir
```

- [ ] **Step 5: Run tests**

```bash
pytest backend/tests/unit/test_settings.py::TestSettingsModel::test_settings_importable -v
pytest backend/tests/unit/test_settings.py::TestSettingsModel::test_required_fields_exist -v
pytest backend/tests/ -x -q 2>&1 | tail -10
```

Expected: first two pass. Full suite should not regress (backward-compat getters still work). `test_no_raw_getenv_outside_config` will fail — that's expected; it passes after Task 2.

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/config.py backend/tests/unit/test_settings.py
git commit -m "feat(config): replace os.getenv getters with pydantic-settings Settings model"
```

---

## Task 2: Migrate raw `os.getenv` calls to `settings.*`

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/routes/forecast.py`
- Modify: `backend/llm/translator.py`
- Modify: `backend/llm/qwen_client.py`
- Modify: `backend/llm/prompts.py`
- Modify: `backend/core/csv_reader.py`
- Modify: `backend/tools/health_tools.py`

For each file: remove `os.getenv(...)` call(s), add `from config import settings` if not already imported, reference `settings.<field>` instead.

- [ ] **Step 1: Migrate `backend/main.py`**

Find and replace these patterns in `main.py`:

| Remove | Replace with |
|--------|-------------|
| `RATE_LIMIT = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))` | `RATE_LIMIT = settings.rate_limit_requests` |
| `RATE_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))` | `RATE_WINDOW = settings.rate_limit_window` |
| `api_key = os.getenv("API_KEY") or os.getenv("DEV_API_KEY")` | `api_key = settings.api_key or settings.dev_api_key` |
| `raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")` | `return settings.cors_origins_list` |
| `os.getenv("ALERT_WEBHOOK_URL", "")` | `settings.alert_webhook_url` |

Add at the top of `main.py` with other imports: `from config import settings`

Remove `import os` only if no other `os.*` usage remains in the file (check `os.path`, `os.getenv`, `os.listdir`, etc. before removing).

- [ ] **Step 2: Migrate `backend/routes/forecast.py`**

Replace at module level (lines 52–55):
```python
_URL    = os.getenv("INFLUX_URL")
_TOKEN  = os.getenv("INFLUX_TOKEN")
_ORG    = os.getenv("INFLUX_ORG")
_BUCKET = os.getenv("INFLUX_BUCKET")
```

With:
```python
from config import settings
_URL    = settings.influx_url
_TOKEN  = settings.influx_token
_ORG    = settings.influx_org
_BUCKET = settings.influx_bucket
```

Also remove the duplicate `logging.basicConfig` block (lines 31–36) that was missed in Phase 3:
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)
```

Replace with (if not already at top of file):
```python
from core.logger import get_logger
logger = get_logger(__name__)
```

- [ ] **Step 3: Migrate `backend/llm/translator.py`**

Replace:
```python
LLM_ENABLED = os.getenv("ENABLE_LLM", "false").lower() == "true"
```
With:
```python
from config import settings
LLM_ENABLED = settings.enable_llm
```

Remove `import os` from `translator.py` if no other `os.*` usage.

- [ ] **Step 4: Migrate `backend/llm/qwen_client.py`**

Find (approximately line 35):
```python
timeout = float(os.getenv("LMS_TIMEOUT", "60.0"))
```
Replace with:
```python
from config import settings
timeout = settings.lms_timeout
```

- [ ] **Step 5: Migrate `backend/llm/prompts.py`**

Find (approximately line 497):
```python
custom_path = os.getenv("WARD_CONFIG_PATH")
```
Replace with:
```python
from config import settings
custom_path = settings.ward_config_path
```

- [ ] **Step 6: Migrate `backend/core/csv_reader.py`**

Find:
```python
DEBUG_MODE = os.getenv('CSV_DEBUG', 'false').lower() == 'true'
```
Replace with:
```python
from config import settings
DEBUG_MODE = settings.csv_debug
```

- [ ] **Step 7: Migrate `backend/tools/health_tools.py`**

Find (approximately lines 41–42):
```python
chroma_dir = os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
collection = os.getenv("RAG_COLLECTION", "wach_docs")
```
Replace with:
```python
from config import settings
chroma_dir = settings.chroma_persist_dir
collection = settings.rag_collection
```

- [ ] **Step 8: Run the full test suite to confirm no regression**

```bash
pytest backend/tests/ -x -q 2>&1 | tail -15
```

Expected: all tests pass.

- [ ] **Step 9: Run the no-raw-getenv test**

```bash
pytest backend/tests/unit/test_settings.py::TestSettingsModel::test_no_raw_getenv_outside_config -v
```

Expected: `PASSED`.

- [ ] **Step 10: Commit**

```bash
git add backend/main.py backend/routes/forecast.py backend/llm/translator.py \
        backend/llm/qwen_client.py backend/llm/prompts.py \
        backend/core/csv_reader.py backend/tools/health_tools.py
git commit -m "refactor(config): migrate all raw os.getenv calls to settings.* singleton"
```

---

## Task 3: Remove dead code

**Files:**
- Delete: `backend/routes/update_level_endpoint.py`
- Modify: `backend/main.py` (remove `sys.path.insert`)

- [ ] **Step 1: Confirm `update_level_endpoint.py` is not imported anywhere**

```bash
grep -r "update_level_endpoint\|update_level" /Users/rdmasia/wach-insight/backend \
    --include="*.py" | grep -v "__pycache__\|venv\|update_level_endpoint.py"
```

Expected: no output. If any output appears, **do not delete** — investigate the caller first.

- [ ] **Step 2: Delete `backend/routes/update_level_endpoint.py`**

```bash
git rm backend/routes/update_level_endpoint.py
```

- [ ] **Step 3: Remove the redundant `sys.path.insert` from `main.py`**

Find and remove this line from `main.py:26`:
```python
sys.path.insert(0, os.path.dirname(__file__))
```

This is redundant because `pyproject.toml` has `pythonpath = ["."]` which adds the repo root to sys.path when running pytest, and gunicorn/uvicorn is invoked from `backend/` in `start.sh` so the directory is already in scope.

- [ ] **Step 4: Verify the app still boots after removing sys.path.insert**

```bash
cd backend && python -c "from main import app; print('app boots ok')"
```

Expected: `app boots ok` with no import errors.

- [ ] **Step 5: Run the test suite**

```bash
pytest backend/tests/ -x -q 2>&1 | tail -10
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/main.py
git commit -m "chore(cleanup): delete update_level_endpoint.py script and remove redundant sys.path.insert"
```

---

## Task 4: Add missing module docstrings

**Files:**
- Modify: `backend/models/schemas.py`
- Modify: `backend/rag/__init__.py`
- Modify: `backend/routes/__init__.py`
- Modify: `backend/tools/__init__.py`

All other production modules already have docstrings. Only these 4 are missing.

- [ ] **Step 1: Add docstring to `backend/models/schemas.py`**

Insert at the very top of the file (before the existing `from pydantic import ...` line):

```python
"""
models/schemas.py
─────────────────
Pydantic models and allowlist constants for the WACH Insight API.

Exposes:
  StructuredQuery — the parsed representation of a user's NL query
  ALLOWED_METRICS, ALLOWED_DEVICES, ALLOWED_TIME_RANGES — InfluxDB allowlists
  QueryType — enum of supported query categories
  ChatHistoryItem — a single turn in the conversation history
"""
```

- [ ] **Step 2: Add docstrings to the three `__init__.py` files**

`backend/rag/__init__.py`:
```python
"""RAG (Retrieval-Augmented Generation) package for WACH Insight document retrieval."""
```

`backend/routes/__init__.py`:
```python
"""FastAPI route modules for all WACH Insight API endpoints."""
```

`backend/tools/__init__.py`:
```python
"""Agentic tool definitions and registry for the WACH Insight chat pipeline."""
```

- [ ] **Step 3: Verify the audit script now reports zero missing docstrings**

```bash
python3 -c "
import ast, pathlib
skip = {'venv', '__pycache__', 'tests', 'scripts'}
missing = []
for p in sorted(pathlib.Path('backend').rglob('*.py')):
    if any(s in p.parts for s in skip): continue
    try:
        if not ast.get_docstring(ast.parse(p.read_text())):
            missing.append(str(p))
    except: pass
print('Missing docstrings:', missing or 'none')
"
```

Expected: `Missing docstrings: none`

- [ ] **Step 4: Commit**

```bash
git add backend/models/schemas.py backend/rag/__init__.py \
        backend/routes/__init__.py backend/tools/__init__.py
git commit -m "docs(modules): add missing docstrings to schemas.py and __init__ files"
```

---

## Task 5: Add missing type hints to public functions

**Files:**
- Modify: `backend/config.py` (2 getters)
- Modify: `backend/llm/client_factory.py` (1 function)
- Modify: `backend/routes/chat.py` (route handler)
- Modify: `backend/routes/health_scores.py` (4 route handlers)
- Modify: `backend/routes/query.py` (route handler)
- Modify: `backend/main.py` (helper functions)

The spec says private helpers are lower priority. Focus on the public API boundary: route handlers and exported functions from `config.py` and `llm/`.

- [ ] **Step 1: Annotate `backend/config.py` getter functions**

The two untyped public functions are `load_env_files()` and `init_config()`. Since these are now stubs/removed, ensure the new config.py's `get_*` functions all have return annotations. Verify each getter has `-> str`, `-> bool`, `-> int`, `-> list[str]`, or `-> Path` as appropriate. The Settings class itself is already fully typed via pydantic.

- [ ] **Step 2: Annotate `backend/llm/client_factory.py`**

Find:
```python
def get_chat_client():
    """Return the configured LLM client instance."""
    return QwenClient()
```

Replace with:
```python
def get_chat_client() -> "QwenClient":
    """Return the configured LLM client instance."""
    return QwenClient()
```

Add `from __future__ import annotations` at the top if not present (avoids circular import for the string annotation).

- [ ] **Step 3: Annotate route handlers in `backend/routes/chat.py`**

Find the chat route handler signature. It will look like:
```python
async def chat(body: ChatRequest, request: Request):
```

Add return type:
```python
async def chat(body: ChatRequest, request: Request) -> dict:
```

- [ ] **Step 4: Annotate route handlers in `backend/routes/health_scores.py`**

All four route handlers are missing return types. Add `-> dict` or `-> list` as appropriate based on what each returns:

```python
async def get_levels() -> dict:
async def get_level_scores(level: int, ...) -> dict:
async def get_level_health_index(level: int, ...) -> dict:
async def get_raw_score_relationship(device_id: str, ...) -> dict:
```

- [ ] **Step 5: Annotate `handle_query` in `backend/routes/query.py`**

Find:
```python
async def handle_query(request: Request, body: QueryRequest):
```

Replace with:
```python
async def handle_query(request: Request, body: QueryRequest) -> dict:
```

- [ ] **Step 6: Annotate helpers in `backend/main.py`**

```python
def get_cors_origins() -> list[str]:
def create_app() -> FastAPI:
async def health() -> dict:
```

The `dispatch` methods on middleware classes take `call_next` — annotate with the Starlette type:

```python
from starlette.types import ASGIApp
# In dispatch methods:
async def dispatch(self, request: Request, call_next: Callable) -> Response:
```

Add `from typing import Callable` at the top if not present.

- [ ] **Step 7: Run tests to confirm nothing broke**

```bash
pytest backend/tests/ -x -q 2>&1 | tail -10
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add backend/config.py backend/llm/client_factory.py backend/routes/chat.py \
        backend/routes/health_scores.py backend/routes/query.py backend/main.py
git commit -m "feat(types): add return type hints to public functions and route handlers"
```

---

## Task 6: Frontend hygiene — remove console statements + add JSDoc to store

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/dashboard/derivation/ScoreCardWithSelector.tsx`
- Modify: `frontend/src/store/useAppStore.ts`

- [ ] **Step 1: Audit all console statements**

```bash
grep -rn "console\." frontend/src --include="*.tsx" --include="*.ts" \
    | grep -v "__tests__\|node_modules"
```

Expected output (current state):
```
frontend/src/App.tsx:104:    console.log('[App] Fetching site summary data with range:', range);
frontend/src/App.tsx:107:        console.log('[App] Site summary data received:', data);
frontend/src/App.tsx:111:        console.error('[App] Failed to load site summary:', err);
frontend/src/components/dashboard/derivation/ScoreCardWithSelector.tsx:44:      .catch(console.error)
frontend/src/api/client.ts:33:    console.error(`[API] Error fetching ${url}:`, error);
```

- [ ] **Step 2: Remove console statements from `App.tsx`**

In `App.tsx`, find the function that contains those three console calls (around line 104–111). Remove all three lines:

```tsx
// DELETE these lines:
console.log('[App] Fetching site summary data with range:', range);
console.log('[App] Site summary data received:', data);
console.error('[App] Failed to load site summary:', err);
```

The surrounding `try/catch` block should still function — just remove the console calls, not the error handling logic itself.

- [ ] **Step 3: Remove console.error from `api/client.ts`**

Find (approximately line 33):
```typescript
console.error(`[API] Error fetching ${url}:`, error);
```

Remove this line. The error is already being re-thrown (or handled by the caller) — the console.error is redundant in production.

- [ ] **Step 4: Fix `.catch(console.error)` in `ScoreCardWithSelector.tsx`**

Find (approximately line 44):
```typescript
.catch(console.error)
```

Replace with a no-op catch to maintain the promise chain without logging:
```typescript
.catch(() => {})
```

- [ ] **Step 5: Verify no console statements remain**

```bash
grep -rn "console\." frontend/src --include="*.tsx" --include="*.ts" \
    | grep -v "__tests__\|node_modules"
```

Expected: no output.

- [ ] **Step 6: Add JSDoc to all Zustand store actions in `useAppStore.ts`**

Open `frontend/src/store/useAppStore.ts`. For each action in the `create<AppStore>()` call, add a JSDoc comment above it. Here is the complete annotated version of the actions block (replace the existing uncommented actions):

```typescript
export const useAppStore = create<AppStore>((set) => ({
  ...initialState,

  /** Current time range for all dashboard queries. Defaults to 7 days. */
  timeRange: '7d',
  /** Update the active time range. Triggers data refetch in subscribed components. */
  setTimeRange: (range) => set({ timeRange: range }),

  /** Select a floor level (1–11). Clears any active device selection. */
  selectLevel: (level) => set({ selectedLevel: level, selectedDevice: null }),
  /** Clear the active level selection and any device selection. */
  clearLevel: () => set({ selectedLevel: null, selectedDevice: null }),

  /** Select a specific AHU device by ID (e.g. "e0101"). */
  selectDevice: (deviceId) => set({ selectedDevice: deviceId }),

  /** Toggle the chat panel open/closed. */
  toggleChat: () => set((state) => ({ chatOpen: !state.chatOpen })),
  /** Open the chat panel. */
  openChat: () => set({ chatOpen: true }),
  /** Close the chat panel. */
  closeChat: () => set({ chatOpen: false }),

  /** Append a new message to the chat history. */
  addMessage: (message) => set((state) => ({
    chatMessages: [...state.chatMessages, message],
  })),
  /** Replace the entire chat history (used on reset). */
  setMessages: (messages) => set({ chatMessages: messages }),

  /** Replace the current dashboard data (null clears the dashboard). */
  setDashboardData: (data) => set({ dashboardData: data }),

  /** Set the global loading state (shows skeleton loaders when true). */
  setLoading: (loading) => set({ isLoading: loading }),

  /** Store financial impact data returned by the /api/financial-impact endpoint. */
  financialImpact: null,
  /** Update stored financial impact data. Pass null to clear. */
  setFinancialImpact: (data) => set({ financialImpact: data }),

  /** Whether the hamburger navigation menu is open. */
  hamburgerOpen: false,
  /** Toggle the hamburger navigation menu. */
  toggleHamburger: () => set((state) => ({ hamburgerOpen: !state.hamburgerOpen })),

  /** Cached site-wide summary data from /api/site-summary. */
  siteSummaryData: null,
  /** Update the cached site summary data. */
  setSiteSummaryData: (d) => set({ siteSummaryData: d }),

  /** Whether the hero section is currently visible (used for scroll animations). */
  setHeroVisible: (visible) => set({ heroVisible: visible }),
}));
```

- [ ] **Step 7: Run frontend tests to confirm nothing broke**

```bash
cd frontend && npm test -- --watchAll=false 2>&1 | tail -15
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/App.tsx frontend/src/api/client.ts \
        "frontend/src/components/dashboard/derivation/ScoreCardWithSelector.tsx" \
        frontend/src/store/useAppStore.ts
git commit -m "chore(frontend): remove console statements and add JSDoc to Zustand store actions"
```

---

## Task 7: Add ruff — configure, fix violations, add CI gate

**Files:**
- Modify: `backend/requirements-dev.txt`
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml`

`ruff` is a fast Python linter and formatter. Run it in check mode in CI so it fails the build without auto-committing changes.

- [ ] **Step 1: Add ruff to dev dependencies**

Add to `backend/requirements-dev.txt`:
```
ruff>=0.4.0
```

Install:
```bash
pip install -r backend/requirements-dev.txt
```

- [ ] **Step 2: Add `[tool.ruff]` config to `pyproject.toml`**

Append to `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes (unused imports, undefined names)
    "I",    # isort
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
]
ignore = [
    "E501",  # line too long — handled by formatter
    "B008",  # do not perform function calls in default args (FastAPI dependency injection)
    "UP007", # use X | Y for union types — keep Optional[] for Python 3.9 compat
]

[tool.ruff.lint.per-file-ignores]
"backend/tests/*" = ["F401", "F811"]  # allow unused imports in tests
```

- [ ] **Step 3: Run ruff to see current violations**

```bash
ruff check backend/ 2>&1 | head -40
```

Review the output. Expected violations include: unused imports (`F401`), import sorting (`I001`), some style issues.

- [ ] **Step 4: Auto-fix safe violations**

```bash
ruff check backend/ --fix --select E,W,F,I,UP
```

This fixes safe violations (import sorting, unused imports, pyupgrade) without changing logic. Review the diff before committing.

- [ ] **Step 5: Run again to see only unfixed violations**

```bash
ruff check backend/ 2>&1 | head -30
```

Manually fix any remaining `B` (bugbear) violations if they are genuine bugs. Skip any `E501` (line length) violations — those are ignored per config.

- [ ] **Step 6: Verify test suite still passes after auto-fix**

```bash
pytest backend/tests/ -x -q 2>&1 | tail -10
```

Expected: all tests pass. If any test breaks, the auto-fix changed logic — revert that specific file and fix manually.

- [ ] **Step 7: Add ruff step to `.github/workflows/ci.yml`**

**If `ci.yml` doesn't exist yet** (Phase 1 not executed), create it:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install -r backend/requirements-dev.txt
      - run: pytest backend/tests/ -x
      - run: ruff check backend/

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "18"
      - run: npm ci
        working-directory: frontend
      - run: npm run build
        working-directory: frontend
      - run: npm test -- --watchAll=false
        working-directory: frontend
```

**If `ci.yml` already exists**, add a `ruff check backend/` step after the existing `pytest` step in the backend job:

```yaml
      - name: Lint with ruff
        run: ruff check backend/
```

- [ ] **Step 8: Commit**

```bash
git add backend/requirements-dev.txt pyproject.toml .github/workflows/ci.yml
git add -u backend/  # stage any files ruff auto-fixed
git commit -m "ci(lint): add ruff check gate to CI; fix existing violations"
```

---

## Task 8: Add prettier — install, configure, add CI gate

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/.prettierrc`
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Install prettier as a devDependency**

```bash
cd frontend && npm install --save-dev prettier@3
```

- [ ] **Step 2: Create `frontend/.prettierrc`**

```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100,
  "arrowParens": "always"
}
```

- [ ] **Step 3: Run prettier in check mode to see current violations**

```bash
cd frontend && npx prettier --check "src/**/*.{ts,tsx}" 2>&1 | head -20
```

Review the output. Expected: some formatting differences.

- [ ] **Step 4: Run prettier to auto-format**

```bash
cd frontend && npx prettier --write "src/**/*.{ts,tsx}"
```

- [ ] **Step 5: Run tests to confirm auto-format didn't break anything**

```bash
cd frontend && npm test -- --watchAll=false 2>&1 | tail -10
```

Expected: all tests pass.

- [ ] **Step 6: Run prettier check — should now pass**

```bash
cd frontend && npx prettier --check "src/**/*.{ts,tsx}"
```

Expected: `All matched files use Prettier code style!`

- [ ] **Step 7: Add `prettier --check` script to `package.json`**

In `frontend/package.json`, add to the `"scripts"` block:
```json
"lint:format": "prettier --check \"src/**/*.{ts,tsx}\""
```

- [ ] **Step 8: Add prettier check to `.github/workflows/ci.yml`**

In the frontend job, after the existing `npm run build` step, add:

```yaml
      - name: Check formatting with prettier
        run: npm run lint:format
        working-directory: frontend
```

- [ ] **Step 9: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/.prettierrc \
        .github/workflows/ci.yml
git add -u frontend/src/  # stage any files prettier reformatted
git commit -m "ci(format): add prettier check gate to CI; format all TS/TSX files"
```

---

## Task 9: Add mypy as a warning-only CI gate

**Files:**
- Modify: `backend/requirements-dev.txt`
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml`

Mypy runs in strict mode but as a **warning** — it does not fail the build initially. The intent is to surface the backlog and make it visible. It graduates to a blocker once the backlog is clear.

- [ ] **Step 1: Add mypy to dev dependencies**

Add to `backend/requirements-dev.txt`:
```
mypy>=1.10.0
```

Install:
```bash
pip install -r backend/requirements-dev.txt
```

- [ ] **Step 2: Add `[tool.mypy]` config to `pyproject.toml`**

```toml
[tool.mypy]
python_version = "3.10"
strict = true
ignore_missing_imports = true
exclude = [
    "backend/venv/",
    "backend/tests/",
    "backend/scripts/",
]
```

- [ ] **Step 3: Run mypy and review the output**

```bash
mypy backend/ 2>&1 | tail -20
```

Note the error count. This is the baseline that the warning gate will surface in CI.

- [ ] **Step 4: Add mypy step to `.github/workflows/ci.yml` (warning only)**

In the backend job, after the `ruff check` step, add:

```yaml
      - name: Type-check with mypy (warning only)
        run: mypy backend/ || true
        continue-on-error: true
```

The `|| true` and `continue-on-error: true` together ensure a mypy failure never blocks the build. The errors are visible in the CI log but do not fail the job.

- [ ] **Step 5: Commit**

```bash
git add backend/requirements-dev.txt pyproject.toml .github/workflows/ci.yml
git commit -m "ci(types): add mypy warning gate to CI — errors visible but non-blocking"
```

---

## Self-Review

### Spec coverage check

| Spec requirement | Task |
|---|---|
| Module-level docstrings — every Python file | Task 4 (4 files were missing; all others already have them) |
| Type hints — all public function signatures | Task 5 |
| `mypy --strict` to CI as warning | Task 9 |
| Remove `routes/update_level_endpoint.py` | Task 3 |
| Clean up `sys.path.insert` in `main.py` | Task 3 |
| Confirm debug scripts not imported | Task 3 Step 1 (grep confirms) |
| All `os.getenv` → `config.py` as `Settings` | Tasks 1 + 2 |
| `pydantic-settings` `Settings` model | Task 1 |
| No raw `os.getenv` outside `config.py` | Task 2 (enforced by unit test) |
| Audit `console.log` in frontend | Task 6 |
| Add JSDoc to Zustand store actions | Task 6 |
| `ruff check backend/` to CI (check mode) | Task 7 |
| `prettier --check frontend/src/` to CI | Task 8 |

### Placeholder scan

No TBD/TODO/placeholder markers found. Task 5 Step 1 mentions verifying return annotations — the instruction is explicit (check that each getter has the right return annotation), not deferred.

### Type consistency

- `settings: Settings` singleton imported as `from config import settings` — used consistently in Tasks 1 and 2.
- `Settings.cors_origins_list` is a `@property` returning `list[str]` — matches the `get_cors_origins() -> list[str]` getter in Task 5.
- `alert_webhook_url` is `str` (empty default) in Settings — matches `os.getenv("ALERT_WEBHOOK_URL", "")` it replaces in `main.py`.
