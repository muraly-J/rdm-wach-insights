# Cyberview MQTT Middleware — Historical-Depth Investigation

**Date:** 2026-05-26
**Investigator:** Jin (with Claude)
**Source:** Live probes against `139.59.106.65` + analysis of `cyberview_mqtt_middleware_audit.csv`
**Related:** [Cyberview MQTT ADR](../specs/2026-05-28-cyberview-mqtt-adr.md), Plan A addendum A.26 / A.27 / A.28

---

## Question

1. What is the earliest payload timestamp obtainable from the Cyberview MQTT middleware at `139.59.106.65:1883`?
2. Is historical backfill possible from that endpoint?

## Bottom line

- **From MQTT alone: NO useful history.** The broker is live-only. Only 56 retained messages exist across the entire broker (against ~2 700 distinct topics in the 5-min audit snapshot). Subscribing to the broker today gives you "now onward," not history.
- **There IS almost certainly a historian behind the middleware.** The host runs Grafana (port 3000) and a Laravel application API (`/service/...` via nginx on port 80). Grafana is a visualizer, not a data store, so the data is being persisted somewhere on that host — most likely a TimescaleDB / PostgreSQL / InfluxDB that is not exposed to the public internet.
- **Earliest possible MQTT-broker history is ~2026-02-21** (broker uptime ≈ 94 days), but only for the 56 retained topics, and the retained values are *current* state snapshots, not time series.
- **Our broker user (`rdmasia`) currently has no ACL grant for `Cyberview/#`** — we connect successfully but receive zero application messages. We must request an ACL update before we can even live-tail. ACLs appear to have been tightened between the 2026-05-14 audit and today.

---

## Evidence

### 1. Snapshot analysis — `cyberview_mqtt_middleware_audit.csv`

```
total_rows:        26 614
unique_topics:     2 697
payload.ts min:    2026-05-14T06:08:19.946Z (UTC)
payload.ts max:    2026-05-14T06:12:51.092Z (UTC)
payload.ts span:   4.52 minutes
broker arrival:    2026-05-14 14:08:19 → 14:12:51 (MYT, 5 min window)
device→broker skew: p50 −83 ms, p99 51 ms, max 54 ms — sub-second alignment
```

**Interpretation:** `payload.ts` (device clock) and broker-arrival time differ by < 1 second across all 26 614 rows. No messages with `payload.ts` older than the first broker arrival. **Zero evidence of retained-message replay in the captured window.** Everything received was a live publish.

### 2. Live broker probe — connected today (2026-05-26)

```
HOST: 139.59.106.65:1883   (plaintext MQTT, no TLS)
USER: rdmasia / PASS: password
```

`$SYS/#` returned 93 broker-metadata messages (all with `retain=True`, as expected — Mosquitto publishes `$SYS` with retention by design):

| Metric | Value | Interpretation |
|---|---|---|
| `$SYS/broker/version` | `mosquitto version 2.1.2` | Mosquitto, current LTS |
| `$SYS/broker/uptime` | `8 137 427 seconds` | **~94 days uptime → broker booted ≈ 2026-02-21** |
| `$SYS/broker/messages/received` | 562 330 535 | ~562 M msgs since boot |
| `$SYS/broker/load/messages/received/1min` | 6 062.75/s | **broker is actively ingesting ~6 kHz right now** |
| `$SYS/broker/retained messages/count` | **56** | Only 56 retained — vs 2 697 distinct topics in audit |
| `$SYS/broker/messages/stored` | 56 | Same count — broker is not configured to persist application messages, only retained ones |
| `$SYS/broker/clients/connected` | 3 | active subscribers |
| `$SYS/broker/clients/maximum` | 10 | client cap |
| `$SYS/broker/store/messages/bytes` | 306 B | the 56 retained messages total 306 bytes — they're config/status flags, not telemetry |

`Cyberview/#` subscription returned **0 messages in 10 seconds** despite the broker ingesting ~60 000 messages over that window.

**Three possible explanations** (in order of likelihood):

1. **ACL change.** Our user had `Cyberview/#` read access during the 2026-05-14 audit but no longer does. Most likely, given the broker is verifiably busy.
2. The publishers are routed to a private vhost / namespace that excludes our user.
3. (Unlikely) The 6 kHz of traffic is on entirely different topics.

### 3. Host-level service discovery

