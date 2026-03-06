/**
 * Regression tests for DashboardView.vue — push button disabled state
 *
 * Run with:
 *   cd frontend && npm test
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import DashboardView from '../DashboardView.vue'

// ---------------------------------------------------------------------------
// Mock the bridge service — no QWebChannel available in tests
//
// vi.mock() is hoisted to the top of the file by vitest, so the factory
// cannot reference variables declared with const/let in module scope.
// Use vi.hoisted() to declare the mock object before hoisting occurs.
// ---------------------------------------------------------------------------

const mockBridge = vi.hoisted(() => ({
  whenReady: vi.fn().mockResolvedValue(undefined),
  getTimesheetStats: vi.fn(),
  getApiConfig: vi.fn().mockResolvedValue({ success: true, data: {} }),
  getDevices: vi.fn().mockResolvedValue({ success: true, data: [] }),
  getSyncLogs: vi.fn().mockResolvedValue({ success: true, data: [] }),
  startPushSync: vi.fn().mockResolvedValue({ success: true, message: 'Push sync started' }),
  startPullSync: vi.fn().mockResolvedValue({ success: true, message: 'Pull sync started' }),
}))

vi.mock('../../services/bridge', () => ({ default: mockBridge }))

// SyncProgressModal is a child — stub it to keep tests focused on DashboardView
vi.mock('../SyncProgressModal.vue', () => ({
  default: { template: '<div />' }
}))

// useToast — stub so we don't need the full composable
vi.mock('../../composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() })
}))

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function mountWithStats(statsData) {
  mockBridge.getTimesheetStats.mockResolvedValue({ success: true, data: statsData })

  const wrapper = mount(DashboardView, {
    global: { stubs: { SyncProgressModal: true } }
  })

  // Wait for onMounted async calls to resolve
  await nextTick()
  await nextTick()

  return wrapper
}

// ---------------------------------------------------------------------------
// Push button disabled state — REGRESSION for Bug #2
// ---------------------------------------------------------------------------

describe('Push button disabled state', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockBridge.getApiConfig.mockResolvedValue({ success: true, data: {} })
    mockBridge.getDevices.mockResolvedValue({ success: true, data: [] })
    mockBridge.getSyncLogs.mockResolvedValue({ success: true, data: [] })
  })

  it('is disabled when pending=0 and errors=0 (nothing to push)', async () => {
    const wrapper = await mountWithStats({ total: 50, synced: 50, pending: 0, errors: 0 })

    const btn = wrapper.find('button.btn-success')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('is enabled when pending > 0', async () => {
    const wrapper = await mountWithStats({ total: 10, synced: 5, pending: 5, errors: 0 })

    const btn = wrapper.find('button.btn-success')
    expect(btn.attributes('disabled')).toBeUndefined()
  })

  it('is enabled when errors > 0 and pending = 0 (REGRESSION for Bug #2)', async () => {
    /**
     * Before the fix, this button would be disabled because stats.pending === 0.
     * But error records are still in the unsynced queue and CAN be pushed.
     * The fix changes the condition to: (stats.pending + stats.errors) === 0
     */
    const wrapper = await mountWithStats({ total: 10, synced: 5, pending: 0, errors: 5 })

    const btn = wrapper.find('button.btn-success')
    expect(btn.attributes('disabled')).toBeUndefined()
  })

  it('is disabled while a push is in progress (prevents double-submit)', async () => {
    const wrapper = await mountWithStats({ total: 10, synced: 5, pending: 5, errors: 0 })

    // Trigger push but don't resolve it — keeps pushLoading = true
    mockBridge.startPushSync.mockReturnValue(new Promise(() => {}))
    await wrapper.find('button.btn-success').trigger('click')
    await nextTick()

    const btn = wrapper.find('button.btn-success')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('is enabled when both pending and errors exist', async () => {
    const wrapper = await mountWithStats({ total: 20, synced: 5, pending: 3, errors: 12 })

    const btn = wrapper.find('button.btn-success')
    expect(btn.attributes('disabled')).toBeUndefined()
  })
})
