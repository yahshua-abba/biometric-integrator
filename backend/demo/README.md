# Mini Payroll demos

Both demos use synthetic employees, temporary SQLite databases and a loopback
Payroll HTTP API. They never load the desktop app's database or credentials,
contact real Payroll, or connect to biometric devices.

## Start

From the repository root with Python 3.10+ and Node 20+:

```bash
python3 -m venv /tmp/biometric-demo-venv
/tmp/biometric-demo-venv/bin/pip install requests
cd frontend
npm ci
npm run build:demo
cd ..
/tmp/biometric-demo-venv/bin/python backend/demo/server.py
```

Open **http://127.0.0.1:8877/retry/** for the actual Vue Retry Queue component,
connected to the shipping Python push service. This is a separate demo bundle;
its HTTP bridge adapter is never imported by the desktop application.
Stop with Ctrl+C to discard the temporary databases. Use `--port 8878` if needed.

## Manual retry walkthrough

1. **Run ordinary sync**. Two configured destinations attempt three synthetic
   records. Mara (4472, Aug 24) and Luis (8821, Aug 25) receive explicit employee
   mapping errors. Ana (9930, Aug 24) is saved by mini Payroll, but her per-record
   acknowledgement is deliberately omitted. The queue shows four failed
   destination records and two unconfirmed ones. Payroll shows one saved punch.
2. **Fix employee mappings**, then **Run ordinary sync** again. The request count
   stays at two: attempted records never re-enter ordinary sync automatically.
3. Filter both attendance dates to **2026-08-24**, select **Mara Santos**, and use
   **Select all filtered → Review & retry selected → Retry 2 records now**.
   Only Mara's two destinations are attempted; one succeeds and the other is
   recognized as an existing duplicate. Her entries leave the queue. Luis and
   Ana remain there, and the request count is now four.
4. Clear the employee selection. Ana's unconfirmed records remain. The review
   dialog requires checking Payroll before retrying. Her punch is already visible
   in the mini Payroll panel, so cancel the review rather than resending it.
5. **HR deletes saved logs**, then **Run ordinary sync**. The saved-record count
   stays at zero. Explicit manual retries can still recreate intentionally deleted
   logs, so HR must not select those logs for retry.
6. **Reset demo** restores fresh synthetic records. Fixing mappings does not retry;
   retries happen only through the dedicated page's reviewed selection.

The page also supports multiple employees, destination and status filters,
individual checkboxes, pagination, and selecting all filtered records across pages.

## Original deletion replay

Open **http://127.0.0.1:8877/**. This page needs no frontend build.

1. **Sync now** uploads the same punch through two configurations reaching one
   mini Payroll. The second receives HTTP 400 / error 120.
2. **Approve deletion in Payroll** removes the saved punch.
3. **Sync now** again. The legacy lane recreates it; the fixed lane makes no new
   request. Optional auto sync runs every five seconds.

The legacy adapter explicitly restores the old retry policy and disables duplicate
classification, only within this demo. The fixed lane uses PushService unchanged.

## Delivery behavior and limits

- A durable ledger claims each record by `sync_id` and configured destination slot
  before the attendance HTTP request. Ordinary sync only picks never-attempted
  records; manual retry only picks reviewed, unresolved destination records.
- Failure, timeout, malformed response, missing/conflicting acknowledgements, app
  restarts, expired authentication and HTTP redirects never trigger an automatic
  attendance resend. A 401 invalidates the token for a later explicit attempt.
- Explicit record rejection is shown as Failed. Missing or uncertain confirmation
  is shown as Unconfirmed. Recognized duplicates remain terminal Duplicate skipped.
- Existing saved errors migrate into manual review; ambiguous legacy errors are
  treated as Unconfirmed. Previously unrecorded attempts cannot be reconstructed.
- A process interrupted during a request leaves a persisted unconfirmed claim.
  Manual retry becomes available after a two-minute in-flight protection window.
- Delivery history survives attendance cleanup. Unresolved records are retained
  for HR review rather than silently aging out of the queue.
- History belongs to this database and configured slots. Replacing the database,
  using another installation, or a different source `sync_id` can bypass local
  history. Guaranteed prevention across all clients requires Payroll-side durable
  idempotency and deletion protection. No production Payroll API was changed.

## Checks

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q
cd frontend
npm test
npm run build
npm run build:demo
```
