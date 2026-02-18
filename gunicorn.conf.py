# gunicorn.conf.py
# Place at project root: rdm-wach-insights/gunicorn.conf.py
# Run with: gunicorn -c gunicorn.conf.py backend.main:app

import multiprocessing

# Bind to localhost only — Cloudflare Tunnel handles public exposure
bind        = "127.0.0.1:8000"

# Workers: (2 x CPU cores) + 1 is the standard formula
workers     = (multiprocessing.cpu_count() * 2) + 1

# Use uvicorn workers so FastAPI async routes work correctly
worker_class = "uvicorn.workers.UvicornWorker"

# Logging
accesslog   = "-"          # stdout
errorlog    = "-"          # stderr
loglevel    = "info"

# Restart workers after this many requests (prevents memory leaks)
max_requests        = 1000
max_requests_jitter = 100

# Timeout — set high because InfluxDB + LLM can take a few seconds
timeout     = 120
keepalive   = 5