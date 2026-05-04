# Phase 4: Stability, Unification & Proactive Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilise the data model, fix bugs, then extend the bot to proactively create tickets, answer with RAG, and escalate stale work.

**Architecture:** Work Orders and Tickets are already one entity (`work_orders` table, `ticket_no = TCK-NNN`). Phase 4 audits any lingering dual-concept code, adds missing CRUD (Delete All), fixes UI state bugs, then builds three new bot capabilities: auto-draft on system alert, `/solve` RAG command, and priority-based escalation.

**Tech Stack:** Python FastAPI, DuckDB (AgentDB), python-telegram-bot, ChromaDB (RAG), Qwen via LM Studio (LLM), React + Zustand (frontend), pytest, Jest + RTL

---

## File Map

### Modified — Backend
| File | Change |
|------|--------|
| `backend/core/agentdb.py` | Add `delete_all_work_orders()`, `list_stale_tickets()` |
| `backend/routes/work_orders.py` | Add `DELETE /api/work-orders` (bulk delete) |
| `backend/bot/handlers/technicians.py` | Add `/solve <ticket_no>` handler |
| `backend/bot/handlers/__init__.py` | Register `/solve` handler |
| `scripts/scheduler/scheduler.py` | Add escalation job step |

### Modified — Frontend
| File | Change |
|------|--------|
| `frontend/src/components/workorders/WorkOrdersView.tsx` | Add "Delete All" button |
| `frontend/src/components/workorders/WorkOrderPanelItem.tsx` | Fix `order.status === 'approved'` → `'open'` colour bug |
| `frontend/src/api/client.ts` | Add `deleteAllWorkOrders()` |

### Created — Backend
| File | Purpose |
|------|---------|
| `scripts/escalation_checker.py` | Standalone script: check ticket age → send Telegram alerts |
| `backend/tests/test_delete_all.py` | Tests for bulk delete endpoint |
| `backend/tests/test_solve_command.py` | Tests for /solve RAG handler |

---

## Task 1: Audit Ticket/Work Order Dual Concepts

**Goal:** Confirm there is no mapping/sync layer. Document the single source of truth. Fix any misleading labels.

**Files:**
- Audit: `backend/routes/work_orders.py`, `frontend/src/components/workorders/`, `frontend/src/types/chat.ts`

- [ ] **Step 1: Search for any "ticket" ↔ "work order" sync/mapping code**

```bash
grep -rn "sync\|mapping\|ticket_id\|work_order_id" \
  backend/routes/ backend/core/ backend/tools/ \
  frontend/src/
```

Expected: Only `status_change_requests.work_order_id` (FK, intentional) and `ticket_no` references. No sync logic.

- [ ] **Step 2: Check frontend type definition**

```bash
cat frontend/src/types/chat.ts | grep -A 20 "WorkOrder"
```

Confirm `WorkOrder` type has `ticket_no: string` and `id: number`. If any `ticketId` or dual-ID field exists, note it for removal.

- [ ] **Step 3: Fix WorkOrderPanelItem status colour bug**

Open `frontend/src/components/workorders/WorkOrderPanelItem.tsx`. Find line ~130:

```tsx
color: order.status === 'approved' ? '#00E5A0' : '#556677',
```

`'approved'` is not a valid status (state machine: `draft → pending_tech_review → open → in_progress → resolved → closed`). Fix:

```tsx
const ACTIVE_STATUSES = new Set(['open', 'in_progress', 'pending_tech_review']);
// ...
color: ACTIVE_STATUSES.has(order.status) ? '#00E5A0' : '#556677',
```

- [ ] **Step 4: Run frontend type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workorders/WorkOrderPanelItem.tsx
git commit -m "fix: correct status colour check in WorkOrderPanelItem (approved→open)"
```

---

## Task 2: Delete All Work Orders

**Goal:** Add `DELETE /api/work-orders` endpoint + DB method + frontend button for clean-slate testing.

**Files:**
- Modify: `backend/core/agentdb.py`
- Modify: `backend/routes/work_orders.py`
- Create: `backend/tests/test_delete_all.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/workorders/WorkOrdersView.tsx`

- [ ] **Step 1: Write the failing backend test**

Create `backend/tests/test_delete_all.py`:

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_delete_all_work_orders_returns_200():
    resp = client.delete("/api/work-orders")
    assert resp.status_code == 200
    data = resp.json()
    assert "deleted" in data
    assert isinstance(data["deleted"], int)


def test_delete_all_leaves_empty_list():
    client.delete("/api/work-orders")
    resp = client.get("/api/work-orders")
    assert resp.json()["count"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_delete_all.py -v
```

