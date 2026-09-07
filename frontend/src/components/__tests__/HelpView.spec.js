import { afterEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import HelpView from '../HelpView.vue'
import { guidePrompt, helpSections } from '../../content/helpGuide'
const bridge = vi.hoisted(() => ({ isReady: true, openChatGPTGuide: vi.fn(), copyHelpGuide: vi.fn() }))
vi.mock('../../services/bridge', () => ({ default: bridge }))
let wrapper
afterEach(() => { wrapper?.unmount(); vi.restoreAllMocks(); vi.clearAllMocks(); bridge.isReady = true })
const button = text => wrapper.findAll('button').find(b => b.text().startsWith(text))
it('searches visible help but sends the complete canonical guide to ChatGPT', async () => {
  bridge.openChatGPTGuide.mockResolvedValue({ message: 'ChatGPT opened' })
  wrapper = mount(HelpView)
  await wrapper.find('input[type="search"]').setValue('grouped')
  expect(wrapper.findAll('h2')).toHaveLength(1)
  await button('Ask ChatGPT').trigger('click'); await flushPromises()
  expect(bridge.openChatGPTGuide).toHaveBeenCalledWith(guidePrompt)
  for (const section of helpSections) expect(guidePrompt).toContain(section.title)
  expect(guidePrompt).toContain('10,000 uploads')
  expect(guidePrompt).toContain('32 attendance logs')
  expect(guidePrompt).toContain('Comm Key')
})
it('copies the same complete guide and provides selectable text after a copy error', async () => {
  wrapper = mount(HelpView)
  bridge.copyHelpGuide.mockRejectedValue(new Error('Unavailable'))
  await button('Copy Guide').trigger('click'); await flushPromises()
  expect(bridge.copyHelpGuide).toHaveBeenCalledWith(guidePrompt)
  expect(wrapper.find('textarea').element.value).toBe(guidePrompt)
  expect(wrapper.find('[role="alert"]').text()).toContain('Copy was unavailable')
})
it('opens an encoded ChatGPT URL in browser mode and handles blocked popups', async () => {
  bridge.isReady = false
  const tab = { opener: {} }
  const open = vi.spyOn(window, 'open').mockReturnValue(tab)
  wrapper = mount(HelpView)
  await button('Ask ChatGPT').trigger('click')
  const url = new URL(open.mock.calls[0][0])
  expect(url.origin).toBe('https://chatgpt.com')
  expect(url.searchParams.get('q')).toBe(guidePrompt)
  expect(tab.opener).toBeNull()
  open.mockReturnValue(null)
  await button('Ask ChatGPT').trigger('click')
  expect(wrapper.find('[role="alert"]').text()).toContain('blocked')
  expect(wrapper.find('textarea').element.value).toBe(guidePrompt)
})
it('shows a manual fallback when the desktop browser cannot open', async () => {
  bridge.openChatGPTGuide.mockRejectedValue(new Error('Could not open the browser'))
  wrapper = mount(HelpView)
  await button('Ask ChatGPT').trigger('click'); await flushPromises()
  expect(wrapper.find('[role="alert"]').text()).toContain('Could not open')
  expect(wrapper.find('textarea').element.value).toBe(guidePrompt)
})
