# Qwen Configuration for WACH Insight

This directory contains configuration files to optimize Qwen Code for the WACH Insight project.

## 📁 Directory Structure

```
.qwen/
├── mcp.json      # Model Context Protocol servers
├── skills.json   # Project-specific skills
└── README.md     # This file

.vscode/
├── extensions.json  # Recommended VS Code extensions
```

## 🚀 MCP Servers (Model Context Protocol)

MCP servers enhance Qwen's capabilities by providing access to external systems and tools.

### Available Servers

| Server | Purpose |
|--------|---------|
| **memory** | Persistent context between sessions (remembers project patterns) |
| **fetch** | Web API calls (InfluxDB cloud, LM Studio API) |
| **local-files** | File system access for your project directory |
| **sqlite** | SQLite database queries (for testing/mock data) |

### Server Details

#### 1. Memory (`@modelcontextprotocol/server-memory`)
- **Purpose**: Remembers project context across conversations
- **Use Cases**:
  - Remembering AHU ID patterns (e.g., `e0101`, `e11xx`)
  - Tracking latest health score calculations
  - Storing project-specific configuration values

#### 2. Fetch (`@modelcontextprotocol/server-fetch`)
- **Purpose**: Make HTTP requests to external APIs
- **Use Cases**:
  - Testing InfluxDB Cloud endpoints
  - Verifying LM Studio API connectivity
  - Fetching remote configuration

#### 3. Local Files (`local-files@latest`)
- **Purpose**: Read and write files in your project
- **Use Cases**:
  - Reading CSV health score data
  - Modifying Python backend files
  - Updating React components

#### 4. SQLite (`@modelcontextprotocol/server-sqlite`)
- **Purpose**: Query SQLite databases
- **Use Cases**:
  - Testing health score calculations
  - Validating data generation scripts
  - Ad-hoc analysis of pre-generated data

## 🧩 Skills

Skills are project-specific tools that extend Qwen's capabilities.

### Available Skills

| Skill | Purpose |
|-------|---------|
| **python** | Execute Python scripts, backend tests, InfluxDB queries |
| **node** | Run frontend build commands, Jest tests, npm operations |
| **csv** | Read and analyze CSV files for health score data |

### Skill Use Cases

#### Python
```python
# Run backend tests
pytest backend/

# Execute health score generation script
python scripts/generate_level1_health_scores.py --all-ranges

# Test InfluxDB connection
python -c "from config import *; print(get_influx_url())"
```

#### Node
```bash
# Build frontend
npm run build

# Run tests
npm test

# Start development server
npm run dev
```

#### CSV Analysis
- Read health score CSV files directly
- Analyze FAIR algorithm output
- Validate data quality metrics

## 💻 VS Code Extensions

Recommended extensions for optimal development experience.

### Must-Have Extensions

| Extension | Purpose |
|-----------|---------|
| **Python (ms-python.python)** | Full Python support with debugging |
| **Pylance (ms-python.vscode-pylance)** | Fast Python language server |
| **ESLint (dbaeumer.vscode-eslint)** | JavaScript/TypeScript linting |

### Recommended Extensions

| Extension | Purpose |
|-----------|---------|
| **Prettier** | Code formatting for Python, JS, JSX |
| **Black Formatter** | Python code formatter |
| **Jupyter** | Data analysis notebooks |
| **REST Client** | API endpoint testing |

## 🎯 Project-Specific Optimizations

### WACH Insight Context

Your Qwen is now configured for:

1. **Time-Series Data Analysis**
   - InfluxDB queries
   - Health score calculations (FAIR algorithm)
   -AHU fleet metrics

2. **Full-Stack Development**
   - FastAPI backend (Python)
   - React frontend (JavaScript/JSX)
   - Local LM Studio integration

3. **Data Processing**
   - CSV generation and validation
   - Health tier classification (Healthy/Monitor/Maintenance Soon/Critical)
   - 24h/7d/30d time range analysis

### Common Workflows

#### 1. Adding a New Dashboard Chart
```
1. Define metric in backend/core/risk_engine.py
2. Add chart configuration to frontend/src/components/AhuHealthTrendDashboard.jsx
3. Test with Python script (scripts/generate_level1_health_scores.py)
4. Verify with VS Code REST Client
```

#### 2. Debugging Health Score Calculation
```
1. Use CSV skill to read health score output
2. Verify FAIR algorithm components (energy, PF, imbalance, THD, overload)
3. Check tier classification thresholds (80/60/40)
```

#### 3. Testing LM Studio Integration
```
1. Ensure LM Studio is running (port 1234)
2. Use Fetch MCP server to test /v1/models endpoint
3. Verify LMS_BASE_URL in .env file
```

## 🔧 Configuration Files

### `.qwen/mcp.json`
```json
{
  "mcpServers": {
    "memory": {...},
    "fetch": {...},
    "local-files": {...},
    "sqlite": {...}
  }
}
```

### `.qwen/skills.json`
```json
{
  "skills": [
    {"name": "python", "description": "..."},
    {"name": "node", "description": "..."},
    {"name": "csv", "description": "..."}
  ]
}
```

### `.vscode/extensions.json`
```json
{
  "recommendations": [
    {"extension": "ms-python.python", "..."},
    ...
  ]
}
```

## 📖 Learning Resources

- [MCP Documentation](https://modelcontextprotocol.io)
- [FastAPI Tutorial](https://fastapi.tiangolo.com)
- [React Documentation](https://react.dev)
- [InfluxDB Python Client](https://github.com/influxdata/influxdb-client-python)

## 🆘 Getting Help

If you need to:
1. **Reset Configuration**: Delete `.qwen/` and recreate
2. **Add New MCP Server**: Update `.qwen/mcp.json`
3. **Configure Skills**: Update `.qwen/skills.json`

---

**Version**: 1.0  
**Last Updated**: March 2026  
**Project**: WACH Insight - AHU Analytics Dashboard