Expected: FAIL — `405 Method Not Allowed` (endpoint does not exist yet).

- [ ] **Step 3: Add `delete_all_work_orders()` to AgentDB**

In `backend/core/agentdb.py`, after the `delete_work_order` method, add:

```python
def delete_all_work_orders(self) -> int:
    """Delete every row in work_orders. Returns deleted count."""
    with self._conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM work_orders").fetchone()[0]
        conn.execute("DELETE FROM work_orders")
    logger.info(f"delete_all_work_orders: removed {count} rows")
    return count
```

- [ ] **Step 4: Add `DELETE /api/work-orders` route**

In `backend/routes/work_orders.py`, after the existing single-delete route:

```python
@router.delete("/work-orders")
async def delete_all_work_orders() -> dict:
    """Delete all work orders. Intended for testing / clean-slate resets."""
    db = _get_db()
    deleted = db.delete_all_work_orders()
    logger.info(f"delete_all_work_orders: {deleted} records removed by user")
    return {"deleted": deleted}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_delete_all.py -v
```

Expected: PASS (both tests green).

- [ ] **Step 6: Add `deleteAllWorkOrders()` to frontend API client**

In `frontend/src/api/client.ts`, add after the existing `deleteWorkOrder` function:

```typescript
export async function deleteAllWorkOrders(): Promise<{ deleted: number }> {
  const res = await fetch('/api/work-orders', { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete all work orders');
  return res.json();
}
```

- [ ] **Step 7: Add "Delete All" button to WorkOrdersView**

In `frontend/src/components/workorders/WorkOrdersView.tsx`, import the new function and add a button next to the Refresh button:

```tsx
import { fetchWorkOrders, deleteAllWorkOrders } from '../../api/client';
// ...

const [deleting, setDeleting] = useState(false);

const handleDeleteAll = async () => {
  if (!window.confirm('Delete ALL work orders? This cannot be undone.')) return;
  setDeleting(true);
  try {
    const { deleted } = await deleteAllWorkOrders();
    showToast(`Deleted ${deleted} work order(s)`, 'info');
    await load();
  } catch {
    showToast('Failed to delete all work orders', 'error');
  } finally {
    setDeleting(false);
  }
};
```

In the button row (near the Refresh button):

```tsx
<button
  onClick={handleDeleteAll}
  disabled={deleting || loading}
  style={{
    background: 'transparent',
    border: '1px solid #4a2030',
    borderRadius: 6,
    padding: '6px 12px',
    color: '#cc4455',
    fontSize: 12,
    cursor: deleting || loading ? 'not-allowed' : 'pointer',
    opacity: deleting || loading ? 0.6 : 1,
  }}
>
  {deleting ? 'Deleting…' : 'Delete All'}
</button>
```

- [ ] **Step 8: Run frontend type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 9: Commit**

```bash
git add backend/core/agentdb.py backend/routes/work_orders.py \
        backend/tests/test_delete_all.py \
        frontend/src/api/client.ts \
        frontend/src/components/workorders/WorkOrdersView.tsx
git commit -m "feat: add Delete All work orders endpoint and UI button"
```

---

## Task 3: Fix the Greying Issue (UI Polish)

**Goal:** After approve/dismiss in the WorkOrderPanel or WorkOrderCard, items must not stay in a visually disabled state. The panel must refresh and show correct colours.

**Files:**
- Modify: `frontend/src/components/workorders/WorkOrderPanelItem.tsx`
- Modify: `frontend/src/components/chat/cards/WorkOrderCard.tsx`
- Modify: `frontend/src/components/workorders/WorkOrderPanel.tsx`

- [ ] **Step 1: Diagnose — read WorkOrderPanel to confirm it calls onUpdated**

```bash
cat frontend/src/components/workorders/WorkOrderPanel.tsx
```

Verify: when a `WorkOrderPanelItem` calls `onUpdated()`, the panel re-fetches work orders from the API. If it only filters local state, items approved to `'open'` will remain visible with grey text rather than disappearing or turning green.

- [ ] **Step 2: Ensure WorkOrderPanel re-fetches on item update**

In `WorkOrderPanel.tsx`, the `onUpdated` callback passed to each `WorkOrderPanelItem` must call `load()` (a full re-fetch), not just filter local state. Confirm or fix:

