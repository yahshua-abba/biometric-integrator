import { afterEach, expect, it, vi } from 'vitest'
import { shallowMount, flushPromises } from '@vue/test-utils'
import App from '../../App.vue'
import RetryQueueView from '../RetryQueueView.vue'
vi.mock('../../services/bridge', () => ({ default: {
  init: vi.fn().mockResolvedValue(), getAppInfo: vi.fn().mockResolvedValue({ data: { version: 'test' } }),
} }))
let wrapper
afterEach(() => wrapper?.unmount())
it('preserves record context through navigation and clears it for the general queue', async () => {
  wrapper = shallowMount(App)
  await flushPromises()
  const detail = { employee: { employee_id: 7, employee_name: 'Demo' }, date: '2026-08-24', state: 'unconfirmed' }
  window.dispatchEvent(new CustomEvent('openRetryQueue', { detail }))
  await flushPromises()
  expect(wrapper.findComponent(RetryQueueView).props('initialContext')).toEqual(detail)
  await wrapper.findAll('button').find(b => b.text() === 'Needs Attention').trigger('click')
  expect(wrapper.findComponent(RetryQueueView).props('initialContext')).toBeNull()
})
