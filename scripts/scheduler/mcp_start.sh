#!/bin/bash
# Fast MCP server starter for WACH Insight

echo "Starting Memory Server..."
npx -y @modelcontextprotocol/server-memory &
M1=$!

echo "Starting Local Files Server..."
npx -y local-files@latest &
M2=$!

sleep 2

echo ""
echo "✅ MCP servers started in background:"
echo "   - Memory Server (PID: $M1)"
echo "   - Local Files (PID: $M2)"
echo ""
echo "Note: For Qwen Code, you still need to use Cmd+Shift+P → MCP: Start Server"
echo "      but this script pre-starts the processes for faster activation."