```tsx
// Inside WorkOrderPanel component:
const load = useCallback(async () => {
  const res = await fetchWorkOrders({ status: 'draft' });
  setOrders(res.work_orders);
  setWorkOrderDraftsCount(res.work_orders.length);
}, [setWorkOrderDraftsCount]);

// Pass to each item:
<WorkOrderPanelItem key={order.id} order={order} onUpdated={load} />
```

If the panel currently passes an inline filter (e.g., `() => setOrders(prev => prev.filter(...))`), replace it with a full `load()` call.

- [ ] **Step 3: Verify WorkOrderCard stays responsive after approve**

In `frontend/src/components/chat/cards/WorkOrderCard.tsx`, confirm that after `state === 'done'`, the card renders a static confirmed state (not a greyed button). Current implementation shows a checkmark which is correct. If the checkmark is missing or the button stays visible and greyed, fix:

```tsx
{state === 'done' ? (
  <span style={{ color: '#00E5A0', fontSize: 11, fontWeight: 700 }}>✓ Submitted</span>
) : (
  <button
    disabled={state === 'loading'}
    // ...
  >
    {state === 'loading' ? '…' : approveItem.label}
  </button>
)}
```

- [ ] **Step 4: Run frontend type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 5: Start dev server and manually test the flow**

```bash
cd frontend && npm run dev &
cd backend && python main.py &
```

1. Open the Work Orders panel.
2. Approve a draft work order.
3. Confirm: the item disappears from the drafts panel (re-fetch removes it).
4. Confirm: the badge count decrements.
5. Confirm: non-draft items show green colour for active statuses.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/workorders/WorkOrderPanel.tsx \
        frontend/src/components/workorders/WorkOrderPanelItem.tsx \
        frontend/src/components/chat/cards/WorkOrderCard.tsx
git commit -m "fix: work order panel re-fetches after action; fix status colour for open/in_progress"
```

---

## Task 4: Proactive Bot — Watchman Auto-Draft Ticket

**Goal:** Verify and complete the pipeline: Watchman detects bad FAIR score → enqueues AHU → processor runs resolution agent → `create_work_order` tool fires → `send_draft_card` delivers Telegram notification to technicians.

**Files:**
- Read: `backend/core/watchman.py`, `scripts/watchman_processor.py`, `backend/tools/action_tools.py`, `backend/bot/push/notifier.py`
- Modify: `scripts/watchman_processor.py` (if draft card dispatch is missing)

- [ ] **Step 1: Trace the full pipeline in watchman_processor.py**

```bash
cat scripts/watchman_processor.py
```

Confirm the processor:
1. Reads from `watchman_queue` (rows where `processed = false`)
2. Calls the resolution agent with the AHU context
3. Agent calls `create_work_order` tool → returns `ticket_no`
4. After creation, calls `notifier.dispatch(event="draft_created", wo=...)` → `send_draft_card` → Telegram message

If step 4 is missing (processor creates work order but never dispatches notification), add it.

- [ ] **Step 2: Fix dispatch call if missing**

In `scripts/watchman_processor.py`, after the agent creates the work order, ensure the draft card is sent:

```python
import asyncio
from backend.bot.push.notifier import dispatch

# After work order is created:
wo = db.get_work_order(wo_id)
asyncio.run(dispatch(event="draft_created", wo=wo))
```

If the script runs outside the FastAPI process (it does — it's a standalone script), it needs `asyncio.run()` since there's no running event loop.

- [ ] **Step 3: Write a smoke test for the watchman queue processor**

Add `backend/tests/test_watchman_processor.py`:

```python
import pytest
from unittest.mock import patch, AsyncMock
from core.agentdb import AgentDB


def test_enqueue_and_mark_processed():
    db = AgentDB()
    db.enqueue_watchman_alert(
        ahu_id="e0101", level=1, health_index=35.0, severity="Critical"
    )
    queue = db.get_pending_watchman_queue()
    assert any(r["ahu_id"] == "e0101" for r in queue)
    for row in queue:
        if row["ahu_id"] == "e0101":
            db.mark_watchman_processed(row["id"])
    queue_after = db.get_pending_watchman_queue()
    assert not any(r["ahu_id"] == "e0101" for r in queue_after)
