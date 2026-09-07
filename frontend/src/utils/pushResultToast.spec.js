import { describe, it, expect, vi } from 'vitest'
import { showPushResultToasts } from './pushResultToast'

describe('duplicate push results', () => {
  it('reports a skipped duplicate without claiming a new upload or failure', () => {
    const toast = { success: vi.fn(), error: vi.fn(), info: vi.fn() }
    showPushResultToasts({ per_config: [{ slot: 2, stats: { success: 0, failed: 0, duplicates: 1 } }] }, toast)
    expect(toast.success).not.toHaveBeenCalled()
    expect(toast.error).not.toHaveBeenCalled()
    expect(toast.info).toHaveBeenCalledWith('1 duplicate(s) skipped; will not retry')
  })

  it('separates uploaded and skipped counts for two destinations', () => {
    const toast = { success: vi.fn(), error: vi.fn(), info: vi.fn() }
    showPushResultToasts({ per_config: [
      { slot: 1, label: 'Payroll 1', stats: { success: 1, failed: 0 } },
      { slot: 2, label: 'Payroll 2', stats: { success: 0, failed: 0, duplicates: 1 } },
    ] }, toast)
    expect(toast.success).toHaveBeenCalledWith('Payroll 1: 1 synced')
    expect(toast.info).toHaveBeenCalledWith('Payroll 2: 1 duplicate(s) skipped; will not retry')
    expect(toast.error).not.toHaveBeenCalled()
  })
})
