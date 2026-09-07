import { afterEach, expect, it } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import AppSelect from '../AppSelect.vue'
let wrapper
afterEach(() => { wrapper?.unmount() })
const options = [{ value: 0, label: 'All destinations' }, { value: 1, label: 'Payroll 1' }, { value: 2, label: 'Payroll 2' }]
const setup = () => { wrapper = mount(AppSelect, { attachTo: document.body, props: { label: 'Payroll destination', options, modelValue: 0 } }); return wrapper.find('[role="combobox"]') }
it('supports arrows, Escape cancellation, typeahead, and committing typed numeric values', async () => {
  const trigger = setup()
  await trigger.trigger('keydown', { key: 'ArrowDown' })
  await trigger.trigger('keydown', { key: 'ArrowDown' })
  expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  await trigger.trigger('keydown', { key: 'Escape' })
  expect(document.querySelector('[role="listbox"]')).toBeNull()
  await trigger.trigger('keydown', { key: 'p' })
  await trigger.trigger('keydown', { key: 'Enter' })
  expect(wrapper.emitted('update:modelValue')).toEqual([[1]])
  expect(document.activeElement).toBe(trigger.element)
})
it('marks the current selection, supports pointer selection, and closes on outside interaction or Tab', async () => {
  const trigger = setup()
  await trigger.trigger('click')
  expect(document.querySelector('[role="option"][aria-selected="true"]').textContent).toContain('All destinations')
  document.querySelectorAll('[role="option"]')[2].click(); await flushPromises()
  expect(wrapper.emitted('update:modelValue')).toEqual([[2]])
  await trigger.trigger('click'); document.body.dispatchEvent(new Event('pointerdown', { bubbles: true })); await flushPromises()
  expect(document.querySelector('[role="listbox"]')).toBeNull()
  await trigger.trigger('click'); await trigger.trigger('keydown', { key: 'Tab' })
  expect(document.querySelector('[role="listbox"]')).toBeNull()
})
it('renders above a control near the viewport bottom and outside clipping panels', async () => {
  const trigger = setup()
  trigger.element.getBoundingClientRect = () => ({ left: 20, width: 180, top: window.innerHeight - 45, bottom: window.innerHeight - 10 })
  await trigger.trigger('click')
  const menu = document.querySelector('[role="listbox"]')
  expect(menu.parentElement).toBe(document.body)
  expect(menu.style.bottom).toBe('51px')
  expect(menu.style.top).toBe('')
})