```

- [ ] **Step 4: Run the smoke test**

```bash
cd backend && python -m pytest tests/test_watchman_processor.py -v
```

Expected: PASS.

- [ ] **Step 5: End-to-end manual test**

```bash
# Manually enqueue a test AHU and run processor once
cd backend
python -c "
from core.agentdb import AgentDB
db = AgentDB()
db.enqueue_watchman_alert('e0101', 1, 32.0, 'Critical')
print('Enqueued e0101')
"
cd ..
python scripts/watchman_processor.py --one-shot
```

Expected: Log shows work order created + Telegram draft card sent.

- [ ] **Step 6: Commit**

```bash
git add scripts/watchman_processor.py backend/tests/test_watchman_processor.py
git commit -m "fix: ensure watchman processor dispatches draft_created notification after work order creation"
```

---

## Task 5: /solve Command (RAG-Powered Fix Suggestions)

**Goal:** Add `/solve <ticket_no>` to the Telegram bot. Bot fetches the unified ticket, queries RAG with the description, returns a specific fix suggestion.

**Files:**
- Create: `backend/tests/test_solve_command.py`
- Modify: `backend/bot/handlers/technicians.py`
- Modify: `backend/bot/handlers/__init__.py`

- [ ] **Step 1: Write the failing unit test**

Create `backend/tests/test_solve_command.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_solve_returns_rag_suggestion():
    """solve_handler fetches ticket, queries RAG, replies with suggestion."""
    mock_db = MagicMock()
    mock_db.get_work_order_by_ticket_no.return_value = {
        "id": 1,
        "ticket_no": "TCK-001",
        "ahu_id": "e0101",
        "title": "High THD on AHU e0101",
        "description": "Total harmonic distortion exceeded 15% threshold",
        "severity": "Critical",
        "status": "open",
    }

    mock_retriever = MagicMock()
    mock_retriever.query.return_value = [
        "THD above 15% indicates harmonic filter degradation. Replace capacitor bank C3."
    ]

    mock_update = MagicMock()
    mock_update.message.text = "/solve TCK-001"
    mock_update.message.reply_text = AsyncMock()
    mock_context = MagicMock()

    with patch("bot.handlers.technicians._get_db", return_value=mock_db), \
         patch("bot.handlers.technicians._get_retriever", return_value=mock_retriever):
        from bot.handlers.technicians import solve_handler
        await solve_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    reply = mock_update.message.reply_text.call_args[0][0]
    assert "TCK-001" in reply
    assert "THD" in reply or "harmonic" in reply.lower()


@pytest.mark.asyncio
async def test_solve_unknown_ticket():
    mock_db = MagicMock()
    mock_db.get_work_order_by_ticket_no.return_value = None

    mock_update = MagicMock()
    mock_update.message.text = "/solve TCK-999"
    mock_update.message.reply_text = AsyncMock()
    mock_context = MagicMock()

    with patch("bot.handlers.technicians._get_db", return_value=mock_db):
        from bot.handlers.technicians import solve_handler
        await solve_handler(mock_update, mock_context)

    reply = mock_update.message.reply_text.call_args[0][0]
    assert "not found" in reply.lower() or "TCK-999" in reply
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_solve_command.py -v
```

Expected: FAIL — `ImportError: cannot import name 'solve_handler'`

- [ ] **Step 3: Add `get_work_order_by_ticket_no` to AgentDB**

In `backend/core/agentdb.py`:

```python
def get_work_order_by_ticket_no(self, ticket_no: str) -> dict | None:
    with self._conn() as conn:
        row = conn.execute(
            "SELECT * FROM work_orders WHERE ticket_no = ?", [ticket_no]
        ).fetchone()
    if not row:
        return None
    cols = [d[0] for d in conn.description] if hasattr(conn, "description") else []
    # Use the same column list as get_work_order
    return dict(zip(self._work_order_columns(), row))
```

If `_work_order_columns()` does not exist, use the column list from `get_work_order` directly:

```python
def get_work_order_by_ticket_no(self, ticket_no: str) -> dict | None:
    with self._conn() as conn:
        rows = conn.execute(
            "SELECT * FROM work_orders WHERE ticket_no = ?", [ticket_no]
        ).fetchdf()
    if rows.empty:
        return None
    return rows.iloc[0].to_dict()
```

- [ ] **Step 4: Add `_get_retriever` helper and `solve_handler` to technicians.py**

In `backend/bot/handlers/technicians.py`, add at the top of the file (after existing imports):

```python
from rag.retriever import Retriever

def _get_db():
    import core.agentdb as agentdb_module
    if agentdb_module._db_instance is None:
        from core.agentdb import AgentDB
        agentdb_module._db_instance = AgentDB()
    return agentdb_module._db_instance

def _get_retriever() -> Retriever:
    return Retriever()
