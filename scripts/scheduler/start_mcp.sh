#!/bin/bash
# Start MCP servers for WACH Insight
# Run this script to start all MCP servers quickly

echo "🚀 Starting MCP Servers..."
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Open these commands in separate terminals:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Terminal 1 - Memory Server:"
echo '  npx -y @modelcontextprotocol/server-memory'
echo ""

echo "Terminal 2 - Local Files Server:"
echo '  npx -y local-files@latest'
echo ""

echo "Terminal 3 - Vercel MCP Server:"
echo '  npx -y @vercel/mcp'
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Once started, verify in Qwen Code:"
echo '  Cmd+Shift+P → MCP: List Servers'
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
