# Fix ETL InfluxDB Connection After Security Changes

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore `python3 scripts/etl/run_health_etl.py --output-hourly` successfully connecting to InfluxDB after the security hardening changed the HTTPS requirements and `.env` structure.

**Architecture:** The bug is almost certainly that `load_dotenv()` in `config.py` does NOT override existing shell environment variables, so if `INFLUX_URL=http://127.0.0.1:8086` is set in the shell (old value), it silently wins over the `.env` file (new `https://` value). Secondary risk: if InfluxDB on `178.128.53.199` runs plain HTTP, we need `verify_ssl=False` or an SSH tunnel. The fix targets `backend/config.py` (add `override=True` to `load_dotenv`) and `backend/core/influx_client.py` (pass `verify_ssl=False` for self-signed / IP-based certs).

**Tech Stack:** Python 3, `influxdb-client`, `python-dotenv`, FastAPI, InfluxDB v2 at `178.128.53.199:8086`

---

## Chunk 1: Diagnose root cause

### Task 1: Confirm which INFLUX_URL is actually being used at runtime

**Files:**
- Read-only: `backend/config.py`, `backend/core/influx_client.py`, `.env`, `backend/.env`

- [ ] **Step 1: Check if shell has INFLUX_URL set**

Run in terminal (project root):
```bash
echo "Shell INFLUX_URL: $INFLUX_URL"
```
Expected (the bug): `Shell INFLUX_URL: http://127.0.0.1:8086`
If blank → the bug is SSL, not env override.

- [ ] **Step 2: Check if InfluxDB is reachable on the remote server**

```bash
curl -v http://178.128.53.199:8086/ping 2>&1 | head -20
curl -v https://178.128.53.199:8086/ping 2>&1 | head -20
```

Expected results:
- If HTTP works: InfluxDB runs plain HTTP → we need to allow HTTP (or use SSH tunnel) + fix the env override
- If HTTPS works: SSL is configured → only the env override is the bug
- If both fail: server is down or port is firewalled → different fix needed

- [ ] **Step 3: Print the URL the ETL actually uses**

```bash
cd /Users/rdmasia/wach-insight
python3 -c "
import sys, os
sys.path.insert(0, 'backend')
import config  # triggers load_env_files
print('INFLUX_URL in env:', os.environ.get('INFLUX_URL', '<NOT SET>'))
from config import get_influx_url
try:
    print('get_influx_url():', get_influx_url())
except Exception as e:
    print('get_influx_url() raised:', e)
"
```

Expected: This will confirm whether the shell env var is winning.

---

## Chunk 2: Fix env-var override (primary fix)

### Task 2: Make `load_dotenv` override existing shell env vars

**Files:**
- Modify: `backend/config.py:33` (both `load_dotenv` calls)

**Why this matters:** `python-dotenv`'s `load_dotenv()` skips variables already present in the process environment. The old `INFLUX_URL=http://127.0.0.1:8086` set in the shell (or a previous config) silently takes precedence over the `.env` file.

- [ ] **Step 1: Verify the bug by reading current load_dotenv calls**

In `backend/config.py` line ~33:
```python
load_dotenv(env_path)
```
No `override=True` → shell env wins. Confirm this is the case.

- [ ] **Step 2: Edit `backend/config.py` to add `override=True`**

Find this block in `backend/config.py`:
```python
    for env_path in env_locations:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"[config] Loaded environment from {env_path}")
```

Change to:
```python
    for env_path in env_locations:
        if env_path.exists():
            load_dotenv(env_path, override=True)
            print(f"[config] Loaded environment from {env_path}")
```

- [ ] **Step 3: Verify fix with the same diagnostic**

```bash
cd /Users/rdmasia/wach-insight
python3 -c "
import sys, os
os.environ['INFLUX_URL'] = 'http://127.0.0.1:8086'  # Simulate stale shell var
sys.path.insert(0, 'backend')
import config
from config import get_influx_url
try:
    print('URL after override=True:', get_influx_url())
except Exception as e:
    print('ERROR:', e)
"
```

Expected: should print the URL from `.env` (`https://178.128.53.199:8086`), not `http://127.0.0.1:8086`.

---

## Chunk 3: Fix SSL/HTTPS connection to InfluxDB

### Task 3: Handle HTTPS to IP address (self-signed cert)

**Files:**
- Modify: `backend/core/influx_client.py:63` (`_get_client` function)

