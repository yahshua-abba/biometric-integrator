import { afterEach, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import DateRangeShortcuts from '../DateRangeShortcuts.vue'
afterEach(() => vi.useRealTimers())
it('emits inclusive local date ranges across a month boundary and allows clearing', async () => {
  vi.useFakeTimers(); vi.setSystemTime(new Date(2026, 8, 7, 0, 30))
  const wrapper = mount(DateRangeShortcuts)
  await wrapper.findAll('button')[0].trigger('click')
  expect(wrapper.emitted('change').at(-1)[0]).toEqual({ date_from: '2026-09-01', date_to: '2026-09-07' })
  await wrapper.findAll('button')[1].trigger('click')
  expect(wrapper.emitted('change').at(-1)[0]).toEqual({ date_from: '2026-08-09', date_to: '2026-09-07' })
  await wrapper.findAll('button')[2].trigger('click')
  expect(wrapper.emitted('change').at(-1)[0]).toEqual({ date_from: '', date_to: '' })
  wrapper.unmount()
})