| Port | Service | Evidence |
|---|---|---|
| **80** | nginx → "terraEdge" SPA (Vite/React, `meta title=terraEdge`) | `curl -I` shows nginx 200 OK |
| **80 /service/** | Laravel API (PHP) | `/service/oauth/token` returns Laravel-default 404 HTML |
| **1883** | Mosquitto 2.1.2 MQTT broker | confirmed |
| **3000** | **Grafana 12.3.3** | `/api/health` returns `{"database":"ok","version":"12.3.3","commit":"2a14494b..."}` |
| **3000 (other)** | Auth-protected | `/api/datasources`, `/api/frontend/settings` return 401 — Grafana auth wall |
| 443, 5432, 8086, 8088, 8443, 9000, 9090 | closed externally | might still be live on `localhost` of the host |

**SPA-extracted API paths** (from `/assets/index-C1lSI0pl.js`):

```
${API_BASE}/oauth/token          — Laravel Passport / OAuth2
${API_BASE}/oauth/refresh
${API_BASE}/oauth/register
/api/user                        — terraEdge user endpoint (proxied via nginx)
SPA routes: /dashboard, /device-adapters, /mqtt-viewer, /Login
```

The `/mqtt-viewer` SPA route is the equivalent of MQTT Explorer that Cyberview team uses. The fact that it exists, plus Grafana, plus ~94 days of 6 kHz publishing, is the strongest possible indirect evidence that **there is a backing database holding history**. We just can't reach it from the public internet, and the only readable HTTP surface (Grafana) is behind auth.

---

## What this means for Plan A A.26 / A.27 / A.28

Mapping back to the three discovery outcomes locked in the [ADR](../specs/2026-05-28-cyberview-mqtt-adr.md):

| Outcome | Match | Notes |
|---|---|---|
| **A. Historian DB exists** | **Almost certainly true, but not directly accessible to us yet.** | Grafana + Laravel + 562 M messages persisted somewhere → must be a DB. Need ops to (a) confirm engine + schema, (b) grant read-only access, or (c) provide a Grafana service-account API key so we can pull via Grafana's data-source proxy. |
| **B. Live MQTT + retained = limited history** | Partially. **Only 56 topics retained — useless for time series.** | Retained messages are clearly used for config/status flags only (306 bytes total → tiny string state). Not a meaningful backfill source. |
| **C. Live-only, no backfill** | **The default if (A) doesn't unblock.** | We start `live_tail.py` after ACL is restored, and Cyberview demo = "live since subscriber came online (Date X)". |

**Recommendation:** Proceed with `core/ingest/` framework build (A.26) and the live-tail subscriber (A.27) on the assumption of outcome **C** as the floor, while simultaneously chasing outcome **A** through ops. Don't block A.26/A.27 on outcome A access — they're needed either way.

---

## Action items (updated)

| # | Owner | Item | Blocking | Why |
|---|---|---|---|---|
| 1 | Jin → Cyberview ops | **Restore ACL** for user `rdmasia` to subscribe to `Cyberview/#` (read-only) | A.27, A.28, and any live tail | Confirmed via probe that current creds connect but receive nothing |
| 2 | Jin → Cyberview ops | Confirm historian DB exists; if yes, identify engine (Postgres/Timescale/Influx/MySQL), schema name, retention policy | A.28 (backfill) | We have 99% confidence one exists; need spec |
| 3 | Jin → Cyberview ops | Provide read-only DB credentials **or** Grafana service-account API key (so we can pull via `/api/datasources/proxy/...`) | A.28 fallback | If full DB access isn't granted, Grafana proxy is a viable second-best |
| 4 | Jin → Cyberview ops | Confirm TLS expectation. Current broker is `1883` plaintext; do they plan to move to `8883` TLS? | A.27 production | Affects paho client config and Railway egress |
| 5 | Jin (internal) | Add `mqtt-explorer` SPA at `http://139.59.106.65/mqtt-viewer` to the demo / context bundle — helps stakeholders see what we're integrating against | docs | low priority |

---

## Reproducibility — commands used

```bash
# 1) Snapshot timestamp analysis (no network)
python3 — runs analysis on cyberview_mqtt_middleware_audit.csv
        → reports payload.ts span vs broker-arrival span
        → checks for messages older than first broker arrival

# 2) Live broker probe
python3 — paho.mqtt.client connect to 139.59.106.65:1883 with rdmasia/password
        → subscribe ["Cyberview/#", "$SYS/#", "#"]
        → collect 10 s of messages, log retained-flag + payload.ts age
        # Result: 0 Cyberview msgs, 93 $SYS msgs (all retained=True)

# 3) Host service discovery
curl  -s -m 3 http://139.59.106.65/                       # nginx + terraEdge SPA
curl  -s -m 3 http://139.59.106.65:3000/api/health        # Grafana 12.3.3
curl  -s -m 3 http://139.59.106.65/service/oauth/token    # Laravel API (PHP)
curl  -s -m 3 http://139.59.106.65/assets/index-C1lSI0pl.js | \
        grep -oE 'f3=[^,;]{1,100}'                         # extract API base = /service
```

Probe scripts intentionally short-lived; no writes attempted; no DoS surface.

---

## Conclusion

The user's two questions, answered crisply:

1. **Earliest payload timestamp obtainable from the MQTT endpoint alone:** about **2026-02-21** (broker boot date), but only for the 56 retained-flag topics, and those topics carry single-value state, not a time series. **Effective historical depth from MQTT alone: zero useful.**
2. **Is historical backfill possible from this endpoint?** Not from the MQTT broker as configured. Backfill *is* possible if Cyberview grants us access to the historian DB that demonstrably exists behind their Grafana + Laravel stack. That request is now action item #2.

---

## Verification

- [x] Snapshot payload.ts analysed against broker arrival times — no retained-message evidence in 5-min capture.
- [x] Live MQTT probe executed — broker confirmed up, uptime captured, retained-count captured, ACL-block hypothesised.
- [x] Host port scan completed — nginx (80), Grafana (3000), Mosquitto (1883) identified.
- [x] SPA bundle inspected — Laravel `/service` API base + OAuth flow identified.
- [x] All three ADR discovery outcomes (A/B/C) mapped to observed evidence.
- [x] Action items updated with current ACL block as new top blocker.
