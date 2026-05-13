-- 0001_cmms_events.duckdb.sql
-- DDL for the CMMS events cache table.
-- Executed inline by CSVCMMSBackend._init_cache(); this file is the canonical
-- schema reference for code reviewers and future migrations.

CREATE TABLE IF NOT EXISTS cmms_events (
    event_id    TEXT PRIMARY KEY,
    ahu_id      TEXT NOT NULL,
    ts          TIMESTAMP NOT NULL,
    event_type  TEXT NOT NULL,
    notes       TEXT,
    source      TEXT NOT NULL DEFAULT 'manual'
);

CREATE INDEX IF NOT EXISTS idx_cmms_events_ahu_ts ON cmms_events (ahu_id, ts);
