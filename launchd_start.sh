#!/bin/bash
cd /Users/rdmasia/wach-insight
source /Users/rdmasia/wach-insight/venv/bin/activate
exec gunicorn -c gunicorn.conf.py backend.main:app
