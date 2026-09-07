import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import RetryQueueView from '../RetryQueueView.vue'
const bridge = vi.hoisted(() => ({ whenReady: vi.fn().mockResolvedValue(), getRetryQueuePage: vi.fn(), getRetrySelection: vi.fn(), retryTimesheets: vi.fn().mockResolvedValue({ success: true }) }))
vi.mock('../../services/bridge', () => ({ default: bridge }))
const base = { employee_id: 1, employee_name: 'Mara Santos', employee_code: '4472', date: '2026-08-24', time: '18:52', log_type: 'in', slot: 1, state: 'failed', reason: 'Employee not found', attempted_at: '2026-08-26 05:34', attempts: 1, busy: 0 }
const group = { employee_id: 1, employee_name: 'Mara Santos', employee_code: '4472', uploads: 60, logs: 30, first_date: '2026-08-01', last_date: '2026-08-24', issue_count: 1, reason: 'Employee not found', available: 60 }
const summary = (rows, rest = {}) => ({ rows, total: rows.length, page: 1, page_size: 25, uploads: 60, employees: 1, available: 60, counts: { failed: 60, unconfirmed: 2 }, ...rest })
let wrapper
const button = text => wrapper.findAll('button').find(b => b.text().startsWith(text))
async function show() {
  bridge.getRetryQueuePage.mockResolvedValue({ data: summary([group]) })
  bridge.getRetrySelection.mockResolvedValue({ data: [{ ...base, id: 1 }, { ...base, id: 2, slot: 2 }] })
  wrapper = mount(RetryQueueView)
  await flushPromises()
}
afterEach(() => { wrapper?.unmount(); vi.clearAllMocks() })

