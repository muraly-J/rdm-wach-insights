#!/bin/bash
# MCP Server Quick Start for WACH Insight
# Usage: ./scripts/mcp.sh [run|status]

case "$1" in
    run)
        echo "🚀 Starting MCP Servers..."
        echo ""
        echo "Open these commands in separate terminals:"
        echo ""
        echo "# Terminal 1 - Memory Server:"
        echo "npx -y @modelcontextprotocol/server-memory"
        echo ""
        echo "# Terminal 2 - Local Files Server:"
        echo "npx -y local-files@latest"
        echo ""
        echo "# Terminal 3 - Vercel MCP (optional):"
        echo "npx -y @vercel/mcp"
        ;;
    status)
        echo "📋 MCP Server Status:"
        echo ""
        echo "Open Qwen Code and run: Cmd+Shift+P → MCP: List Servers"
        echo ""
        echo "Servers to start:"
        echo "  ✓ memory"
        echo "  ✓ local-files"
        echo "  ⚙️  com.vercel/vercel-mcp (HTTP - auto-starts)"
        ;;
    *)
        echo "🚀 MCP Server Starter for WACH Insight"
        echo ""
        echo "Usage:"
        echo "  ./scripts/mcp.sh run    # Show commands to start servers"
        echo "  ./scripts/mcp.sh status # Check server status"
        ;;
esac
