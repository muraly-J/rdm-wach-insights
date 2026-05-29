"""Build a one-stop WACH data-inventory markdown.

Joins three sources per device:
  1. docs/ahu_relationships.tsv  -> device_id (e0101) <-> AHU label/name
  2. EMS (electrical) DuckDB layers (data/ archive + backend/data/ hot)
  3. BMS (HVAC/BACnet) InfluxDB bucket wach_temp on the private host

Outputs: docs/2026-05-29-wach-data-inventory.md

Run from repo root:  venv/bin/python -m scripts.research.build_data_inventory
"""
from __future__ import annotations

import csv
import os
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import duckdb

# ── Config ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
TSV = ROOT / "docs" / "ahu_relationships.tsv"
OUT = ROOT / "docs" / "2026-05-29-wach-data-inventory.md"
EMS_DBS = [ROOT / "data" / "healthdb.duckdb", ROOT / "backend" / "data" / "healthdb.duckdb"]

# Credentials/host come from the environment — never hardcode tokens.
#   BMS_INFLUX_URL=http://<host>:8086 BMS_INFLUX_TOKEN=<token> venv/bin/python -m scripts.research.build_data_inventory
INFLUX_URL = os.environ.get("BMS_INFLUX_URL", "")
INFLUX_TOKEN = os.environ.get("BMS_INFLUX_TOKEN", "")
INFLUX_ORG = os.environ.get("BMS_INFLUX_ORG", "wach")
BMS_BUCKET = os.environ.get("BMS_INFLUX_BUCKET", "wach_temp")
EMS_BUCKET = "wach_bucket_3"  # electrical (public host) - for reference only

if not INFLUX_URL or not INFLUX_TOKEN:
    sys.exit(
        "Missing BMS Influx credentials. Set BMS_INFLUX_URL and BMS_INFLUX_TOKEN in the "
        "environment before running (do not hardcode them)."
    )

# The 46 source electrical metrics (ALLOWED_METRICS minus the 5 time-range tokens)
EMS_METRICS = [
    "power_total", "power_l1", "power_l2", "power_l3", "power_demand", "max_power_demand",
    "apparent_power_total", "apparent_power_l1", "apparent_power_l2", "apparent_power_l3",
    "apparent_power_demand", "reactive_power_total", "reactive_power_l1", "reactive_power_l2",
    "reactive_power_l3", "reactive_power_demand", "energy_import", "energy_export",
    "reactive_energy_import", "reactive_energy_export", "apparent_energy", "current_avg",
    "current_l1", "current_l2", "current_l3", "current_l1_thd", "current_l3_thd",
    "volts_l_n_avg", "volts_l_l_avg", "volts_l1_n", "volts_l2_n", "volts_l3_n",
    "volts_l1_l2", "volts_l2_l3", "volts_l3_l1", "volts_l1_thd", "volts_l2_thd",
    "volts_l3_thd", "power_factor_avg", "power_factor_l1", "power_factor_l2",
    "power_factor_l3", "freq", "current_unbalance", "volts_unbalance", "digital_input_1_and_2",
]


