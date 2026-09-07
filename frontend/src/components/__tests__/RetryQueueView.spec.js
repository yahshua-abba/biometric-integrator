import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import RetryQueueView from '../RetryQueueView.vue'
const bridge = vi.hoisted(() => ({ whenReady: vi.fn().mockResolvedValue(), getRetryQueue: vi.fn(), retryTimesheets: vi.fn().mockResolvedValue({ success: true }) }))
vi.mock('../../services/bridge', () => ({ default: bridge }))
const base = { employee_id: 1, employee_name: 'Mara Santos', employee_code: '4472', date: '2026-08-24', time: '18:52', log_type: 'in', slot: 1, state: 'failed', reason: 'Employee not found', attempted_at: '2026-08-26 05:34', attempts: 1, busy: 0 }
let wrapper
const button = text => wrapper.findAll('button').find(b => b.text().startsWith(text))
async function show(rows) {
  bridge.getRetryQueue.mockResolvedValue({ data: rows })
  wrapper = mount(RetryQueueView)
  await flushPromises()
}
afterEach(() => { wrapper?.unmount(); vi.clearAllMocks() })
describe('Retry Queue review and bulk scope', () => {
  it('filters attendance dates and employees and retries only the chosen destination', async () => {
    await show([{ ...base, id: 1, slot: 2 }, { ...base, id: 2, date: '2026-08-25' },
      { ...base, id: 3, employee_id: 2, employee_name: 'Luis', employee_code: '88' }])
    const dates = wrapper.findAll('input[type="date"]')
    await dates[0].setValue('2026-08-24'); await dates[1].setValue('2026-08-24')
    await wrapper.findAll('fieldset label').find(l => l.text().includes('Mara Santos')).find('input').setValue(true)
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    await button('Select all filtered').trigger('click')
    await button('Review & retry').trigger('click')
    await button('Retry 1 records now').trigger('click')
    expect(bridge.retryTimesheets).toHaveBeenCalledWith({ items: [{ id: 1, slot: 2 }], filters: { date_from: '2026-08-24', date_to: '2026-08-24', employee_ids: [1], slot: 0, state: 'all' }, reviewed_payroll: false })
  })
  it('requires Payroll review for unconfirmed uploads and clears selection on filter change', async () => {
    await show([{ ...base, id: 1, state: 'unconfirmed' }])
    await button('Select all filtered').trigger('click'); await button('Review & retry').trigger('click')
    expect(button('Retry 1 records now').attributes('disabled')).toBeDefined()
    expect(bridge.retryTimesheets).not.toHaveBeenCalled()
    await wrapper.find('[role="dialog"] input').setValue(true)
    await button('Retry 1 records now').trigger('click')
    expect(bridge.retryTimesheets.mock.calls[0][0].reviewed_payroll).toBe(true)
    window.dispatchEvent(new CustomEvent('syncCompleted', { detail: { type: 'push', manual_retry: true, result: { message: 'Retry completed' } } }))
    await flushPromises()
    await button('Select all filtered').trigger('click')
    await wrapper.find('input[type="date"]').setValue('2026-08-25')
    expect(button('Review & retry').attributes('disabled')).toBeDefined()
  })
  it('selects across filtered pages while excluding active uploads', async () => {
    await show(Array.from({ length: 52 }, (_, i) => ({ ...base, id: i + 1, busy: i === 0 ? 1 : 0 })))
    expect(wrapper.findAll('tbody tr')).toHaveLength(50)
    expect(wrapper.find('tbody input').attributes('disabled')).toBeDefined()
    await button('Select all filtered').trigger('click')
    expect(button('Review & retry').text()).toContain('(51)')
    await button('Next').trigger('click')
    expect(wrapper.findAll('tbody tr')).toHaveLength(2)
    await button('Review & retry').trigger('click'); await button('Retry 51 records now').trigger('click')
    expect(bridge.retryTimesheets.mock.calls[0][0].items).toHaveLength(51)
    expect(bridge.retryTimesheets.mock.calls[0][0].items.some(r => r.id === 1)).toBe(false)
  })
  it('shows backend errors and refreshes after retries without losing failures', async () => {
    await show([{ ...base, id: 1 }])
    bridge.retryTimesheets.mockRejectedValueOnce(new Error('Selected record changed. Refresh.'))
    await button('Select all filtered').trigger('click'); await button('Review & retry').trigger('click'); await button('Retry 1 records now').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="dialog"]').text()).toContain('Selected record changed')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    await button('Cancel').trigger('click')
    bridge.getRetryQueue.mockResolvedValue({ data: [] })
    window.dispatchEvent(new CustomEvent('syncCompleted', { detail: { type: 'push', manual_retry: true, result: {} } }))
    await flushPromises()
    expect(wrapper.text()).toContain('No attendance uploads need a manual retry.')
  })
  it('prevents retry with inverted date ranges', async () => {
    await show([{ ...base, id: 1 }])
    const dates = wrapper.findAll('input[type="date"]')
    await dates[0].setValue('2026-08-25'); await dates[1].setValue('2026-08-24')
    expect(wrapper.text()).toContain('Start date must be on or before end date.')
    expect(button('Select all filtered').attributes('disabled')).toBeDefined()
  })
})
