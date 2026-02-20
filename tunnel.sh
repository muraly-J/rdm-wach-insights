#!/bin/bash
# tunnel.sh — starts a free Cloudflare Tunnel pointing to Gunicorn
# Run in a separate terminal AFTER start.sh (or after LaunchAgent is running)
#
# FIRST TIME SETUP:
#   brew install cloudflare/cloudflare/cloudflared
#
# THEN RUN:
#   bash tunnel.sh
#
# Cloudflare will print a public URL like:
#   https://random-words-here.trycloudflare.com
# Share that URL — anyone can open it from any device.
#
# The URL changes every time you restart the tunnel.
# For a permanent URL, upgrade to a named Cloudflare tunnel (free with an account).

echo ""
echo "====================================="
echo "  WACH Insight — Cloudflare Tunnel"
echo "====================================="
echo ""
echo "Starting tunnel → http://127.0.0.1:8000"
echo "Your public URL will appear below in a moment..."
echo ""

cloudflared tunnel --url http://127.0.0.1:8000