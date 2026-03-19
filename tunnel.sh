#!/bin/bash
# tunnel.sh — DEPRECATED: Cloudflare Tunnel for local development only
# 
# This script is kept for backward compatibility with local development setups.
# For production, the backend now runs as a Vercel serverless function.
#
# To run locally without tunnel:
#   1. Start backend: ./start.sh
#   2. Open frontend: cd frontend && npm run dev
#
# Usage (local development only):
#   bash tunnel.sh
#
# Requires: cloudflared (brew install cloudflare/cloudflare/cloudflared)

echo ""
echo "====================================="
echo "  WACH Insight — Local Development"
echo "====================================="
echo ""
echo "NOTE: This script is for LOCAL DEVELOPMENT only."
echo "For production deployment, see DEPLOYMENT.md"
echo ""
echo "Starting tunnel → http://127.0.0.1:8081"
echo "Your public URL will appear below..."
echo ""

cloudflared tunnel --url http://127.0.0.1:8081