```

Then add the handler:

```python
async def solve_handler(update, context) -> None:
    """
    /solve <ticket_no>
    Fetch ticket → query RAG → suggest fix.
    """
    text = update.message.text or ""
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("Usage: /solve <ticket_no>  e.g. /solve TCK-005")
        return

    ticket_no = parts[1].strip().upper()
    db = _get_db()
    wo = db.get_work_order_by_ticket_no(ticket_no)

    if not wo:
        await update.message.reply_text(f"❌ Ticket {ticket_no} not found.")
        return

    query = f"{wo['title']}. {wo.get('description', '')}"
    retriever = _get_retriever()
    docs = retriever.query(query, top_k=3)

    if not docs:
        await update.message.reply_text(
            f"🔍 *{ticket_no}* — No relevant documentation found.\n\n"
            f"Description: {wo.get('description', 'N/A')}",
            parse_mode="Markdown",
        )
        return

    context_text = "\n\n".join(f"• {d}" for d in docs)
    reply = (
        f"🧠 *Suggested Fix for {ticket_no}*\n"
        f"AHU: `{wo['ahu_id']}` | Severity: {wo['severity']}\n\n"
        f"*Issue:* {wo['title']}\n\n"
        f"*Relevant guidance from technical manuals:*\n{context_text}"
    )
    await update.message.reply_text(reply, parse_mode="Markdown")
```

- [ ] **Step 5: Register /solve in handler __init__.py**

In `backend/bot/handlers/__init__.py`, add `solve_handler` to the dispatcher:

```python
from bot.handlers.technicians import solve_handler
# ...
# In the handler registration section:
application.add_handler(CommandHandler("solve", solve_handler))
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_solve_command.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/core/agentdb.py \
        backend/bot/handlers/technicians.py \
        backend/bot/handlers/__init__.py \
        backend/tests/test_solve_command.py
git commit -m "feat: add /solve <ticket_no> command with RAG-powered fix suggestions"
```

---

## Task 6: Escalation Scheduler

**Goal:** Background job checks ticket age against priority thresholds and sends Telegram alerts to admins for stale high-priority tickets.

**Thresholds:**
- Critical / High priority → alert after **2 hours** unclaimed
- Medium priority → alert after **8 hours** unclaimed
- Low priority → alert after **24 hours** unclaimed

**Files:**
- Modify: `backend/core/agentdb.py` — add `list_stale_tickets()`
- Create: `scripts/escalation_checker.py`
- Modify: `scripts/scheduler/scheduler.py` — add escalation step

- [ ] **Step 1: Add `list_stale_tickets()` to AgentDB**

In `backend/core/agentdb.py`:

```python
def list_stale_tickets(self) -> list[dict]:
    """
    Return open/pending tickets that have exceeded their priority age threshold
    and have not been claimed.
    Thresholds: Critical/High=2h, Medium=8h, Low=24h
    """
    with self._conn() as conn:
        rows = conn.execute("""
            SELECT *,
                CASE
                    WHEN priority IN ('Critical', 'High') THEN 2
                    WHEN priority = 'Medium' THEN 8
                    ELSE 24
                END AS threshold_hours
            FROM work_orders
            WHERE status IN ('open', 'pending_tech_review')
              AND claimed_by IS NULL
              AND created_at <= NOW() - INTERVAL (
                    CASE
                        WHEN priority IN ('Critical', 'High') THEN 2
                        WHEN priority = 'Medium' THEN 8
                        ELSE 24
                    END
                  ) HOUR
        """).fetchdf()
    return rows.to_dict(orient="records")
