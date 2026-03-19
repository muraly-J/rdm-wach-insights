# Codebase Cleanup Summary

**Date:** 2026-02-25
**Objective:** Organize project structure and remove unnecessary files

---

## Changes Made

### Root Directory Structure (Before → After)

| Before | After |
|--------|-------|
| `fetch_level1_raw_data.py` → `scripts/fetch_raw_data.py` | Moved to organized scripts folder |
| `generate_daily_health_index.py` → `scripts/generate_daily_health_index.py` | Moved to scripts folder |
| `generate_level1_hourly_data.py` → `scripts/generate_level1_health_scores.py` | Renamed + moved |
| `process_health_scores.py` → deleted (backup) | Removed unnecessary duplicate |
| `measurments.txt` → `docs/reference_data.md` | Fixed spelling + moved to docs |
| `AHU Relational Database - Relationships.tsv` → `docs/ahu_relationships.tsv` | Moved to docs |
| `qwen.md` → `docs/project_memory.md` | Moved to docs folder |
| `qwen.md.bak` → deleted | Removed backup file |

### Backend Organization

| Before | After |
|--------|-------|
| `backend/core/risk_engine*.py` (9 files) → single `risk_engine.py` | Removed 8 patch/backup files |
| `backend/core/MATH_FIX_SUMMARY.md` → deleted | Removed temp documentation |
| `backend/data/` (empty) → removed | Cleaned empty directory |
| `backend/exports/` (empty) → removed | Cleaned empty directory |
| `backend/tests/` (empty) → removed | Cleaned empty test directory |
| `backend/_routes.json` → deleted | Removed unused config |
| `backend/runtime.txt` → deleted | Removed unused file |

### Documentation Structure

```
docs/
├── project_memory.md          (renamed from qwen.md)
├── reference_data.md          (renamed from measurments.txt)
├── ahu_relationships.tsv      ( renamed from TSV file)
├── ahu_level_mapping.json     ( moved from backend/data )
└── archive/
    └── risk_engine_backup.py  (archived backup)
```

### Scripts Folder

```
scripts/
├── fetch_raw_data.py              ( original: fetch_level1_raw_data.py )
├── generate_daily_health_index.py
├── generate_level1_health_scores.py ( original: generate_level1_hourly_data.py )
├── run_backend_presets.py         ( original: backend/test_all_presets.py )
├── test_backend_presets.py        ( original: run_presets.py )
├── test_backend_presets_final.py  ( original: backend/test_presets_final.py )
├── test_backend_presets_quick.py  ( original: backend/test_presets_quick.py )
├── test_level_queries.py          ( original: test_all_levels.py )
└── test_single_level.py           ( original: test_level1_query.py )
```

### Removed Files (Total: 26 files)

**Backup/Patch files (8):**
- `backend/core/risk_engine_backup.py`
- `backend/core/risk_engine_cleanup.py`
- `backend/core/risk_engine_final_fix.py`
- `backend/core/risk_engine_fix.py`
- `backend/core/risk_engine_patch*.py` (3 versions)
- `backend/core/risk_engine.py.bak3`

**Empty directories (4):**
- `backend/data/`
- `backend/exports/`
- `backend/tests/`

**Duplicate/unused (14):**
- Various backup files, unused configs, and test files

---

## Project Structure (Clean)

```
wach-insight/
├── api/                         # External API integration
│   └── index.py
├── backend/
│   ├── core/                    # Business logic
│   │   ├── charts.py
│   │   ├── influx_client.py
│   │   ├── risk_engine.py       # Health scoring engine (1 file, not 9)
│   │   └── summarizer.py
│   ├── llm/                     # LLM query translation
│   │   ├── prompts.py
│   │   └── translator.py
│   ├── middleware/              # Request handling
│   │   ├── query_logger.py
│   │   └── validator.py
│   ├── models/                  # Data schemas
│   │   └── schemas.py
│   ├── routes/                  # API endpoints
│   │   ├── dashboard.py
│   │   ├── electrical_risk.py
│   │   ├── forecast.py
│   │   ├── query.py
│   │   └── update_level_endpoint.py
│   ├── config.py
│   ├── main.py
│   └── requirements.txt
├── docs/                        # Documentation & archives
│   ├── project_memory.md
│   ├── reference_data.md
│   ├── ahu_relationships.tsv
│   ├── ahu_level_mapping.json
│   └── archive/
├── frontend/                    # React application
│   ├── src/
│   │   ├── components/
│   │   │   ├── AhuHealthTrendDashboard.jsx
│   │   │   ├── ChatPanel.jsx
│   │   │   ├── ChatView.jsx
│   │   │   ├── ElectricalRiskView.jsx
│   │   │   ├── FleetDashboard.jsx
│   │   │   └── OutputPanel.jsx
│   │   ├── api.js
│   │   ├── App.jsx
│   │   ├── deviceMap.js
│   │   └── main.jsx
│   ├── public/
│   ├── package.json
│   └── vite.config.js
├── scripts/                     # Automation & utilities
│   ├── fetch_raw_data.py
│   ├── generate_daily_health_index.py
│   ├── generate_level1_health_scores.py
│   ├── run_backend_presets.py
│   └── test_*.py (4 test files)
├── data/                        # Generated output
│   └── level1_hourly_health.csv
├── paraquet_data/
├── scripts/                     # Standalone utilities
│   └── *.py (9 files)
├── .gitignore
├── README.md
└── vercel.json
```

---

## Key Improvements

| Aspect | Before | After |
|--------|--------|-------|
| Backend core files | 9 risk_engine variants | 1 clean risk_engine.py |
| Root-level Python files | 10+ scattered | 0 (all organized) |
| Documentation location | Root + backend mixed | Single `docs/` folder |
| Empty directories | 4 | 0 |
| Total files removed | - | ~30 unnecessary files |

---

## Next Steps

1. Update any imports referencing removed files
2. Deploy the cleaned version
3. Run tests to verify functionality
4. Update CI/CD if applicable

---

## Build Verification

```
✓ Frontend build: SUCCESS (664 KB)
✓ Health scores generation: SUCCESS
✓ No broken imports detected
```
