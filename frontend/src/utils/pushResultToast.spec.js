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

describe('destination runs that stop early', () => {
  it('shows a destination that sent nothing as a failure next to one that synced', () => {
    const toast = { success: vi.fn(), error: vi.fn(), info: vi.fn() }
    showPushResultToasts({ success: false, per_config: [
      { slot: 1, label: 'Payroll 1', success: true, message: 'Push completed', stats: { success: 3, failed: 0 } },
      { slot: 2, label: 'Payroll 2', success: false, message: 'Push failed: Authentication expired - please log in again', stats: { success: 0, failed: 0 } },
    ] }, toast)
    expect(toast.success).toHaveBeenCalledWith('Payroll 1: 3 synced')
    expect(toast.error).toHaveBeenCalledWith('Payroll 2: Push failed: Authentication expired - please log in again')
  })

  it('shows a lone destination failure as an error, not as information', () => {
    const toast = { success: vi.fn(), error: vi.fn(), info: vi.fn() }
    showPushResultToasts({ success: false, message: 'Payroll 1 (Primary): Push failed: Cannot connect', per_config: [
      { slot: 1, label: 'Payroll 1 (Primary)', success: false, message: 'Push failed: Cannot connect', stats: { success: 0, failed: 0 } },
    ] }, toast)
    expect(toast.error).toHaveBeenCalledWith('Push failed: Cannot connect')
    expect(toast.info).not.toHaveBeenCalled()
  })

  it('reports why a run stopped after some uploads went through', () => {
    const toast = { success: vi.fn(), error: vi.fn(), info: vi.fn() }
    showPushResultToasts({ success: false, per_config: [
      { slot: 1, label: 'Payroll 1 (Primary)', success: false, message: 'Push failed: Cannot connect (50 synced before error, 0 failed)', stats: { success: 50, failed: 0 } },
    ] }, toast)
    expect(toast.success).toHaveBeenCalledWith('50 records synced')
    expect(toast.error).toHaveBeenCalledWith('Push failed: Cannot connect (50 synced before error, 0 failed)')
  })
})
