<template>
  <main class="p-6 lg:p-8 space-y-6">
    <header class="flex flex-wrap items-start justify-between gap-4">
      <div><h1 class="text-2xl font-bold text-gray-900">Retry Queue</h1>
        <p class="text-gray-600 mt-2">Failed and unconfirmed attendance uploads need your review. They will not retry automatically.</p></div>
      <button class="btn btn-secondary" :disabled="loading" @click="load">Refresh</button>
    </header>
    <div class="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900">
      <strong>Check Payroll before retrying unconfirmed records.</strong>
      The upload may already be saved. Do not retry a log that HR intentionally deleted.
    </div>
    <p v-if="error" role="alert" class="text-red-700">{{ error }}</p>
    <p v-if="notice" role="status" class="text-primary-700">{{ notice }}</p>
    <section class="card p-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Retry filters">
      <label class="text-sm font-medium">Attendance date from<input v-model="filters.date_from" type="date" class="input mt-1 w-full" /></label>
      <label class="text-sm font-medium">Attendance date to<input v-model="filters.date_to" type="date" class="input mt-1 w-full" /></label>
      <label class="text-sm font-medium">Payroll destination<select v-model.number="filters.slot" class="input mt-1 w-full"><option :value="0">All destinations</option><option :value="1">Payroll 1 (Primary)</option><option :value="2">Payroll 2 (Secondary)</option></select></label>
      <label class="text-sm font-medium">Status<select v-model="state" class="input mt-1 w-full"><option value="all">Failed and unconfirmed</option><option value="failed">Failed</option><option value="unconfirmed">Unconfirmed</option></select></label>
      <fieldset class="sm:col-span-2 xl:col-span-4">
        <legend class="text-sm font-medium mb-2">Employees <span class="font-normal text-gray-500">— leave unchecked to include everyone</span></legend>
        <input v-model="employeeSearch" aria-label="Find employee" placeholder="Find by name or employee code" class="input w-full mb-3" />
        <div class="flex flex-wrap gap-3 max-h-36 overflow-auto">
          <label v-for="employee in employeeOptions" :key="employee.id" class="flex gap-2 items-center text-sm border rounded px-3 py-2">
            <input v-model="filters.employee_ids" type="checkbox" :value="employee.id" />{{ employee.name }} · {{ employee.code }}
          </label>
          <span v-if="!employeeOptions.length" class="text-sm text-gray-500">No matching employees in the queue.</span>
        </div>
        <button v-if="filters.employee_ids.length" class="mt-2 text-sm underline" @click="filters.employee_ids = []">Clear employee selection ({{ filters.employee_ids.length }})</button>
      </fieldset>
    </section>
    <p v-if="invalidDates" role="alert" class="text-red-700">Start date must be on or before end date.</p>
    <p v-if="eligible.length > 10000" class="text-amber-800">More than 10,000 records match. Narrow the filters or select individual records for a smaller retry.</p>
    <section class="card overflow-hidden">
      <div class="p-4 flex flex-wrap items-center justify-between gap-3 border-b">
        <p>{{ filtered.length }} destination records · {{ selected.length }} selected</p>
        <div class="flex flex-wrap gap-2">
          <button class="btn btn-secondary" :disabled="!eligible.length || running || eligible.length > 10000" @click="selected = eligible.map(key)">Select all filtered ({{ eligible.length }})</button>
          <button class="btn btn-secondary" :disabled="!selected.length" @click="selected = []">Clear selection</button>
          <button class="btn btn-primary" :disabled="!selected.length || running || loading" @click="openReview">Review &amp; retry selected ({{ selected.length }})</button>
        </div>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm text-left">
          <thead class="bg-gray-50 text-gray-600"><tr><th class="p-3">Select</th><th class="p-3">Employee</th><th class="p-3">Attendance</th><th class="p-3">Destination</th><th class="p-3">Status / reason</th><th class="p-3">Last attempt (UTC)</th></tr></thead>
          <tbody class="divide-y">
            <tr v-for="row in pageRows" :key="key(row)">
              <td class="p-3"><input v-model="selected" type="checkbox" :value="key(row)" :disabled="!!row.busy || running" :aria-label="`Select ${row.employee_name}, ${row.date}, Payroll ${row.slot}`" /></td>
              <td class="p-3 whitespace-nowrap"><strong>{{ row.employee_name }}</strong><div class="text-gray-500">{{ row.employee_code }}</div></td>
              <td class="p-3 whitespace-nowrap">{{ row.date }}<div class="text-gray-500">{{ row.time }} · {{ row.log_type.toUpperCase() }}</div></td>
              <td class="p-3 whitespace-nowrap">Payroll {{ row.slot }}<div class="text-gray-500">{{ row.slot === 1 ? 'Primary' : 'Secondary' }}</div></td>
              <td class="p-3 min-w-64"><strong :class="row.state === 'failed' ? 'text-red-700' : 'text-amber-700'">{{ row.busy ? 'Syncing / awaiting confirmation' : row.state === 'failed' ? 'Failed — manual retry' : 'Unconfirmed — check Payroll' }}</strong><p class="text-gray-600 mt-1">{{ row.reason || 'No confirmation was saved.' }}</p></td>
              <td class="p-3 whitespace-nowrap">{{ row.attempted_at }}<div class="text-gray-500">{{ row.attempts }} attempt(s)</div></td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!filtered.length" class="p-10 text-center text-gray-500">{{ loading ? 'Loading retry queue…' : rows.length ? 'No records match these filters.' : 'No attendance uploads need a manual retry.' }}</p>
      <footer v-if="filtered.length" class="p-4 border-t flex items-center justify-between"><button class="btn btn-secondary" :disabled="page === 1" @click="page--">Previous</button><span>Page {{ page }} of {{ pages }}</span><button class="btn btn-secondary" :disabled="page >= pages" @click="page++">Next</button></footer>
    </section>
    <div v-if="review" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" @keydown.esc="review = false">
      <section ref="dialog" @keydown.tab="trapFocus" role="dialog" aria-modal="true" aria-labelledby="retry-review-title" class="bg-white rounded-xl shadow-xl max-w-xl w-full p-6 space-y-4">
        <h2 id="retry-review-title" class="text-xl font-bold">Review {{ selectedRows.length }} destination records</h2>
        <p>This sends only the selected attendance records to their listed Payroll destinations.</p>
        <p class="text-sm text-gray-600">{{ reviewScope }}</p>
        <p>{{ failedCount }} failed · {{ unconfirmedCount }} unconfirmed</p>
        <p v-if="unconfirmedCount" class="text-amber-800">Unconfirmed uploads may already exist in Payroll. Retrying can recreate an intentionally deleted log.</p>
        <label v-if="unconfirmedCount" class="flex gap-3 items-start"><input v-model="reviewedPayroll" type="checkbox" class="mt-1" />I checked these unconfirmed records in Payroll and verified they should be sent again.</label>
        <p v-if="error" role="alert" class="text-red-700">{{ error }}</p>
        <div class="flex justify-end gap-3"><button class="btn btn-secondary" :disabled="running" @click="review = false">Cancel</button><button class="btn btn-primary" :disabled="running || !selectedRows.length || (unconfirmedCount > 0 && !reviewedPayroll)" @click="retry">Retry {{ selectedRows.length }} records now</button></div>
      </section>
    </div>
  </main>
