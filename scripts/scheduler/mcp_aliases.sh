#!/bin/bash
# MCP Server Quick Start for WACH Insight
# Source this file: source scripts/mcp_aliases.sh

alias mcp="echo '🚀 MCP Server Quick Start for WACH Insight'"
alias mcp-run="echo 'Run these commands in separate terminals:' && echo '' && echo 'Terminal 1 - Memory:' && echo '   npx -y @modelcontextprotocol/server-memory' && echo '' && echo 'Terminal 2 - Local Files:' && echo '   npx -y local-files@latest' && echo '' && echo 'Terminal 3 - Vercel (optional):' && echo '   npx -y @vercel/mcp'"
alias mcp-all="echo 'Copies commands to clipboard (macOS):' && echo '' && echo '  npx -y @modelcontextprotocol/server-memory' && echo '  npx -y local-files@latest'"

echo "Aliases created:"
echo "  mcp      - Show welcome message"
echo "  mcp-run  - Display commands to run manually"
echo "  mcp-all  - Show all commands (copy-paste friendly)"
