import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import RetryEmployeeFilter from '../RetryEmployeeFilter.vue'
const bridge = vi.hoisted(() => ({ getRetryQueuePage: vi.fn() }))
vi.mock('../../services/bridge', () => ({ default: bridge }))
let wrapper
afterEach(() => { wrapper?.unmount(); vi.clearAllMocks(); vi.useRealTimers() })
describe('compact employee picker', () => {
  it('loads only when opened, with 20 employee options per page', async () => {
    bridge.getRetryQueuePage.mockResolvedValue({ data: { total: 300, rows: [{ employee_id: 1, employee_name: 'Mara Santos', employee_code: '4472' }] } })
    wrapper = mount(RetryEmployeeFilter, { props: { modelValue: [], filters: { date_from: '', date_to: '', slot: 0 } } })
    expect(bridge.getRetryQueuePage).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('All employees')
    await wrapper.find('button').trigger('click'); await flushPromises()
    expect(bridge.getRetryQueuePage).toHaveBeenCalledWith(expect.objectContaining({ mode: 'employees', page: 1, page_size: 20 }))
    await wrapper.find('input[type="checkbox"]').setValue(true)
    expect(wrapper.emitted('update:modelValue')[0][0][0].employee_id).toBe(1)
    await wrapper.findAll('button').find(b => b.text() === 'Next').trigger('click'); await flushPromises()
    expect(bridge.getRetryQueuePage).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2, page_size: 20 }))
  })
  it('searches the database and preserves previously selected employees', async () => {
    vi.useFakeTimers()
    bridge.getRetryQueuePage.mockResolvedValue({ data: { total: 1, rows: [{ employee_id: 2, employee_name: 'Luis Cruz', employee_code: '8821' }] } })
    wrapper = mount(RetryEmployeeFilter, { props: { modelValue: [{ employee_id: 1, employee_name: 'Mara Santos' }], filters: {} } })
    await wrapper.find('button').trigger('click'); await flushPromises()
    await wrapper.find('input[type="text"], input:not([type])').setValue('8821')
    await vi.advanceTimersByTimeAsync(250); await flushPromises()
    expect(bridge.getRetryQueuePage).toHaveBeenLastCalledWith(expect.objectContaining({ search: '8821', employee_ids: [] }))
    await wrapper.find('input[type="checkbox"]').setValue(true)
    expect(wrapper.emitted('update:modelValue')[0][0].map(r => r.employee_id)).toEqual([1, 2])
  })
})