</template>

<script setup>
import { nextTick, computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import bridge from '../services/bridge'
const dialog = ref(null)
let previousFocus
const rows = ref([]), selected = ref([]), loading = ref(false), running = ref(false)
const error = ref(''), notice = ref(''), review = ref(false), reviewedPayroll = ref(false)
const employeeSearch = ref(''), state = ref('all'), page = ref(1)
const filters = reactive({ date_from: '', date_to: '', employee_ids: [], slot: 0 })
const key = row => `${row.id}:${row.slot}`
const invalidDates = computed(() => filters.date_from && filters.date_to && filters.date_from > filters.date_to)
const employeeOptions = computed(() => {
  const employees = new Map(rows.value.map(r => [r.employee_id, { id: r.employee_id, name: r.employee_name, code: r.employee_code }]))
  const term = employeeSearch.value.toLowerCase()
  return [...employees.values()].filter(e => `${e.name} ${e.code}`.toLowerCase().includes(term)).sort((a, b) => a.name.localeCompare(b.name))
})
const filtered = computed(() => invalidDates.value ? [] : rows.value.filter(r =>
  (!filters.date_from || r.date >= filters.date_from) && (!filters.date_to || r.date <= filters.date_to) &&
  (!filters.employee_ids.length || filters.employee_ids.includes(r.employee_id)) &&
  (!filters.slot || r.slot === filters.slot) && (state.value === 'all' || r.state === state.value)))
const eligible = computed(() => filtered.value.filter(r => !r.busy))
const selectedRows = computed(() => eligible.value.filter(r => selected.value.includes(key(r))))
const unconfirmedCount = computed(() => selectedRows.value.filter(r => r.state === 'unconfirmed').length)
const failedCount = computed(() => selectedRows.value.length - unconfirmedCount.value)
const pages = computed(() => Math.max(1, Math.ceil(filtered.value.length / 50)))
const pageRows = computed(() => filtered.value.slice((page.value - 1) * 50, page.value * 50))
watch([filters, state], () => { selected.value = []; page.value = 1; review.value = false })
async function load() {
  if (loading.value) return
  loading.value = true
  try {
    const result = await bridge.getRetryQueue({})
    rows.value = result.data
    selected.value = selected.value.filter(id => eligible.value.some(r => key(r) === id))
    page.value = Math.min(page.value, pages.value)
  } catch (err) { error.value = err.message }
  finally { loading.value = false }
}
const reviewScope = computed(() => {
  const selected = selectedRows.value
  const employees = [...new Set(selected.map(r => `${r.employee_name} (${r.employee_code})`))]
  const dates = selected.map(r => r.date).sort()
  return `${employees.slice(0, 3).join(', ')}${employees.length > 3 ? ` and ${employees.length - 3} more` : ''} · ${dates[0] || ''} to ${dates.at(-1) || ''}`
})
async function openReview() {
  previousFocus = document.activeElement
  error.value = ''; reviewedPayroll.value = false; review.value = true
  await nextTick(); dialog.value?.querySelector('input, button')?.focus()
}
watch(review, value => { if (!value) previousFocus?.focus() })
function trapFocus(event) {
  const controls = [...dialog.value.querySelectorAll('button:not(:disabled), input:not(:disabled)')]
  const first = controls[0], last = controls.at(-1)
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
}
async function retry() {
  running.value = true; error.value = ''; notice.value = ''
  try {
    await bridge.retryTimesheets({ items: selectedRows.value.map(({ id, slot }) => ({ id, slot })), filters: { ...filters, state: state.value }, reviewed_payroll: reviewedPayroll.value })
    review.value = false; selected.value = []; notice.value = 'Manual retry started. Results will appear here.'
    await load()
  } catch (err) { error.value = err.message; running.value = false }
}
function completed(event) {
  if (event.detail?.type !== 'push') return
  if (event.detail.manual_retry) {
    running.value = false
    notice.value = event.detail.result?.message || 'Manual retry completed. Review any remaining records.'
  }
  load()
}
let timer, disposed = false
onMounted(async () => {
  window.addEventListener('syncCompleted', completed)
  await bridge.whenReady()
  if (disposed) return
  await load()
  if (disposed) return
  timer = setInterval(() => { if (!review.value) load() }, 5000)
})
onUnmounted(() => { disposed = true; clearInterval(timer); window.removeEventListener('syncCompleted', completed) })
</script>
