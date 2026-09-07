"""Large-company queue: SQL pages, employee summaries and bounded review snapshots."""
from datetime import date
import pytest
from database import Database
from demo.fixtures import seed_large_queue


@pytest.fixture(scope='module')
def volume(tmp_path_factory):
    db = Database(str(tmp_path_factory.mktemp('volume') / 'queue.db'))
    db.update_api_config(push_enabled_2=1, push_username_2='demo')
    seed_large_queue(db)
    return db


def test_employee_summaries_do_not_return_all_logs(volume, monkeypatch):
    monkeypatch.setattr(volume, 'get_retry_queue', lambda *_: pytest.fail('Do not load the entire queue'))
    result = volume.get_retry_queue_page({'state': 'failed'})
    assert len(result['rows']) == 25
    assert result['total'] == result['employees'] == 300
    assert result['uploads'] == 19200
    assert result['counts'] == {'failed': 19200, 'unconfirmed': 4800}
    assert all(r['uploads'] == 64 and r['logs'] == 32 for r in result['rows'])
    second = volume.get_retry_queue_page({'state': 'failed', 'page': 2})
    assert not {r['employee_id'] for r in result['rows']} & {r['employee_id'] for r in second['rows']}


def test_log_pages_employee_filters_and_status_counts(volume):
    employee = volume.get_employee_by_code('90000')['id']
    filters = {'state': 'failed', 'employee_ids': [employee], 'mode': 'logs', 'page_size': 25}
    page = volume.get_retry_queue_page(filters)
    assert page['total'] == 64 and len(page['rows']) == 25
    assert page['counts'] == {'failed': 64, 'unconfirmed': 16}
    next_page = volume.get_retry_queue_page({**filters, 'page': 2})
    assert not {(r['id'], r['slot']) for r in page['rows']} & {(r['id'], r['slot']) for r in next_page['rows']}
    day = date.today().isoformat()
    same_day = volume.get_retry_queue_page({**filters, 'state': 'all', 'date_from': day, 'date_to': day, 'slot': 2})
    assert same_day['total'] == 2 and same_day['counts'] == {'failed': 1, 'unconfirmed': 1}
    assert all(r['slot'] == 2 and r['employee_id'] == employee for r in same_day['rows'])


def test_employee_picker_is_bounded_and_searches_code_or_name(volume):
    page = volume.get_retry_queue_page({'mode': 'employees', 'page_size': 20, 'search': '900'})
    assert len(page['rows']) == 20 and page['total'] == 100
    person = volume.get_retry_queue_page({'search': '90017'})
    assert person['total'] == 1 and person['rows'][0]['employee_code'] == '90017'
    assert volume.get_retry_queue_page({'search': "' OR 1=1 --"})['total'] == 0


def test_bulk_snapshot_limits_and_scoping(volume):
    with pytest.raises(ValueError, match='10,000'):
        volume.get_retry_selection({'state': 'failed'})
    employees = [volume.get_employee_by_code(code)['id'] for code in ('90000', '90001')]
    filters = {'employee_ids': employees, 'state': 'failed', 'slot': 2}
    selection = volume.get_retry_selection(filters)
    assert len(selection) == 64
    assert {r['employee_id'] for r in selection} == set(employees)
    payload = {'filters': filters, 'items': [{'id': r['id'], 'slot': r['slot']} for r in selection]}
    assert volume.validate_retry_selection(payload) == {2: {r['id'] for r in selection}}
    with pytest.raises(ValueError):
        volume.validate_retry_selection({**payload, 'filters': {**filters, 'slot': 1}})


@pytest.mark.parametrize('filters', [{'page_size': 100000}, {'page': 0}, {'page_size': True}, {'mode': 'invalid'}, {'slot': 3}, {'date_from': '2026-9-1'}])
def test_invalid_page_parameters_fail_closed(volume, filters):
    with pytest.raises(ValueError):
        volume.get_retry_queue_page(filters)
