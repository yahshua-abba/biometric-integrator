/**
 * Show push-sync result as separate colored toasts:
 *   - one GREEN toast summarizing what synced (if anything did)
 *   - one RED toast summarizing what failed (if anything did)
 * A mixed result therefore produces exactly two toasts.
 *
 * Counts are attributed PER destination so the same record pushed to two
 * payrolls isn't confusingly reported as both "synced" and "failed" in one line.
 *
 * @param {object} result  The push result: { success, message, error, stats, per_config }
 * @param {object} toast   { success, error, info } from useToast()
 */
/**
 * Turn a {reason: count} map into a short human string.
 *   1 reason  -> "Employee not found in payroll system"
 *   N reasons -> "Employee not found (3); Invalid date (1)" (capped at 3 shown)
 */
function summarizeReasons(reasons) {
  if (!reasons || typeof reasons !== 'object') return ''
  const entries = Object.entries(reasons)
  if (entries.length === 0) return ''
  if (entries.length === 1) return entries[0][0]

  const shown = entries.slice(0, 3).map(([msg, n]) => `${msg} (${n})`)
  if (entries.length > 3) shown.push(`+${entries.length - 3} more`)
  return shown.join('; ')
}

export function showPushResultToasts(result, { success, error, info }) {
  if (!result) return

  const perConfig = Array.isArray(result.per_config) ? result.per_config : []

  // Fallback: no per-destination breakdown (e.g. an early/hard failure) — one toast.
  if (perConfig.length === 0) {
    if (result.success) {
      success(result.message || 'Push completed')
    } else {
      error(result.message || result.error || 'Push failed')
    }
    return
  }

  const showLabel = perConfig.length > 1
  const syncedParts = []
  const failedParts = []

  for (const cfg of perConfig) {
    const label = cfg.label || `Payroll ${cfg.slot ?? ''}`.trim()
    const s = (cfg.stats && cfg.stats.success) || 0
    const f = (cfg.stats && cfg.stats.failed) || 0

    // A destination-level hard error (auth/network) counts as a failure.
    if (cfg.error) {
      failedParts.push(showLabel ? `${label}: ${cfg.error}` : cfg.error)
      continue
    }
    if (s > 0) {
      syncedParts.push(showLabel ? `${label}: ${s} synced` : `${s} record${s === 1 ? '' : 's'} synced`)
    }
    if (f > 0) {
      const base = showLabel ? `${label}: ${f} failed` : `${f} record${f === 1 ? '' : 's'} failed`
      const reason = summarizeReasons(cfg.stats && cfg.stats.reasons)
      failedParts.push(reason ? `${base} — ${reason}` : base)
    }
  }

  if (syncedParts.length) success(syncedParts.join('  ·  '))
  if (failedParts.length) error(failedParts.join('  ·  '))

  // Nothing synced and nothing failed → there was nothing to push.
  if (!syncedParts.length && !failedParts.length) {
    if (info) info(result.message || 'No records to sync')
  }
}
