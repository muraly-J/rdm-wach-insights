# ADR — Cyberview MQTT Middleware Contract

**Date:** 2026-05-28
**Ticket:** RDMI-005
**Status:** Proposed (supersedes the "fixtures vs ingest" decision from spec stage)
**Decision drivers:** Plan A addendum A.26 / A.27 / A.28 (ingest framework + Cyberview discovery + backfill)

---

## Context

Cyberview is the second tenant for RDM Insight MVP. Their telemetry sits behind an MQTT middleware operated by Cyberview. To date we have **a single 5-minute snapshot** (`cyberview_mqtt_middleware_audit.csv`, 26 615 rows captured 2026-05-14 14:08 → 14:13 MYT) and a draft scoring design (`scripts/research/cyberview_health_index_design.md`).

Original Plan C T2 assumed: seed Cyberview org/site row + ingest from `scripts/research` fixtures for MVP demo, defer real MQTT to Phase 2.

This is no longer the chosen path. Per Plan A addendum we ingest live + backfill from the MQTT middleware behind a **separate ETL scheduler** from WACH. This ADR locks the contract we believe holds based on the 5-min snapshot, names the unknowns, and lists the verifications that must close in discovery.

---

## Decision

1. **Cyberview ingest is in-scope for MVP.** No fixtures path. The adapter (`sites/_default` queries DuckDB) reads tables written by `sites/cyberview/ingest/`.
2. **Separate scheduler from WACH.** A different `IngestRunner` instance under the `core/ingest/` framework (Plan A A.26), running on its own cadence with its own credentials and its own DuckDB schema namespace (`cyberview_*` tables vs `wach_*`).
3. **Three-pronged ingest** lives in `apps/api/sites/cyberview/ingest/`:
   - `mqtt_subscriber.py` — paho MQTT client, subscribes to `Cyberview/#`, writes to DuckDB buffer.
   - `historian_backfill.py` — if discovery finds a historian DB, one-shot pull from earliest timestamp → buffer.
   - `live_tail.py` — long-running subscriber for continuous ingest post-backfill.
4. **Buffer-first storage.** Append-only DuckDB table holds raw `{topic, payload_json, ts}` rows with `(source_id, topic, ts)` idempotency key. Structured columns derive later in transform step (Plan C). Schema instability is absorbed at the transform layer, not the ingest layer.
5. **Discovery is the first step of A.27, not a separate spike.** Connect to broker, document, then build the subscriber on top.

---

## Snapshot-derived contract

These facts are observed in `cyberview_mqtt_middleware_audit.csv`. They become the working assumption for the subscriber. Discovery (A.27) verifies or corrects.

### Topic schema

10-level path:

```
Cyberview / <Site> / Main / <Floor> / <Wing> / <Sub-Floor> / <Room> / <Device> / <direction> / <Metric>
```

**Observed values:**

| Field | Examples |
|---|---|
| Root | `Cyberview` |
| Site | `CoPlace3`, `Cyberview23` |
| Section | `Main` (constant in snapshot) |
| Floor | `L01`, `L02`, `L03`, `LB1`, `LGF`, `LRF`, `nullFloor` |
| Room | `AHU_Room_1..4`, `Ceiling`, `Fire_Control_Room`, `FM_Office`, `Genset_Room`, `Hex_Room`, `HT_Room`, `Kitchen`, `LMR`, `LV_Room*`, `Riser_Closet`, `Surau_*`, `nullRoom` |
| Device | `FCU-SME-GF-1`, AHUs, electrical panels, gateways |
| Direction | `input` (only direction in snapshot — no `output`/`command` observed; verify in discovery) |
| Metric | see "Metric categories" below |

**`null*` segments** in floor/room fields indicate topics that are not placed in the building hierarchy (e.g., gateway-host telemetry). The subscriber must NOT discard these — they carry CPU/memory/load metrics needed for ingest-pipeline observability and "is the gateway alive" signal.

**Topic count in snapshot:** 2 697 distinct topics over 5 minutes. Estimated total topic universe ≈ 3 000–5 000 (a fraction of inactive devices may not publish in any given 5-minute window).

### Payload schema

JSON value object (uniform across snapshot):

```json
{"val": <scalar>, "unit": "<unit_string>", "ts": <epoch_ms>}
```

- `val` — type varies: number, "ON"/"OFF" string for booleans, occasionally `null` (verify).
- `unit` — Cyberview-namespaced units. Examples seen: `"no-units"`, `"degrees-celsius"`, plus electrical/flow units (parse in discovery). Treat the unit string as opaque metadata, not a parsing key.
- `ts` — Unix epoch milliseconds **from the device**, not broker arrival time. The CSV `Timestamp` column is broker arrival. They differ; **use device `ts` as the canonical event time** and store broker arrival as `ingest_ts` for clock-skew detection.

**Sample-rate observation:** within the 5-min snapshot, individual topics publish anywhere from once per second (gateway telemetry) to every ~30 s (slow analog) to no publishes at all (steady-state digital). The middleware appears to broadcast on **change-of-value** for many digital topics, plus periodic refresh for analog. Confirm by inspecting two non-overlapping snapshots.