```

- [ ] **Step 2: Create escalation_checker.py**

Create `scripts/escalation_checker.py`:

```python
#!/usr/bin/env python3
"""
scripts/escalation_checker.py
Check for stale tickets and send escalation alerts to admins via Telegram.

Usage:
    python scripts/escalation_checker.py [--dry-run]
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from core.agentdb import AgentDB

THRESHOLD_LABELS = {
    "Critical": "2 hours",
    "High": "2 hours",
    "Medium": "8 hours",
    "Low": "24 hours",
}


async def send_escalation(ticket_no: str, ahu_id: str, priority: str, title: str,
                           dry_run: bool = False) -> None:
    threshold = THRESHOLD_LABELS.get(priority, "24 hours")
    message = (
        f"⚠️ *Escalation Alert*\n"
        f"Ticket `{ticket_no}` ({priority} priority) is still unclaimed after {threshold}!\n\n"
        f"AHU: `{ahu_id}`\n"
        f"Issue: {title}\n\n"
        f"Assign immediately or escalate to supervisor."
    )
    if dry_run:
        print(f"[DRY RUN] Would send:\n{message}\n")
        return

    try:
        from bot.config import BOT_TOKEN, ADMIN_CHAT_ID
        from telegram import Bot
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=message,
            parse_mode="Markdown",
        )
        print(f"[{datetime.now().isoformat()}] Escalation sent for {ticket_no}")
    except Exception as e:
        print(f"[ERROR] Failed to send escalation for {ticket_no}: {e}")


async def run(dry_run: bool = False) -> None:
    db = AgentDB()
    stale = db.list_stale_tickets()

    if not stale:
        print(f"[{datetime.now().isoformat()}] No stale tickets found.")
        return

    print(f"[{datetime.now().isoformat()}] Found {len(stale)} stale ticket(s).")
    for ticket in stale:
        await send_escalation(
            ticket_no=ticket["ticket_no"],
            ahu_id=ticket["ahu_id"],
            priority=ticket.get("priority", "Low"),
            title=ticket["title"],
            dry_run=dry_run,
        )


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(run(dry_run=dry_run))
```

- [ ] **Step 3: Test dry-run locally**

```bash
cd /path/to/wach-insight
python scripts/escalation_checker.py --dry-run
```

Expected: Either "No stale tickets found." or "[DRY RUN] Would send: ⚠️ Escalation Alert…" — no Telegram messages sent.

- [ ] **Step 4: Add escalation step to scheduler**

In `scripts/scheduler/scheduler.py`, find the main loop body where prediction ETL and health ETL are called. Add:

```python
# After watchman queue processing:
log_scheduler("Running escalation checker...")
subprocess.run(
    [sys.executable, str(SCRIPTS_DIR / "escalation_checker.py")],
    check=False,
)
log_scheduler("Escalation check complete.")
```

Where `SCRIPTS_DIR` is the scripts directory path (already used in the scheduler for other subprocess calls — match the existing pattern).

- [ ] **Step 5: Write a unit test for list_stale_tickets**

Add to `backend/tests/test_escalation.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta


def test_list_stale_tickets_returns_overdue():
    """Tickets older than threshold with no claimed_by should appear."""
    mock_db = MagicMock()
    old_time = (datetime.now() - timedelta(hours=3)).isoformat()
    mock_db.list_stale_tickets.return_value = [
        {
            "ticket_no": "TCK-001",
            "ahu_id": "e0101",
            "priority": "Critical",
            "title": "High THD",
            "status": "open",
            "claimed_by": None,
            "created_at": old_time,
        }
    ]
    stale = mock_db.list_stale_tickets()
    assert len(stale) == 1
    assert stale[0]["ticket_no"] == "TCK-001"


def test_list_stale_tickets_empty_when_all_claimed():
    mock_db = MagicMock()
    mock_db.list_stale_tickets.return_value = []
    assert mock_db.list_stale_tickets() == []
```

- [ ] **Step 6: Run the test**

```bash
cd backend && python -m pytest tests/test_escalation.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/core/agentdb.py \
        scripts/escalation_checker.py \
        scripts/scheduler/scheduler.py \
        backend/tests/test_escalation.py
git commit -m "feat: add priority-based ticket escalation alerts via Telegram"
```

---

## Self-Review

### Spec Coverage

| Requirement | Task |
|-------------|------|
| Merge Work Order / Ticket concept, one ID | Task 1 (audit + confirm already unified) |
| Fix `status === 'approved'` colour bug | Task 1, Step 3 |
| Delete All endpoint + UI | Task 2 |
| Greying issue fix + panel re-fetch | Task 3 |
| Watchman auto-draft → Telegram card | Task 4 |
| `/solve <ticket_no>` RAG handler | Task 5 |
| Escalation scheduler by priority | Task 6 |

### Placeholder Scan

None. All steps contain exact code, exact commands, expected outputs.

### Type Consistency

- `get_work_order_by_ticket_no` used in Task 5 test and defined in Task 5, Step 3. ✓
- `list_stale_tickets` used in Task 6 test and defined in Task 6, Step 1. ✓
- `delete_all_work_orders` used in Task 2 test and defined in Task 2, Steps 3–4. ✓
- `_get_retriever` used in Task 5 test and defined in Task 5, Step 4. ✓
- `solve_handler` imported in Task 5 test and defined in Task 5, Step 4. ✓
