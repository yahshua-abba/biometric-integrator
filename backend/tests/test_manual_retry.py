"""Send-once delivery and HR's scoped manual-retry contract."""
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock
import pytest
import requests
from database import Database
from tests.test_duplicate_recovery import seeded, service, reply


@pytest.mark.parametrize('slot', [1, 2])
@pytest.mark.parametrize('response', ['timeout', 'missing', 'invalid', 'conflict', 'server'])
def test_uncertain_upload_never_auto_retries_after_restart(seeded, slot, response):
    db, row = seeded
    svc = service(db, slot)
    if response == 'timeout':
        svc.session.post = Mock(side_effect=requests.exceptions.Timeout)
    else:
        result = {'missing': reply(200), 'invalid': reply(200),
                  'conflict': reply(200, [row], [{'id': row, 'reason': 'Invalid'}]),
                  'server': reply(500)}[response]
        if response == 'invalid':
            result.json.side_effect = ValueError('Not JSON')
        svc.session.post = Mock(return_value=result)
    svc.push_data()
    restarted = Database(str(db.db_path))
    again = service(restarted, slot)
    again.session.post = Mock()
    again.push_data()
    again.push_data(timesheet_ids=[row])
    again.session.post.assert_not_called()
    item = restarted.get_retry_queue()[0]
    assert item['state'] == 'unconfirmed' and item['attempts'] == 1 and not item['busy']
    assert restarted.get_unsynced_timesheets(slot=3-slot)


def test_claim_is_atomic_across_services_and_survives_crash(seeded):
    db, row = seeded
    def claim(_):
        return Database(str(db.db_path)).claim_delivery([row], 1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, [1, 2]))
    assert sorted(len(r) for r in results) == [0, 1]
    assert not db.get_unsynced_timesheets(slot=1)
    assert db.get_retry_queue()[0]['busy']
    assert not db.claim_delivery([row], 1, manual_retry=True)
    conn = db.get_connection()
    with conn:
        conn.execute("UPDATE delivery_attempt SET attempted_at=datetime('now','-3 minutes')")
    conn.close()
    assert db.get_retry_queue()[0]['state'] == 'unconfirmed'
    assert db.claim_delivery([row], 1, manual_retry=True) == [row]
    assert db.get_retry_queue()[0]['attempts'] == 2


def test_attempt_history_survives_cleanup_and_reimport(seeded):
    db, row = seeded
    original = db.get_all_timesheets()[0]
    db.claim_delivery([row], 1)
    db.mark_timesheet_sync_failed(row, 'Lost confirmation', 1, unconfirmed=True)
    conn = db.get_connection()
    with conn:
        conn.execute('DELETE FROM timesheet WHERE id=?', (row,))
    conn.close()
    db.add_timesheet_entry(original['sync_id'], original['employee_id'], 'in', original['date'], original['time'])
    assert not db.get_unsynced_timesheets(slot=1)
    assert len(db.get_retry_queue()) == 1


def test_only_sent_batch_is_claimed_when_request_fails(seeded):
    db, row = seeded
    employee = db.get_all_timesheets()[0]['employee_id']
    for i in range(50):
        db.add_timesheet_entry(f'batch-{i}', employee, 'in', '2026-08-25', '08:00')
    svc = service(db, 1)
    svc.session.post = Mock(side_effect=requests.exceptions.Timeout)
    svc.push_data()
    assert len(db.get_retry_queue()) == 50
    assert len(db.get_unsynced_timesheets(slot=1)) == 1
    assert svc.session.post.call_count == 1


def test_foreign_acknowledgements_never_mark_other_records_synced(seeded):
    db, row = seeded
    employee = db.get_all_timesheets()[0]['employee_id']
    other = db.add_timesheet_entry('other', employee, 'in', '2026-08-25', '08:00')
    svc = service(db, 1)
    svc.session.post = Mock(return_value=reply(200, [other]))
    svc.push_data(timesheet_ids=[row])
    assert db.get_retry_queue()[0]['state'] == 'unconfirmed'
    assert [r['id'] for r in db.get_unsynced_timesheets(slot=1)] == [other]