def flux(query: str) -> list[list[str]]:
    """Run a Flux query, return parsed non-empty CSV rows (annotations stripped)."""
    req = urllib.request.Request(
        f"{INFLUX_URL}/api/v2/query?org={INFLUX_ORG}",
        data=query.encode(),
        headers={
            "Authorization": f"Token {INFLUX_TOKEN}",
            "Accept": "application/csv",
            "Content-Type": "application/vnd.flux",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        text = r.read().decode()
    rows = []
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        rows.append(line.split(","))
    return rows


def norm(name: str) -> str:
    """Normalize a device label/name to a join key: strip leading AHU tokens + separators."""
    toks = re.split(r"[ _\-]+", name.upper().strip())
    toks = [t for t in toks if t]
    while toks and toks[0] == "AHU":
        toks.pop(0)
    return "".join(toks)


# ── 1. Parse TSV ──────────────────────────────────────────────────────────────
def load_tsv() -> tuple[list[dict], dict[str, list[dict]]]:
    rows = []
    by_norm: dict[str, list[dict]] = defaultdict(list)
    with open(TSV) as f:
        reader = csv.DictReader(f, delimiter="\t")
        for r in reader:
            rec = {
                "level": (r.get("Level") or "").strip(),
                "label": (r.get("AHU Label") or "").strip(),
                "device_id": (r.get("device_id") or "").strip(),
                "remark": (r.get("Remark") or "").strip(),
                "dept": (r.get("Department Name") or "").strip(),
            }
            rows.append(rec)
            by_norm[norm(rec["label"])].append(rec)
    return rows, by_norm


# ── 2. EMS (electrical) availability per device ────────────────────────────────
def load_ems() -> dict[str, dict]:
    """Return {ahu_id: {min_ts, max_ts, metrics:[...]}} merged across both DuckDBs."""
    out: dict[str, dict] = {}
    raw_cols = [f"raw_{m}" for m in EMS_METRICS]
    for db in EMS_DBS:
        if not db.exists():
            continue
        con = duckdb.connect(str(db), read_only=True)
        # which raw_ columns exist in this db
        cols_here = {
            r[0] for r in con.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name='health_hourly'"
            ).fetchall()
        }
        present = [c for c in raw_cols if c in cols_here]
        cnt_sql = ", ".join(f"COUNT({c}) AS {c}" for c in present)
        q = (
            f"SELECT ahu_id, MIN(timestamp) mn, MAX(timestamp) mx, {cnt_sql} "
            f"FROM health_hourly GROUP BY ahu_id"
        )
        for row in con.execute(q).fetchall():
            ahu = row[0]
            mn, mx = row[1], row[2]
            counts = dict(zip(present, row[3:]))
            metrics = [c[4:] for c in present if counts.get(c, 0) and counts[c] > 0]
            e = out.setdefault(ahu, {"min_ts": mn, "max_ts": mx, "metrics": set()})
            if mn and (e["min_ts"] is None or mn < e["min_ts"]):
                e["min_ts"] = mn
            if mx and (e["max_ts"] is None or mx > e["max_ts"]):
                e["max_ts"] = mx
            e["metrics"].update(metrics)
        con.close()
    for e in out.values():
        e["metrics"] = sorted(e["metrics"])
    return out


# ── 3. BMS (HVAC) availability per device ──────────────────────────────────────
PTN = re.compile(r"^(.*_\d{2})_([A-Za-z].*)$")


def load_bms() -> tuple[dict[str, dict], list[str]]:
    """Return {bms_device: {points:set, min_ts, max_ts}} for AHU devices, + unparseable items."""
    # all AHU items
    rows = flux(
        f'import "influxdata/influxdb/schema" '
        f'schema.tagValues(bucket: "{BMS_BUCKET}", tag: "item")'
    )
    items = [r[-1] for r in rows if r and r[-1] not in ("_value", "")]
    items = [i for i in items if i.upper().startswith("AHU")]

    dev_points: dict[str, set] = defaultdict(set)
    unparsed = []
    for it in items:
        m = PTN.match(it)
        if not m:
            unparsed.append(it)
            continue
        dev_points[m.group(1)].add(m.group(2))

    # min/max ts per item (first/last across all time), then aggregate to device
    dev_min: dict[str, str] = {}
    dev_max: dict[str, str] = {}
    for agg, store in (("first", dev_min), ("last", dev_max)):
        q = (
            f'from(bucket:"{BMS_BUCKET}") |> range(start: 0) '
            f'|> filter(fn:(r)=> r._measurement=="bacnet_points" and r.item =~ /^AHU/) '
            f'|> {agg}() |> keep(columns:["item","_time"])'
        )
        res = flux(q)
        if not res:
            continue
        header = res[0]
        try:
            ti, tt = header.index("item"), header.index("_time")
        except ValueError:
            continue
        for r in res[1:]:
            if len(r) <= max(ti, tt):
                continue
            it, t = r[ti], r[tt]
            m = PTN.match(it)
            if not m:
                continue
            d = m.group(1)
            if agg == "first":
                if d not in store or t < store[d]:
                    store[d] = t
            else:
                if d not in store or t > store[d]:
                    store[d] = t

    out = {}
    for d, pts in dev_points.items():
        out[d] = {"points": sorted(pts), "min_ts": dev_min.get(d), "max_ts": dev_max.get(d)}
    return out, sorted(set(unparsed))


def fmt_ts(ts) -> str:
    if ts is None:
        return "—"
    if isinstance(ts, datetime):
        return ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    s = str(ts)
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return s


def group_bms_by_norm(bms: dict[str, dict]) -> dict[str, dict]:
    """Merge BMS device-name variants that share a normalized key.

    BMS has stray duplicate prefixes (e.g. AHU_L1_ES_01 vs AHU_AHU_L1_ES_01) that
    refer to the same physical AHU. Union their points and time ranges.
    """
    grouped: dict[str, dict] = {}
    for name, rec in bms.items():
        k = norm(name)
        g = grouped.setdefault(k, {"points": set(), "min_ts": None, "max_ts": None, "names": []})
        g["names"].append(name)
        g["points"].update(rec["points"])
        for fld, better in (("min_ts", lambda a, b: b < a), ("max_ts", lambda a, b: b > a)):
            v = rec[fld]
            if v and (g[fld] is None or better(g[fld], v)):
                g[fld] = v
    for g in grouped.values():
        g["points"] = sorted(g["points"])
        # canonical name = the variant contributing the most points (longest set proxy)
        g["names"].sort(key=lambda n: (-len(bms[n]["points"]), n))
        g["name"] = g["names"][0]
    return grouped


def main() -> int:
    tsv_rows, tsv_by_norm = load_tsv()
    ems = load_ems()
    bms_raw, bms_unparsed = load_bms()
    bms = group_bms_by_norm(bms_raw)  # key -> {points, min_ts, max_ts, names, name}
    bms_by_norm = bms

    # Build the device universe keyed by normalized label.
    keys = set(tsv_by_norm) | set(bms_by_norm)
    # also EMS-only devices (e-ids not in tsv) -> map via tsv device_id
    devid_to_norm = {}
    for k, recs in tsv_by_norm.items():
        for r in recs:
            if r["device_id"]:
                devid_to_norm[r["device_id"]] = k
    ems_extra = [a for a in ems if a not in devid_to_norm]

    lines: list[str] = []
    A = lines.append

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    A("# WACH Data Inventory — One-Stop Reference")
    A("")
    A(f"_Generated: {now} by `scripts/research/build_data_inventory.py`._")
    A("")
    A("Single source of truth for **what data exists for WACH**, per device, across the two")
    A("disconnected systems: **EMS** (electrical power meters) and **BMS** (HVAC/BACnet controls).")
    A("")

    # Connection / source summary
    A("## 1. Data Sources")
    A("")
    A("| System | What | Host | Bucket | Measurement | Schema |")
    A("|---|---|---|---|---|---|")
    A(f"| **EMS** | Electrical power-meter telemetry (46 metrics) | `178.128.53.199:8086` (public) | `{EMS_BUCKET}` | per-metric | wide |")
    A(f"| **BMS** | HVAC/BACnet control points | `172.17.84.201:8086` (private LAN) | `{BMS_BUCKET}` | `bacnet_points` | long (`item` tag + `value`) |")
    A("")
    A("> EMS hot/processed layer lives locally in DuckDB (`backend/data/healthdb.duckdb` + archive `data/healthdb.duckdb`).")
    A("> BMS is queried live from Influx. The two systems use **different device-ID schemes** and **different time spans** — see §2 and the caveats in §6.")
    A("")

    # Global time ranges
    ems_min = min((e["min_ts"] for e in ems.values() if e["min_ts"]), default=None)
    ems_max = max((e["max_ts"] for e in ems.values() if e["max_ts"]), default=None)
    bms_min = min((v["min_ts"] for v in bms.values() if v["min_ts"]), default=None)
    bms_max = max((v["max_ts"] for v in bms.values() if v["max_ts"]), default=None)
    A("## 2. Coverage Summary")
    A("")
    A("| | EMS (electrical) | BMS (HVAC) |")
    A("|---|---|---|")
    A(f"| Devices with data | {len(ems)} | {len(bms)} |")
    A(f"| Earliest timestamp | {fmt_ts(ems_min)} | {fmt_ts(bms_min)} |")
    A(f"| Latest timestamp | {fmt_ts(ems_max)} | {fmt_ts(bms_max)} |")
    A(f"| Metrics per device | up to {len(EMS_METRICS)} (uniform) | varies (≈30–40, per AHU type) |")
    A("")
    matched = sum(1 for k in keys if tsv_by_norm.get(k) and bms_by_norm.get(k))
    A(f"- TSV mapping rows: **{len(tsv_rows)}**  ·  unique device labels: **{len(tsv_by_norm)}**")
    A(f"- Devices matched **both** EMS and BMS (via label↔name join): **{matched}**")
    A(f"- BMS AHU items that could not be parsed into device+point: **{len(bms_unparsed)}**")
    A("")

    # Per-device table
    A("## 3. Per-Device Inventory")
    A("")
    A("Columns: device_id (EMS) · BMS device name · level/dept · EMS start · BMS start · #EMS metrics · #BMS points.")
    A("`—` = not present in that system. See §4/§5 for the metric/point lists.")
    A("")
    A("| device_id | BMS name | Level | Dept | EMS start | BMS start | EMS metrics | BMS points |")
    A("|---|---|---|---|---|---|---:|---:|")

    detail_blocks: list[str] = []

    def add_row(device_id, bms_name, level, dept, e_rec, b_rec, anchor):
        e_start = fmt_ts(e_rec["min_ts"]) if e_rec else "—"
        b_start = fmt_ts(b_rec["min_ts"]) if b_rec else "—"
        n_e = len(e_rec["metrics"]) if e_rec else 0
        n_b = len(b_rec["points"]) if b_rec else 0
        did = device_id or "**(no id)**"
        bn = bms_name or "—"
        A(f"| {did} | {bn} | {level or '—'} | {dept or '—'} | {e_start} | {b_start} | {n_e or '—'} | {n_b or '—'} |")
        # detail block
        db = [f"### {did} · {bn}", ""]
        db.append(f"- **Level / Dept:** {level or '—'} / {dept or '—'}")
        db.append(f"- **EMS:** " + (
            f"start {e_start}, end {fmt_ts(e_rec['max_ts'])}, {n_e} metrics" if e_rec else "**none** (not in electrical bucket)"))
        db.append(f"- **BMS:** " + (
            f"start {b_start}, end {fmt_ts(b_rec['max_ts'])}, {n_b} points" if b_rec else "**none** (not in BMS bucket)"))
        if b_rec:
            if len(b_rec.get("names", [])) > 1:
                db.append(f"- **BMS name variants:** {', '.join(b_rec['names'])}")
            db.append(f"- **BMS points:** {', '.join(b_rec['points'])}")
        if not e_rec and not b_rec:
            db.append("- ⚠️ **No EMS and no BMS data for this device.**")
        db.append("")
        detail_blocks.append("\n".join(db))

    seen_bms = set()
    # iterate TSV labels (sorted by device_id then label)
    def sort_key(k):
        recs = tsv_by_norm.get(k, [])
        did = next((r["device_id"] for r in recs if r["device_id"]), "zzzz")
        return (did, k)

    for k in sorted(keys, key=sort_key):
        recs = tsv_by_norm.get(k, [])
        b_rec = bms_by_norm.get(k)
        bms_name = b_rec["name"] if b_rec else None
        if bms_name:
            seen_bms.add(bms_name)
        if recs:
            # one row per distinct device_id label (collapse dup labels)
            r0 = recs[0]
            device_id = next((r["device_id"] for r in recs if r["device_id"]), "")
            e_rec = ems.get(device_id) if device_id else None
            add_row(device_id, bms_name, r0["level"], r0["dept"], e_rec, b_rec, k)
        else:
            # BMS device with no TSV label
            add_row("", bms_name, "", "", None, b_rec, k)

    # EMS-only devices (e-ids present electrically but no TSV label)
    for ahu in sorted(ems_extra):
        add_row(ahu, None, "", "", ems[ahu], None, ahu)

    A("")
    A("## 4. EMS Metric Catalog (46 electrical metrics)")
    A("")
    A("Uniform across all EMS devices. Source bucket `wach_bucket_3`, hourly in the hot layer.")
    A("")
    for m in EMS_METRICS:
        A(f"- `{m}`")
    A("")
    A("> Derived/engineered columns also stored in the health layer (not raw EMS):")
    A("> `composite_thd`, `nema_voltage_imbalance`, `p95_current`, `hourly_delta`, `predicted_delta`, `energy_anomaly_raw`.")
    A("")

    A("## 5. BMS Point Glossary (observed point-type suffixes)")
    A("")
    all_pts = sorted({p for v in bms.values() for p in v["points"]})
    gloss = {
        "AM": "Auto/Manual selection status (binary)",
        "SS": "Start/Stop command (binary)",
        "STS": "Operational status (binary)",
        "TRIP": "Trip alarm status (binary)",
        "RunTime": "Accumulated run time (hours)",
        "OCT": "Occupancy status (binary)",
        "RAT": "Return air temperature (°C)",
        "RATSp": "Return air temperature setpoint (°C)",
        "RATHiAlmLmt": "Return air temp high alarm limit (°C)",
        "RATLoAlmLmt": "Return air temp low alarm limit (°C)",
        "DefaultRATSp": "Default RAT setpoint (°C)",
        "UserRATSp": "User RAT setpoint (°C)",
        "WST": "Chilled water supply temperature (°C)",
        "WRT": "Chilled water return temperature (°C)",
        "HWST": "Hot water supply temperature (°C)",
        "HWS": "Hot water supply status/temp",
        "CO2": "CO2 level (ppm)",
        "CO2SP": "CO2 setpoint (ppm)",
        "CO2_P": "CO2 PID proportional term",
        "CO2_I": "CO2 PID integral term",
        "RAH": "Return air humidity (%RH)",
        "RH": "Relative humidity (%RH)",
        "RAHSp": "Return air humidity setpoint (%RH)",
        "DSP": "Duct static pressure (Pa)",
        "DSPSP": "Duct static pressure setpoint (Pa)",
        "DSPNew": "Duct static pressure (alt point) (Pa)",
        "DP": "Differential pressure (Pa)",
        "FaDmpr": "Fresh air damper position (%)",
        "FaDmprMin": "Fresh air damper minimum position (%)",
        "MVLV": "Modulating valve position (%)",
        "HWVLV": "Hot water valve position (%)",
        "MCVLV": "Mixing cooling valve position (%)",
        "MHVLV": "Mixing heating valve position (%)",
        "VSD": "Variable speed drive speed (%)",
        "VSDCTRL": "VSD control signal (%)",
        "VSDFB": "VSD feedback (%)",
        "Clg_P": "Cooling PID proportional term",
        "Clg_I": "Cooling PID integral term",
        "Heat_P": "Heating PID proportional term",
        "Heat_I": "Heating PID integral term",
        "FLTR": "Air filter status/alarm (binary)",
        "AlmEnaDly": "Alarm enable delay (sec)",
        "FailDly": "Failure delay (sec)",
        "SSDly": "Start/Stop delay (sec)",
        "TimeStart": "Scheduled start time",
        "TimeStop": "Scheduled stop time",
        "TotalTons": "Total cooling load (Tons)",
    }
    A("| Point | Meaning | Observed in data |")
    A("|---|---|---|")
    for p in sorted(set(all_pts) | set(gloss)):
        meaning = gloss.get(p, "_(undocumented)_")
        seen = "✅" if p in all_pts else "—"
        A(f"| `{p}` | {meaning} | {seen} |")
    A("")

    # caveats
    A("## 6. Caveats / Known Gaps")
    A("")
    A("- **Device-ID schemes differ.** EMS uses `e0101`; BMS uses `AHU_L10_PM1_01`. Join is via the")
    A("  TSV `AHU Label` normalized to a key (strip leading `AHU` + separators). Some TSV rows have")
    A("  no `device_id` (see §3 rows marked `(no id)`); some BMS devices have no TSV match.")
    A("- **Time spans differ.** EMS history reaches back further than BMS; joined rows only exist")
    A("  from the later BMS start. See §2.")
    A("- **BMS point sets vary per AHU** (cooling-only AHUs lack hot-water/heating points; only")
    A("  AHUs with a BTU meter expose `TotalTons`).")
    if bms_unparsed:
        A(f"- **{len(bms_unparsed)} BMS items unparsed** (did not match `<device>_<NN>_<point>`):")
        A("  ```")
        for u in bms_unparsed[:40]:
            A(f"  {u}")
        if len(bms_unparsed) > 40:
            A(f"  … (+{len(bms_unparsed) - 40} more)")
        A("  ```")
    A("- **EMS token rejected** for the public bucket during this run; EMS facts come from the local")
    A("  DuckDB layers, which may lag the live electrical bucket.")
    A("")

    A("## 7. Per-Device Detail")
    A("")
    lines.extend(detail_blocks)

    OUT.write_text("\n".join(lines))
    print(f"Wrote {OUT}  ({len(lines)} lines)")
    print(f"EMS devices={len(ems)} BMS devices={len(bms)} matched_both={matched} bms_unparsed={len(bms_unparsed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
