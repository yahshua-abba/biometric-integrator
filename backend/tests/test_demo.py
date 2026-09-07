"""Exercise the demo over real loopback HTTP using the shipping push service."""

import threading

import pytest
import requests

from demo.server import create_server


@pytest.fixture
def mini_payroll():
    server = create_server(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.demo.base_url
    finally:
        server.demo.close()
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def action(base, name):
    response = requests.post(base + '/action', json={'action': name}, timeout=10)
    response.raise_for_status()
    return response.json()['lanes']


def test_deleted_punch_returns_before_fix_but_stays_deleted_after(mini_payroll):
    before, after = action(mini_payroll, 'sync')
    assert len(before['payroll']) == len(after['payroll']) == 1
    assert before['slots'][1]['status'] == 'Retry queued'
    assert after['slots'][1]['status'] == 'Duplicate skipped'
    assert before['requests'] == after['requests'] == 2
    before, after = action(mini_payroll, 'delete')
    assert before['deleted'] and after['deleted']
    assert before['payroll'] == after['payroll'] == []
    before, after = action(mini_payroll, 'sync')
    assert len(before['payroll']) == 1
    assert after['payroll'] == []
    assert before['requests'] == 3 and after['requests'] == 2
    for _ in range(3):
        before, after = action(mini_payroll, 'sync')
        assert after['payroll'] == [] and after['requests'] == 2


def test_reset_and_auto_controls_are_isolated(mini_payroll):
    action(mini_payroll, 'sync')
    requests.post(mini_payroll + '/action', json={'action': 'auto'}, timeout=10).raise_for_status()
    state = requests.get(mini_payroll + '/state', timeout=10).json()
    assert state['automatic'] and state['interval'] == 5
    lanes = action(mini_payroll, 'reset')
    assert all(lane['requests'] == 0 and not lane['payroll'] for lane in lanes)
    assert not requests.get(mini_payroll + '/state', timeout=10).json()['automatic']


def test_demo_rejects_cross_origin_commands_and_missing_payroll_token(mini_payroll):
    response = requests.post(mini_payroll + '/action', json={'action': 'sync'},
                             headers={'Origin': 'https://unrelated.invalid'}, timeout=10)
    assert response.status_code == 403
    response = requests.post(mini_payroll + '/payroll/after/api/sync-time-in-out/', json={}, timeout=10)
    assert response.status_code == 401


def retry_api(base, method, payload=None):
    return requests.post(base + '/retry-api', json={'method': method, 'payload': payload}, timeout=10)


def test_real_retry_queue_filters_manual_delivery_and_lost_acknowledgement(mini_payroll):
    retry_api(mini_payroll, 'sync').raise_for_status()
    queue = retry_api(mini_payroll, 'getRetryQueue', {}).json()['data']
    assert len(queue) == 6
    assert len([r for r in queue if r['state'] == 'unconfirmed']) == 2
    retry_api(mini_payroll, 'fix').raise_for_status()
    retry_api(mini_payroll, 'sync').raise_for_status()
    snapshot = requests.get(mini_payroll + '/retry-state', timeout=10).json()
    assert snapshot['requests'] == 2 and len(snapshot['payroll']) == 1
    mara = next(r for r in queue if r['employee_code'] == '4472')
    filters = {'date_from': '2026-08-24', 'date_to': '2026-08-24', 'employee_ids': [mara['employee_id']]}
    selected = retry_api(mini_payroll, 'getRetryQueue', filters).json()['data']
    assert len(selected) == 2
    result = retry_api(mini_payroll, 'retryTimesheets', {'filters': filters, 'items': [{'id': r['id'], 'slot': r['slot']} for r in selected]})
    result.raise_for_status()
    remaining = retry_api(mini_payroll, 'getRetryQueue', {}).json()['data']
    assert len(remaining) == 4 and all(r['employee_code'] != '4472' for r in remaining)
    ana = next(r for r in remaining if r['employee_code'] == '9930')
    assert retry_api(mini_payroll, 'retryTimesheets', {'items': [{'id': ana['id'], 'slot': ana['slot']}]}).status_code == 400
    retry_api(mini_payroll, 'delete').raise_for_status()
    retry_api(mini_payroll, 'sync').raise_for_status()
    snapshot = requests.get(mini_payroll + '/retry-state', timeout=10).json()
    assert snapshot['requests'] == 4 and not snapshot['payroll']


def test_volume_demo_pages_and_retries_only_one_employee(mini_payroll):
    retry_api(mini_payroll, 'large').raise_for_status()
    page = retry_api(mini_payroll, 'getRetryQueuePage', {'state': 'failed', 'mode': 'employees'}).json()['data']
    assert len(page['rows']) == 25 and page['total'] == 300
    assert page['uploads'] == 19200
    assert retry_api(mini_payroll, 'getRetrySelection', {'state': 'failed'}).status_code == 400
    employee = page['rows'][0]['employee_id']
    filters = {'state': 'failed', 'employee_ids': [employee]}
    selected = retry_api(mini_payroll, 'getRetrySelection', filters).json()['data']
    assert len(selected) == 64
    retry_api(mini_payroll, 'fix').raise_for_status()
    retry_api(mini_payroll, 'retryTimesheets', {'filters': filters, 'items': [{'id': r['id'], 'slot': r['slot']} for r in selected]}).raise_for_status()
    remaining = retry_api(mini_payroll, 'getRetryQueuePage', filters).json()['data']
    assert remaining['uploads'] == 0
    assert remaining['counts']['unconfirmed'] == 16
