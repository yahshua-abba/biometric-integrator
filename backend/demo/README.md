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

Open **http://127.0.0.1:8877/retry/** for the actual Vue Needs Attention component,
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
3. In **Failed → By employee**, filter both attendance dates to **2026-08-24**.
   Select **Mara Santos** in the employee table, then use
   **Review selected → Retry 2 uploads now**.
   Only Mara's two destinations are attempted; one succeeds and the other is
   recognized as an existing duplicate. Her entries leave the queue. Luis and
   Ana remain there, and the request count is now four.
4. Open the **Unconfirmed** tab. Ana's unconfirmed records remain. The review
   dialog requires checking Payroll before retrying. Her punch is already visible
   in the mini Payroll panel, so cancel the review rather than resending it.
5. **HR deletes saved logs**, then **Run ordinary sync**. The saved-record count
   stays at zero. Explicit manual retries can still recreate intentionally deleted
   logs, so HR must not select those logs for retry.
6. **Reset demo** restores fresh synthetic records. Fixing mappings does not retry;
   retries happen only through the dedicated page's reviewed selection.

The default view groups uploads by employee, with counts and attendance-date
ranges. **View logs** opens one employee's records. The employee filter is a
searchable popup with 20 results per page; it retains multiple chosen employees
across searches. The main table loads 25 rows at a time from SQLite (25/50/100
options), and shows Failed and Unconfirmed in separate tabs. **Review all filtered**
freezes up to 10,000 eligible uploads before confirmation; new arrivals are never
silently added. Larger selections require narrower filters.

## Full desktop app and volume example

Install the normal `backend/requirements.txt` desktop dependencies and build the
production frontend (`cd frontend && npm run build`). Then, from the repo root:

```bash
python backend/demo/desktop.py --large
```

This opens the actual PyQt app and QWebChannel bridge, with an isolated temporary
database and local mini Payroll at **http://127.0.0.1:8878/retry/**. No Vite server
is needed. The window title includes **TEST / Mini Payroll**. `--large` adds 300
synthetic employees, 12,000 attendance logs and 24,000 queued destination uploads.
These volume failures are seeded locally; subsequent retries use real loopback
HTTP. Employee mappings are already fixed for desktop retry testing. Omit
`--large` for the original three-employee example. Close the app to discard the
test database. Use `--payroll-port` / `--app-port` if defaults 8878/8890 are occupied.

The standalone browser demo also offers **Load 300-employee example**. This lets
you check paging, employee search and narrowed bulk retries at larger scale.

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


### Sending new uploads and reviewing retries

The desktop sidebar has three attendance views:
- **Overview** shows attendance totals. **Send New Uploads** sends only first attempts for each enabled Payroll destination and is disabled when none remain.
- **Attendance Records** starts with all statuses in the date range. **Send New Selected** counts only selected records with a first upload remaining. An already attempted destination is never resent from this button, even if another destination is still new.
- **Needs Attention** is the manual retry review. Opening review from an attendance row carries that employee and attendance date into the individual logs view; unconfirmed records open the Unconfirmed tab. Nothing is preselected or submitted by navigating here.

Overview's totals count attendance records; the send button and Needs Attention count uploads to individual Payroll destinations. One attendance record may have two uploads.