describe('scalable Retry Queue', () => {
  it('starts with employee summaries and a bounded database page', async () => {
    await show()
    expect(bridge.getRetryQueuePage).toHaveBeenCalledWith({ date_from: '', date_to: '', employee_ids: [], slot: 0, state: 'failed', mode: 'employees', page: 1, page_size: 25 })
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    expect(wrapper.text()).toContain('30 attendance logs')
    expect(wrapper.find('fieldset').exists()).toBe(false)
    expect(bridge.getRetrySelection).not.toHaveBeenCalled()
  })
  it('opens one employee’s logs with preserved date filters', async () => {
    await show()
    const dates = wrapper.findAll('input[type="date"]')
    await dates[0].setValue('2026-08-24'); await dates[1].setValue('2026-08-24'); await flushPromises()
    bridge.getRetryQueuePage.mockResolvedValue({ data: summary([{ ...base, id: 1 }]) })
    await button('View logs').trigger('click'); await flushPromises()
    expect(bridge.getRetryQueuePage).toHaveBeenLastCalledWith(expect.objectContaining({ employee_ids: [1], mode: 'logs', date_from: '2026-08-24', date_to: '2026-08-24' }))
    expect(wrapper.find('tbody details').exists()).toBe(true)
    expect(wrapper.find('tbody details').text()).toContain('Last attempt:')
    await button('← Employees').trigger('click'); await flushPromises()
    expect(bridge.getRetryQueuePage).toHaveBeenLastCalledWith(expect.objectContaining({ employee_ids: [], mode: 'employees' }))
  })
  it('reviews the selected employee scope and freezes exact upload IDs', async () => {
    await show()
    await wrapper.find('tbody input').setValue(true)
    await button('Review selected').trigger('click'); await flushPromises()
    expect(bridge.getRetrySelection).toHaveBeenCalledWith(expect.objectContaining({ employee_ids: [1], state: 'failed' }))
    expect(wrapper.find('[role="dialog"]').text()).toContain('Review 2 uploads')
    bridge.getRetrySelection.mockResolvedValue({ data: [{ ...base, id: 99 }] })
    await button('Retry 2 uploads now').trigger('click'); await flushPromises()
    expect(bridge.retryTimesheets).toHaveBeenCalledWith(expect.objectContaining({ items: [{ id: 1, slot: 1 }, { id: 2, slot: 2 }], reviewed_payroll: false }))
  })
  it('keeps Unconfirmed separate and requires Payroll review', async () => {
    await show()
    await button('Unconfirmed').trigger('click'); await flushPromises()
    expect(bridge.getRetryQueuePage).toHaveBeenLastCalledWith(expect.objectContaining({ state: 'unconfirmed' }))
    bridge.getRetrySelection.mockResolvedValue({ data: [{ ...base, id: 1, state: 'unconfirmed' }] })
    await button('Review all filtered').trigger('click'); await flushPromises()
    expect(button('Retry 1 uploads now').attributes('disabled')).toBeDefined()
    await wrapper.find('[role="dialog"] input').setValue(true)
    await button('Retry 1 uploads now').trigger('click'); await flushPromises()
    expect(bridge.retryTimesheets.mock.calls[0][0].reviewed_payroll).toBe(true)
  })
  it('pages in the database and preserves individually selected logs across pages', async () => {
    await show()
    bridge.getRetryQueuePage.mockResolvedValue({ data: summary([{ ...base, id: 1 }], { total: 52 }) })
    await button('Individual logs').trigger('click'); await flushPromises()
    await wrapper.find('tbody input').setValue(true)
    bridge.getRetryQueuePage.mockResolvedValue({ data: summary([{ ...base, id: 26 }], { total: 52, page: 2 }) })
    await button('Next').trigger('click'); await flushPromises()
    expect(bridge.getRetryQueuePage).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2, page_size: 25 }))
    await wrapper.find('tbody input').setValue(true)
    await button('Review selected').trigger('click'); await flushPromises()
    expect(bridge.getRetrySelection).not.toHaveBeenCalled()
    await button('Retry 2 uploads now').trigger('click'); await flushPromises()
    expect(bridge.retryTimesheets.mock.calls[0][0].items).toEqual([{ id: 1, slot: 1 }, { id: 26, slot: 1 }])
  })
  it('does not allow a broad retry above the 10,000 upload limit', async () => {
    await show()
    bridge.getRetryQueuePage.mockResolvedValue({ data: summary([group], { uploads: 19200, available: 19200, employees: 300, total: 300 }) })
    await button('Refresh').trigger('click'); await flushPromises()
    expect(button('Review all filtered').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('narrow the dates')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
  })
  it('ignores late page responses after the filters change', async () => {
    await show()
    let resolveOld
    bridge.getRetryQueuePage.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve }))
    await button('Refresh').trigger('click')
    bridge.getRetryQueuePage.mockResolvedValue({ data: summary([{ ...group, employee_name: 'New scope' }]) })
    await button('Unconfirmed').trigger('click'); await flushPromises()
    resolveOld({ data: summary([{ ...group, employee_name: 'Stale scope' }]) }); await flushPromises()
    expect(wrapper.find('tbody').text()).toContain('New scope')
    expect(wrapper.find('tbody').text()).not.toContain('Stale scope')
  })
  it('discards a prepared bulk selection when its filter changes', async () => {
    await show()
    let resolveSelection
    bridge.getRetrySelection.mockImplementationOnce(() => new Promise(resolve => { resolveSelection = resolve }))
    await button('Review all filtered').trigger('click')
    await button('Unconfirmed').trigger('click'); await flushPromises()
    resolveSelection({ data: [{ ...base, id: 1 }] }); await flushPromises()
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    expect(bridge.retryTimesheets).not.toHaveBeenCalled()
  })
  it('shows backend rejection and does not silently clear the queue', async () => {
    await show()
    bridge.retryTimesheets.mockRejectedValueOnce(new Error('Selection changed. Refresh.'))
    await button('Review all filtered').trigger('click'); await flushPromises()
    await button('Retry 2 uploads now').trigger('click'); await flushPromises()
    expect(wrapper.find('[role="dialog"]').text()).toContain('Selection changed')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
  })
  it('rejects invalid dates and clears a previous selection', async () => {
    await show()
    await wrapper.find('tbody input').setValue(true)
    const dates = wrapper.findAll('input[type="date"]')
    await dates[0].setValue('2026-08-25'); await dates[1].setValue('2026-08-24'); await flushPromises()
    expect(wrapper.text()).toContain('Start date must be on or before end date.')
    expect(button('Review all filtered').attributes('disabled')).toBeDefined()
    expect(wrapper.findAll('tbody tr')).toHaveLength(0)
  })
})


it('opens a contextual attendance review without selecting or resending uploads', async () => {
  bridge.getRetryQueuePage.mockResolvedValue({ data: summary([{ ...base, id: 1, state: 'unconfirmed' }]) })
  wrapper = mount(RetryQueueView, { props: { initialContext: {
    employee: { employee_id: 1, employee_name: 'Mara' }, date: '2026-08-24', state: 'unconfirmed',
  } } })
  await flushPromises()
  expect(bridge.getRetryQueuePage).toHaveBeenLastCalledWith(expect.objectContaining({
    employee_ids: [1], date_from: '2026-08-24', date_to: '2026-08-24', state: 'unconfirmed', mode: 'logs',
  }))
  expect(wrapper.text()).toContain('These uploads may already be in Payroll')
  expect(wrapper.find('tbody input').element.checked).toBe(false)
  expect(bridge.retryTimesheets).not.toHaveBeenCalled()
  await wrapper.setProps({ initialContext: null }); await flushPromises()
  expect(bridge.getRetryQueuePage).toHaveBeenLastCalledWith(expect.objectContaining({ employee_ids: [], date_from: '', state: 'failed', mode: 'employees' }))
})
