"""Exercise Qt's JSON boundary with a minimal signal stub when Qt is unavailable."""
import importlib
import json
import sys
import threading
import types
from unittest.mock import Mock
import pytest
from tests.test_duplicate_recovery import seeded


@pytest.fixture
def bridge_class(monkeypatch):
    # CI does not install Qt; keep this boundary test independent of a GUI runtime.
    qt = types.ModuleType('PyQt6.QtCore')
    qt.QObject = type('QObject', (), {})
    qt.pyqtSlot = lambda *args, **kwargs: lambda function: function
    qt.pyqtSignal = lambda *args: Mock()
    for name in ('QThread', 'QMetaObject', 'Qt', 'Q_ARG'):
        setattr(qt, name, Mock())
    monkeypatch.setitem(sys.modules, 'PyQt6', types.ModuleType('PyQt6'))
    monkeypatch.setitem(sys.modules, 'PyQt6.QtCore', qt)
    old = sys.modules.pop('bridge', None)
    try:
        yield importlib.import_module('bridge').Bridge
    finally:
        sys.modules.pop('bridge', None)
        if old is not None:
            sys.modules['bridge'] = old


def test_bridge_dispatches_only_reviewed_destination_and_emits_result(seeded, bridge_class):
    db, row = seeded
    db.claim_delivery([row], 2)
    db.mark_timesheet_sync_failed(row, 'Mapping failed', 2)
    first, second = Mock(slot=1, label='Primary'), Mock(slot=2, label='Secondary')
    second.push_data.return_value = (True, 'Retried one record', {'success': 1})
    second.is_configured.return_value = True
    bridge = bridge_class(db, None, first, push_service_2=second)
    completed = threading.Event()
    bridge.syncCompleted = Mock()
    bridge.syncCompleted.emit.side_effect = lambda _: completed.set()
    payload = {'items': [{'id': row, 'slot': 2}], 'filters': {'slot': 2}}
    assert json.loads(bridge.retryTimesheets(json.dumps(payload)))['success']
    assert completed.wait(5)
    first.push_data.assert_not_called()
    assert second.push_data.call_args.kwargs['timesheet_ids'] == [row]
    assert second.push_data.call_args.kwargs['manual_retry'] is True
    result = json.loads(bridge.syncCompleted.emit.call_args.args[0])
    assert result['manual_retry'] and result['result']['stats']['success'] == 1
    assert not json.loads(bridge.retryFailedTimesheet(row))['success']


@pytest.mark.parametrize('payload', ['null', '[]', '{', '{"items":[]}', '{"items":[{"id":true,"slot":1}]}'])
def test_bridge_rejects_invalid_retry_payload_without_dispatch(seeded, bridge_class, payload):
    db, row = seeded
    svc = Mock(slot=1)
    bridge = bridge_class(db, None, svc)
    assert not json.loads(bridge.retryTimesheets(payload))['success']
    svc.push_data.assert_not_called()


def test_bridge_paged_queue_and_frozen_bulk_selection(seeded, bridge_class):
    db, row = seeded
    db.claim_delivery([row], 1)
    db.mark_timesheet_sync_failed(row, 'Failed', 1)
    bridge = bridge_class(db, None, Mock(slot=1))
    page = json.loads(bridge.getRetryQueuePage(json.dumps({'state': 'failed', 'mode': 'employees', 'page_size': 25})))
    assert page['success'] and page['data']['total'] == 1
    assert page['data']['rows'][0]['uploads'] == 1
    selection = json.loads(bridge.getRetrySelection(json.dumps({'state': 'failed'})))
    assert selection['success'] and [r['id'] for r in selection['data']] == [row]
    assert not json.loads(bridge.getRetryQueuePage('{"page_size":10000}'))['success']