### Metric categories (from snapshot leaf names)

| Category | Example leaves |
|---|---|
| Thermal | `Space_Temperature`, `Temperature_Supply_Air`, `Temperature_Return_Air`, `CHWS_Temperature`, `CHWR_Temperature`, `CHW_Temperature_Difference` |
| Hydronic | `Flow_Rate`, `Valve_Pressure_Differential`, `Feedback_Position`, `Cooling_Output` |
| Status / safety | `Status_Start-Stop`, `Status_Trip`, `AOM_Status`, `Filter_Alarm`, `OT_Alarm` |
| Electrical (LV/HT rooms) | `Air_Circuit_Breaker_Status`, `Capacitor_Bank_Status`, `Incoming_0N_Status`, `Outgoing_0N_Status`, `Earth_Fault_Relay_Status`, `Overcurrent_Relay_Status`, `Bus_Coupler_Status`, `Genset_Supply_Status`, `Energy_Cumulative` |
| Gateway telemetry | `CPU_Load`, `CPU_Temperature`, `Board_Top_Temperature`, `Memory_Free/Total`, `Load_Avg_{1,5,15}_min`, `Buffers`, `Cached`, `Browser_Handles`, `Browser_Rss`, `Handles` |

Cyberview-defined health index (in `scripts/research/cyberview_health_index_design.md`) uses thermal + hydronic + electrical. Gateway telemetry is for our own ingest observability.

---

## Open unknowns (discovery must close)

| # | Question | Why it matters | How to verify |
|---|---|---|---|
| 1 | **Auth model** — TLS? username/password? client cert? | Determines paho config + Railway secret layout | Ask Cyberview ops; try `mosquitto_sub -h <host> -p <port> -v -t '#'` with credentials they provide |
| 2 | **Broker reachability from Railway** | If only reachable from inside Cyberview LAN, we need a bastion/tunnel or self-hosted subscriber sidecar | Connection attempt from Railway preview env |
| 3 | **Persistence + retention config** | `persistence true`? `max_queued_messages`? Retained messages on which topics? | `mosquitto_pub -D` to inspect; or read broker config; or observe by reconnecting and checking what arrives in first second |
| 4 | **Historian DB behind middleware** | If a TimescaleDB/InfluxDB/Mosquitto-DB sits behind the broker, **that's our backfill source** — MQTT alone cannot replay history that's been consumed | Direct question to Cyberview ops |
| 5 | **Output/command topics** | Snapshot shows only `input/`. Are there `output/`, `setpoint/`, `command/` topics? | Subscribe to `Cyberview/#` for a longer window; ask ops |
| 6 | **`val` type stability per topic** | Does a given topic ever flip between numeric and string? | Group snapshot by topic, check `val` types per topic |
| 7 | **Topic publish rate distribution** | Drives buffer sizing and DuckDB write batching | Re-sample with a 30-min window |
| 8 | **QoS levels in use** | Affects delivery guarantees and replay behaviour | Inspect broker config or paho `on_message` granfo |
| 9 | **Multi-site naming consistency** | `CoPlace3` and `Cyberview23` use the same topic shape — verified. Will future sites? | Confirm with ops |

These map to three possible discovery outcomes (Plan A addendum):

- **Outcome A — historian DB exists.** `historian_backfill.py` pulls earliest→now in batches. Full history. Preferred.
- **Outcome B — live MQTT only, retained messages on most topics.** Subscribe-with-retained at connect time = one snapshot per topic. Time series starts at `live_tail` boot. Document the depth limitation.
- **Outcome C — live MQTT only, no retention.** Live-only. Demo = "Cyberview since subscriber came online (Date X)". No backfill possible. Document clearly to stakeholders.

---

## Subscriber design (Plan A A.27 deliverable)

### Topology

```
                                                ┌──────────────────────────────┐
   Cyberview MQTT broker  ──────────TLS─────►   │ apps/api workers (Railway)   │
   (broker host TBD)                            │                              │
                                                │  cyberview/mqtt_subscriber   │
                                                │     paho async client        │
                                                │     subscribe "Cyberview/#"  │
                                                │     QoS 1                    │
                                                │                              │
                                                │  ─► core/ingest/buffer.py    │
                                                │       DuckDB INSERT          │
                                                │       idempotency key        │
                                                │                              │
                                                │  ─► ingest_runs row          │
                                                └──────────────────────────────┘
```

### Buffer table (writes from all three runners)

```sql
CREATE TABLE cyberview_raw_events (
  source_id      TEXT NOT NULL,       -- 'cyberview-mqtt' | 'cyberview-historian'
  topic          TEXT NOT NULL,
  device_ts      TIMESTAMP NOT NULL,  -- from payload.ts (epoch ms → ts)
  ingest_ts      TIMESTAMP NOT NULL,  -- broker arrival
  val_raw        JSON,                -- payload.val (typed)
  val_num        DOUBLE,              -- numeric coercion when possible
  val_str        TEXT,                -- string repr when not numeric
  unit           TEXT,
  raw_payload    JSON,                -- full payload for replay/debug
  PRIMARY KEY (source_id, topic, device_ts)
);

CREATE INDEX cv_raw_topic_ts ON cyberview_raw_events(topic, device_ts DESC);
CREATE INDEX cv_raw_device_ts ON cyberview_raw_events(device_ts DESC);
```

