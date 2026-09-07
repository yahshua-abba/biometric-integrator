import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import TimesheetView from '../TimesheetView.vue'

const bridge = vi.hoisted(() => ({
  whenReady: vi.fn().mockResolvedValue(),
  getApiConfig: vi.fn().mockResolvedValue({ data: { push_enabled_2: 1, push_username_2: 'demo' } }),
  getDevices: vi.fn().mockResolvedValue({ data: [] }),
  getAllTimesheets: vi.fn(),
  startPushSyncForIds: vi.fn().mockResolvedValue({ success: true }),
  setTimesheetExcluded: vi.fn().mockResolvedValue({ updated: 1, message: '1 record(s) excluded' }),
}))
vi.mock('../../services/bridge', () => ({ default: bridge }))
vi.mock('../../composables/useToast', () => ({ useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }) }))
let wrapper
afterEach(() => { wrapper?.unmount(); vi.clearAllMocks() })

async function show(fields) {
  bridge.getAllTimesheets.mockResolvedValue({ data: [{
    id: 1, employee_id: 7, new_uploads: 0, employee_name: 'Demo Employee', employee_code: '4472',
    date: new Date().toISOString().slice(0, 10), time: '18:52:00', log_type: 'in', sync_id: 'DEMO',
    backend_timesheet_id: 1, backend_timesheet_id_2: null, ...fields,
  }] })
  wrapper = mount(TimesheetView, { global: { stubs: { SyncProgressModal: true } } })
  await flushPromises()
  const filter = wrapper.findAll('select').find(s => s.find('option[value="duplicate"]').exists())
  await filter.setValue('all')
  return wrapper.find('tbody tr')
}

describe('per-destination duplicate status', () => {
  it('shows skipped duplicates separately and offers no automatic retry', async () => {
    const row = await show({ sync_skipped_reason_2: 'Time in range (5mins)' })
    expect(row.text()).toContain('Duplicate skipped')
    expect(row.find('[title="Retry sync"]').exists()).toBe(false)
    expect(row.find('input[type="checkbox"]').exists()).toBe(false)
    expect(row.find('[title*="Time in range"]').exists()).toBe(true)
    const filter = wrapper.findAll('select').find(s => s.find('option[value="duplicate"]').exists())
    await filter.setValue('duplicate')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    await filter.setValue('synced')
    expect(wrapper.findAll('tbody tr')).toHaveLength(0)
  })

  it('allows Do Not Sync when primary succeeded but secondary is pending', async () => {
    const row = await show({ sync_error_message_2: 'Connection failed' })
    expect(row.text()).toContain('Partial / Error')
    await row.find('[title="Mark as do-not-sync"]').trigger('click')
    expect(bridge.setTimesheetExcluded).toHaveBeenCalledWith([1], true)
  })

  it('keeps a record selectable when one destination skipped but the other is pending', async () => {
    const row = await show({ backend_timesheet_id: null, sync_skipped_reason: 'Duplicate record already exists' })
    expect(row.text()).toContain('Pending')
    expect(row.find('input[type="checkbox"]').exists()).toBe(true)
  })
})


describe('first uploads and manual retry entry points', () => {
  it('disables Send New Selected for an attempted record', async () => {
    const row = await show({ sync_error_message_2: 'Employee missing', delivery_outcome_2: 'failed' })
    await row.find('input[type="checkbox"]').setValue(true)
    const send = wrapper.findAll('button').find(b => b.text().includes('Send New Selected'))
    expect(send.attributes('disabled')).toBeDefined()
    await send.trigger('click')
    expect(bridge.startPushSyncForIds).not.toHaveBeenCalled()
  })
  it('sends a new destination even when the other destination failed', async () => {
    const row = await show({ backend_timesheet_id: null, sync_error_message: 'Employee missing', delivery_outcome_1: 'failed', new_uploads: 1 })
    await row.find('input[type="checkbox"]').setValue(true)
    await wrapper.findAll('button').find(b => b.text().includes('Send New Selected')).trigger('click')
    expect(bridge.startPushSyncForIds).toHaveBeenCalledWith([1])
  })
  it('opens review with the employee, attendance date, and unconfirmed tab', async () => {
    const row = await show({ sync_error_message_2: 'Timeout', delivery_outcome_2: 'unconfirmed' })
    const listener = vi.fn()
    window.addEventListener('openRetryQueue', listener, { once: true })
    await row.find('[title="Review in Needs Attention"]').trigger('click')
    expect(listener.mock.calls[0][0].detail).toEqual({
      employee: { employee_id: 7, employee_name: 'Demo Employee', employee_code: '4472' },
      date: new Date().toISOString().slice(0, 10), state: 'unconfirmed',
    })
    expect(bridge.startPushSyncForIds).not.toHaveBeenCalled()
  })
})
