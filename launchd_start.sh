#!/bin/bash
# Wrapper for launchd — activates venv before starting Gunicorn
cd /Users/rdmasia/Documents/JINENDRA/rdm-wach-insights
source venv/bin/activate
exec gunicorn -c gunicorn.conf.py backend.main:app