def test_queue_filters_and_bulk_scope_are_rechecked(seeded):
    db, row = seeded
    first = db.get_all_timesheets()[0]['employee_id']
    db.add_or_update_employee('99', 'Other Employee', '99')
    second = db.get_employee_by_code('99')['id']
    records = [row, db.add_timesheet_entry('other-day', first, 'in', '2026-08-25', '08:00'),
               db.add_timesheet_entry('other-employee', second, 'in', '2026-08-24', '08:00')]
    for slot in (1, 2):
        db.claim_delivery(records, slot)
        for record in records:
            db.mark_timesheet_sync_failed(record, 'Rejected', slot)
    filters = {'date_from': '2026-08-24', 'date_to': '2026-08-24', 'employee_ids': [first], 'slot': 2, 'state': 'failed'}
    assert [(r['id'], r['slot']) for r in db.get_retry_queue(filters)] == [(row, 2)]
    payload = {'items': [{'id': row, 'slot': 2}], 'filters': filters}
    assert db.validate_retry_selection(payload) == {2: {row}}
    for bad in ({'id': row, 'slot': 1}, {'id': records[1], 'slot': 2}, {'id': records[2], 'slot': 2}):
        with pytest.raises(ValueError):
            db.validate_retry_selection({**payload, 'items': [bad]})
    svc = service(db, 2)
    svc.session.post = Mock(return_value=reply(200, [row]))
    svc.push_data(timesheet_ids=[row], manual_retry=True)
    assert len(db.get_retry_queue()) == 5
    assert db.get_retry_queue({'slot': 1})[0]['attempts'] == 1
    assert not db.claim_delivery([row], 2, manual_retry=True)


@pytest.mark.parametrize('change', ['excluded', 'deleted', 'duplicate', 'success', 'disabled'])
def test_reviewed_selection_is_rejected_if_no_longer_eligible(seeded, change):
    db, row = seeded
    db.claim_delivery([row], 2)
    db.mark_timesheet_sync_failed(row, 'Failed', 2)
    if change == 'excluded': db.set_timesheets_excluded([row], True)
    elif change == 'deleted': db.soft_delete_timesheets_by_ids([row])
    elif change == 'duplicate': db.mark_timesheet_duplicate(row, 'Duplicate', 2)
    elif change == 'success': db.mark_timesheet_synced(row, row, 2)
    else: db.update_api_config(push_enabled_2=0)
    with pytest.raises(ValueError):
        db.validate_retry_selection({'items': [{'id': row, 'slot': 2}]})


def test_unconfirmed_manual_retry_requires_payroll_review(seeded):
    db, row = seeded
    db.claim_delivery([row], 1)
    db.mark_timesheet_sync_failed(row, 'Timeout', 1, unconfirmed=True)
    payload = {'items': [{'id': row, 'slot': 1}]}
    with pytest.raises(ValueError, match='Check unconfirmed'):
        db.validate_retry_selection(payload)
    assert db.validate_retry_selection({**payload, 'reviewed_payroll': True}) == {1: {row}}
    with pytest.raises(ValueError):
        db.get_retry_queue({'date_from': '2026-08-26', 'date_to': '2026-08-24'})


def test_cleanup_keeps_old_records_that_need_manual_review(seeded):
    from services.scheduler import SyncScheduler
    db, row = seeded
    db.claim_delivery([row], 1)
    db.mark_timesheet_sync_failed(row, 'Rejected', 1)
    conn = db.get_connection()
    with conn:
        conn.execute("UPDATE timesheet SET date='2000-01-01' WHERE id=?", (row,))
    conn.close()
    scheduler = SyncScheduler(None, None, db)
    scheduler.run_cleanup()
    assert len(db.get_retry_queue()) == 1
    db.mark_timesheet_synced(row, row, 1)
    scheduler.run_cleanup()
    assert not db.get_all_timesheets()
    conn = db.get_connection()
    assert conn.execute('SELECT COUNT(*) FROM delivery_attempt').fetchone()[0] == 1
    conn.close()


def test_attendance_request_does_not_follow_redirects(seeded):
    db, row = seeded
    svc = service(db, 1)
    svc.session.post = Mock(return_value=reply(307))
    svc.push_data()
    assert svc.session.post.call_args.kwargs['allow_redirects'] is False
    assert svc.session.post.call_count == 1
    assert not db.get_unsynced_timesheets(slot=1)


def test_bulk_review_snapshot_does_not_include_new_arrivals(seeded):
    db, row = seeded
    db.claim_delivery([row], 1)
    db.mark_timesheet_sync_failed(row, 'Rejected', 1)
    snapshot = db.get_retry_selection({'state': 'failed'})
    employee = db.get_all_timesheets()[0]['employee_id']
    arriving = db.add_timesheet_entry('new-after-review', employee, 'in', '2026-08-24', '09:00')
    db.claim_delivery([arriving], 1)
    db.mark_timesheet_sync_failed(arriving, 'Rejected', 1)
    scope = db.validate_retry_selection({'filters': {'state': 'failed'}, 'items': [{'id': r['id'], 'slot': r['slot']} for r in snapshot]})
    assert scope == {1: {row}}