**Why:** If InfluxDB at `178.128.53.199:8086` uses HTTPS with a self-signed cert (common for internal servers), the Python `influxdb-client` will reject it unless `verify_ssl=False`. If InfluxDB runs plain HTTP on `178.128.53.199`, we need a different approach (see Task 4).

This step only applies if `curl -v https://178.128.53.199:8086/ping` from Task 1 Step 2 returned a response (even an error), confirming HTTPS is configured.

- [ ] **Step 1: Check what `curl -v https://` returned (from Chunk 1 Task 1 Step 2)**

- If SSL error like `SSL certificate problem: self-signed certificate` → apply Task 3 fix
- If `Connection refused` on HTTPS but HTTP works → skip to Task 4

- [ ] **Step 2: Edit `_get_client()` in `backend/core/influx_client.py`**

Find:
```python
def _get_client() -> InfluxDBClient:
    return InfluxDBClient(url=_URL, token=_TOKEN, org=_ORG, timeout=18_000_000)
```

Change to:
```python
def _get_client() -> InfluxDBClient:
    # verify_ssl=False is required when InfluxDB uses a self-signed certificate
    # (common for IP-based HTTPS endpoints on internal servers)
    use_verify_ssl = _URL.startswith("https://localhost") or _URL.startswith("https://127.0.0.1")
    return InfluxDBClient(url=_URL, token=_TOKEN, org=_ORG, timeout=18_000_000, verify_ssl=use_verify_ssl)
```

This disables SSL verification only for non-localhost HTTPS (which typically means self-signed cert). Localhost HTTPS is left alone.

- [ ] **Step 3: Suppress the urllib3 SSL warning that will appear**

At the top of `backend/core/influx_client.py`, after `import warnings`:
```python
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

---

## Chunk 4: Handle plain-HTTP InfluxDB on remote server (if HTTPS fails)

> **Only do this task if curl https:// gave `Connection refused` but curl http:// worked.**

### Task 4: Allow HTTP for the specific remote IP via SSH tunnel approach

**Files:**
- No code changes — operational fix only

**Context:** The security hardening in `backend/config.py` correctly rejects `http://178.128.53.199:8086` (non-localhost HTTP). The right solution is NOT to weaken that check, but to either:
1. Set up HTTPS on the InfluxDB server (recommended long-term)
2. Use an SSH local port forward to make remote HTTP appear as localhost

- [ ] **Step 1: Open SSH tunnel in a background terminal**

```bash
ssh -L 8086:127.0.0.1:8086 user@178.128.53.199 -N -f
```
Replace `user` with the actual SSH username for the server.

This forwards `localhost:8086` → `178.128.53.199's localhost:8086`.

- [ ] **Step 2: Update `.env` to use the tunnel URL**

In both `.env` and `backend/.env`, change:
```
INFLUX_URL=https://178.128.53.199:8086
```
To:
```
INFLUX_URL=http://127.0.0.1:8086
```

This satisfies the security validator (localhost HTTP is allowed) while actually connecting through the SSH tunnel to the remote server.

---

## Chunk 5: End-to-end test

### Task 5: Run ETL and confirm success

**Files:**
- None (test only)

- [ ] **Step 1: Run ETL in dry-run mode first**

```bash
cd /Users/rdmasia/wach-insight
python3 scripts/etl/run_health_etl.py --dry-run --level 1
```

Expected output:
```
[config] Loaded environment from .../backend/.env
[config] Loaded environment from .../.env
[influx_client] Fetching latest data for Level 1 (22 AHUs)...
[OK] Retrieved XX AHU readings
...
[DRY RUN] Skipping file write
```

No `Connection refused` errors, no `[ERROR] No data retrieved from InfluxDB!`.

- [ ] **Step 2: Run full ETL with hourly output**

```bash
python3 scripts/etl/run_health_etl.py --output-hourly
```

Expected: Pipeline completes successfully with rows loaded.

- [ ] **Step 3: Verify output files exist and have content**

```bash
wc -l data/health_all_levels.csv data/health_hourly.csv
```

Expected: non-zero row counts in both files.

- [ ] **Step 4: Commit the fix**

```bash
git add backend/config.py backend/core/influx_client.py
git commit -m "fix: restore InfluxDB connection after security hardening

- load_dotenv now uses override=True so .env values win over stale shell env vars
- influx_client skips SSL verification for remote HTTPS endpoints using self-signed certs
- suppress urllib3 InsecureRequestWarning for non-localhost HTTPS"
```
