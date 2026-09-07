# Mini Payroll: deletion and retry demo

This local demo compares the previous retry behavior with the fixed biometric
push service. It uses **synthetic employee 4472, Mara Santos**, two temporary app
databases, and a small Payroll HTTP API. It never uses the installed desktop
app's database, credentials, devices, or actual Payroll.

## Start

From the repository root, using Python 3.10 or newer:

```bash
python3 -m venv /tmp/biometric-demo-venv
/tmp/biometric-demo-venv/bin/pip install requests
/tmp/biometric-demo-venv/bin/python backend/demo/server.py
```

Open <http://127.0.0.1:8877>. Use `--port 8878` if that port is occupied.
Stop the process with Ctrl+C. Its temporary SQLite databases are cleaned up.
No frontend build, Qt installation, biometric machine, or external API is needed.

## Reproduce in three clicks

1. **Sync now**: one tap is uploaded through two configurations pointing to the
   same mini Payroll. The second upload is rejected with HTTP 400 / error 120.
   Before: it remains queued. After: it is visibly skipped for that destination.
2. **Approve deletion in Payroll**: both mini Payroll copies remove the punch.
   This does not alter either app's local upload history.
3. **Sync now** again: the old lane recreates the punch. The fixed lane makes no
   new upload and Payroll stays empty. Alternatively start auto sync every five
   seconds and watch the request history. Reset returns to a single fresh tap.

The fixed lane uses the shipping `PushService` directly, with real loopback HTTP
requests and the production SQLite implementation. The old lane subclasses it
only to disable duplicate classification. Destinations run in a fixed order for
a repeatable walkthrough; concurrent service behavior has separate unit tests.

## Deliberate limits

- Mini Payroll forgets a deleted punch, allowing it to be recreated. This is a
  test model of the reported failure, not verification of production deletion.
- The fix stops retries after an **explicit duplicate rejection**, including
  recognizable duplicate errors saved by older builds. It does not claim a
  nearby IN/OUT record was uploaded: its reason remains visible as skipped.
- A request whose response is lost can still be ambiguous. If HR deletes the
  punch before any duplicate rejection reaches the app, the client has no way
  to know it was deliberately deleted. A durable deletion record / idempotency
  rule in the actual Payroll API is needed to guarantee this across new app
  installations and lost local history. This demo does not modify Payroll.
- Generic old errors such as `Bad request` cannot safely be converted into
  duplicate skips without evidence. Ordinary failures remain retryable.
- Skip history follows the existing local retention policy. Cleanup after 60 days
  or replacing the database removes that history; server-side deletion protection
  is needed to cover later re-imports too.
- The sync lock covers manual and scheduled pushes sharing the same service in
  one app process; Payroll must enforce uniqueness across independent clients.

## Automated checks

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q
cd frontend
npm ci
npm test
npm run build
```

The suite includes real HTTP create → duplicate rejection → delete → next-sync
checks, both destination slots, restart and upgrade handling, partial-sync
exclusion, authentication retry results, and overlapping sync attempts.