The transform step (Plan C T2 work, narrowed) parses `topic` into hierarchical columns and produces `cyberview_device_metric_hourly` views on top of this buffer.

### `IngestRunner` contract (from Plan A A.26)

```python
class CyberviewMQTTRunner(IngestRunner):
    async def discover(self) -> DiscoveryReport: ...        # one-shot, outputs unknowns 1-9 above
    async def backfill(self, since, until) -> RunStats: ... # no-op for MQTT (handled by historian runner)
    async def tail(self) -> None: ...                       # long-running, never returns
```

### Failure modes + responses

| Failure | Detection | Response |
|---|---|---|
| Broker unreachable | paho `on_connect` rc != 0 | Exponential backoff, log to `ingest_runs`, alert via core/observability if down > 5 min |
| Message decode error | JSON parse fail | Store as `val_raw=null, raw_payload=<string>`, do not drop the row |
| DuckDB write contention | INSERT exception | Single-writer per source (subscriber owns the connection); other readers use separate connections |
| Topic explosion (e.g., new site comes online) | Topic count vs baseline | Log+continue; topics auto-register, no schema change needed |
| Clock skew between device and broker | `abs(device_ts - ingest_ts) > 60s` | Log warning per device; continue (device_ts remains canonical) |

---

## Why separate from WACH ETL

(Restated from Plan A addendum, for completeness.)

| Concern | WACH | Cyberview |
|---|---|---|
| Source | InfluxDB Cloud (HTTP poll) | MQTT broker (push) + optional historian DB |
| Auth | Influx token | TBD (likely TLS + creds) |
| Failure mode | HTTP 5xx / rate-limit | Connection drop / message storm |
| Schedule | Cron every N min | Continuous tail + one-shot backfill |
| Module | `sites/wach/ingest/` | `sites/cyberview/ingest/` |
| DuckDB namespace | `wach_*` tables | `cyberview_*` tables |
| Worker | Same `IngestRunner` framework, distinct runner instance | Same framework, distinct runner instance |

If one ingest pipeline breaks, the other survives. Different processes, different credentials, different schedules.

---

## Open requests (action items)

| # | Owner | Item |
|---|---|---|
| 1 | Jin → Cyberview ops | Broker host, port, auth method, TLS config |
| 2 | Jin → Cyberview ops | Confirm or deny existence of historian DB; if yes, access creds + read-only role |
| 3 | Jin → Cyberview ops | Network path: do we connect direct from Railway or via bastion / VPN? |
| 4 | Jin → Cyberview ops | List of `output/` / `command/` topics if any |
| 5 | Jin → Cyberview ops | Persistence + retention policy (`persistence true`, `max_queued_messages`, retained per-topic) |
| 6 | Jin (internal) | Lock decision: APScheduler in-process vs separate Railway worker service for the Cyberview tail. Default = separate Railway worker (matches "separate scheduler" principle of this ADR). Confirm before Sprint 1. |

---

## Consequences

**Positive**
- Cyberview demo uses live data, not fixtures. More compelling for stakeholders.
- Ingest framework (A.26) is reusable for future tenants — pay for it once.
- Buffer-first storage absorbs schema drift; transform layer evolves independently.
- Separate scheduler isolates failure modes between tenants.

**Negative**
- +3 days to Sprint 1/2 (A.26 + A.27 + A.28). Demo slips to ~Jul 21.
- Hard dependency on Cyberview ops providing broker access in week 1. If they don't, A.27/A.28 stall and we fall back to fixture-mode for the worst case (matches outcome C above — no backfill but still real-shape data).
- DuckDB single-writer constraint requires care if we ever want multi-process ingest. Acceptable for MVP; revisit if scale demands.

**Neutral**
- Plan C T2 shrinks (data already in DuckDB) but T1 (generic adapter for `_default`) is unchanged.

---

## Verification

- [x] Topic schema documented from snapshot, with `null*` segments noted.
- [x] Payload schema documented (`val`/`unit`/`ts`).
- [x] Metric categories enumerated.
- [x] Open unknowns enumerated with verification method per item.
- [x] Three discovery outcomes mapped to A.26/A.27/A.28 scope.
- [x] Buffer table DDL specified.
- [x] Cross-tenant isolation justified (separate runner, separate schema namespace).
- [x] Action items assigned to owner.

## Next

- A.27 discovery kickoff requires Cyberview broker creds. Email/call ops this week.
- A.26 ingest framework can proceed in parallel — no dependency on Cyberview access.
- This ADR is the input to Plan A T2 (compose adds `paho-mqtt` + optional Mosquitto for dev) and Plan A T6 (migration adds `ingest_sources`/`ingest_runs` tables).
