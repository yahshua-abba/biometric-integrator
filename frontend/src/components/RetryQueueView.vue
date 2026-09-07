<template>
  <main class="retry-queue p-6 lg:p-8 max-w-screen-2xl mx-auto space-y-5">
    <header class="flex items-start justify-between gap-4">
      <div><h1 class="text-2xl font-semibold tracking-tight text-gray-900">Logs Needing Review</h1><p class="text-sm text-gray-500 mt-1">Review employees first, then the uploads that need attention. Retries are always manual.</p></div>
      <button class="btn btn-secondary text-sm" :disabled="loading" @click="load">Refresh</button>
    </header>
    <section class="bg-white border border-gray-200 rounded-lg" aria-label="Retry filters">
      <div class="grid gap-4 p-4 sm:grid-cols-2 xl:grid-cols-4">
        <label class="text-xs font-medium text-gray-500">Attendance date from<input v-model="filters.date_from" type="date" class="input text-sm mt-1.5 text-gray-900" /></label>
        <label class="text-xs font-medium text-gray-500">Attendance date to<input v-model="filters.date_to" type="date" class="input text-sm mt-1.5 text-gray-900" /></label>
        <label class="text-xs font-medium text-gray-500">Payroll destination<select v-model.number="filters.slot" class="input text-sm mt-1.5 text-gray-900"><option :value="0">All destinations</option><option :value="1">Payroll 1 (Primary)</option><option :value="2">Payroll 2 (Secondary)</option></select></label>
        <RetryEmployeeFilter v-model="employees" :filters="filters" @open-change="pickerOpen = $event" />
      </div>
      <div class="px-4 pb-3 flex flex-wrap items-center gap-3 text-xs text-gray-500"><DateRangeShortcuts @change="range => Object.assign(filters, range)" /><span v-if="employees.length" class="ml-auto">{{ employeeSummary }}</span></div>
    </section>
    <p v-if="invalidDates" role="alert" class="text-sm text-red-700">Start date must be on or before end date.</p>
    <p v-if="error" role="alert" class="text-sm text-red-700">{{ error }}</p>
    <p v-if="notice" role="status" class="text-sm text-primary-700">{{ notice }}</p>
    <section class="bg-white border border-gray-200 rounded-lg overflow-hidden" :aria-busy="loading">
      <div class="border-b border-gray-200 flex flex-wrap items-center justify-between gap-3 px-4">
        <nav class="flex gap-6" aria-label="Upload status">
          <button v-for="tab in tabs" :key="tab.id" :aria-pressed="state === tab.id" :class="['py-4 border-b-2 text-sm font-medium', state === tab.id ? 'border-primary-600 text-primary-700' : 'border-transparent text-gray-500']" @click="state = tab.id">
            {{ tab.label }} <span class="ml-1.5 bg-gray-100 text-gray-600 rounded px-1.5 py-0.5 text-xs">{{ number(data.counts[tab.id]) }}</span>
          </button>
        </nav>
        <div class="flex bg-gray-100 rounded p-0.5 text-xs" aria-label="Queue view"><button :class="['px-3 py-1.5 rounded', mode === 'employees' && !focusEmployee ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500']" @click="showEmployees">By employee</button><button :class="['px-3 py-1.5 rounded', mode === 'logs' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500']" @click="mode = 'logs'">Individual logs</button></div>
      </div>
      <div v-if="state === 'unconfirmed'" class="bg-amber-50 border-b border-amber-100 px-4 py-3 text-sm text-amber-900">These uploads may already be in Payroll. Check before retrying; an intentional HR deletion must not be restored.</div>
      <div v-else class="px-4 pt-3 text-xs text-gray-500">Correct the reported problem before retrying. Counts represent uploads to each Payroll destination.</div>
      <div class="px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div v-if="focusEmployee" class="flex items-center gap-2 text-sm mb-1"><button class="text-primary-700" @click="showEmployees">← Employees</button><span class="text-gray-300">/</span><strong>{{ focusEmployee.employee_name }}</strong></div>
          <p class="text-sm text-gray-600"><strong class="text-gray-900">{{ number(data.uploads) }}</strong> uploads across <strong class="text-gray-900">{{ number(data.employees) }}</strong> {{ data.employees === 1 ? 'employee' : 'employees' }}<span v-if="selected.length"> · {{ selected.length }} {{ mode === 'employees' ? 'employees' : 'uploads' }} selected</span></p>
        </div>
        <div class="flex flex-wrap gap-3 items-center">
          <button v-if="selected.length" class="text-xs text-gray-500" @click="selected = []">Clear selection</button>
          <button v-if="selected.length" class="btn btn-primary text-sm" :disabled="loading || preparing || running" @click="reviewSelected">Review selected</button>
          <button v-else class="text-sm text-primary-700 font-medium disabled:text-gray-400" :disabled="!data.available || data.available > 10000 || loading || preparing || running" @click="reviewFiltered">Review all filtered ({{ number(data.available) }})</button>
        </div>
      </div>
      <p v-if="data.available > 10000 && !selected.length" class="px-4 pb-3 text-xs text-gray-500">Choose employees or narrow the dates to review up to 10,000 uploads at a time.</p>
      <div class="overflow-x-auto">
        <table class="w-full text-sm text-left">
          <thead class="bg-gray-50 border-y text-xs text-gray-500"><tr>
            <th class="py-3 pl-4 w-12"><input type="checkbox" aria-label="Select this page" :checked="allPageSelected" :disabled="!data.rows.length || loading || running" @change="selectPage($event.target.checked)" /></th>
            <th class="p-3">Employee</th>
            <template v-if="mode === 'employees'"><th class="p-3">Uploads</th><th class="p-3">Attendance dates</th><th class="p-3">Issue</th><th class="p-3"><span class="sr-only">View employee logs</span></th></template>
            <template v-else><th class="p-3">Attendance</th><th class="p-3">Destination</th><th class="p-3">Issue</th></template>
          </tr></thead>
          <tbody class="divide-y divide-gray-100" :class="loading ? 'opacity-50 pointer-events-none' : ''">
            <tr v-for="row in data.rows" :key="key(row)" class="hover:bg-gray-50/70">
              <td class="py-3 pl-4"><input type="checkbox" :checked="selected.some(item => key(item) === key(row))" :disabled="!available(row) || loading || running" :aria-label="`Select ${row.employee_name}${mode === 'logs' ? `, ${row.date}, Payroll ${row.slot}` : ''}`" @change="selectRow(row, $event.target.checked)" /></td>
              <td class="p-3"><span class="font-medium text-gray-900">{{ row.employee_name }}</span><div class="text-xs text-gray-500 mt-0.5">{{ row.employee_code }}</div></td>
              <template v-if="mode === 'employees'">
                <td class="p-3 whitespace-nowrap"><strong class="font-medium">{{ number(row.uploads) }}</strong><div class="text-xs text-gray-500 mt-0.5">{{ number(row.logs) }} attendance logs</div></td>
                <td class="p-3 whitespace-nowrap text-xs text-gray-600">{{ row.first_date }}<span v-if="row.last_date !== row.first_date" class="block mt-1">to {{ row.last_date }}</span></td>
                <td class="p-3 max-w-xs text-gray-600 text-xs"><span v-if="row.issue_count > 1">{{ row.issue_count }} different issues</span><span v-else class="line-clamp-2">{{ row.reason || 'No confirmation saved' }}</span></td>
                <td class="p-3 text-right whitespace-nowrap"><button class="text-primary-700 text-xs font-medium" :aria-label="`View logs for ${row.employee_name}`" @click="openEmployee(row)">View logs →</button></td>
              </template>
              <template v-else>
                <td class="p-3 whitespace-nowrap text-xs">{{ row.date }}<div class="text-gray-500 mt-1">{{ row.time }} · {{ row.log_type.toUpperCase() }}</div></td>
                <td class="p-3 whitespace-nowrap text-xs">Payroll {{ row.slot }}</td>
                <td class="p-3 max-w-lg text-xs"><span v-if="row.busy" class="text-gray-500">Awaiting confirmation…</span><details v-else><summary class="cursor-pointer text-gray-700">{{ row.state === 'failed' ? 'Failed' : 'Unconfirmed' }} · {{ shortReason(row.reason) }}</summary><div class="mt-2 space-y-1 text-gray-500"><p>{{ row.reason || 'No confirmation was saved. Check Payroll first.' }}</p><p>Last attempt: {{ row.attempted_at }} UTC · {{ row.attempts }} attempt(s)</p></div></details></td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="!data.rows.length" class="px-6 py-14 text-center text-sm"><p class="font-medium text-gray-700">{{ loading ? 'Loading queue…' : 'No matching ' + (state === 'failed' ? 'failed' : 'unconfirmed') + ' uploads' }}</p><p class="text-gray-500 mt-1">Try another date range, employee, or status.</p></div>
      <TablePagination :page="data.page" v-model:page-size="pageSize" :total="data.total" :unit="mode === 'employees' ? (data.total === 1 ? 'employee' : 'employees') : (data.total === 1 ? 'upload' : 'uploads')" :loading="loading" @update:page="page = $event" />
    </section>
    <div v-if="review" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" @keydown.esc="review = false">
      <section ref="dialog" @keydown.tab="trapFocus" role="dialog" aria-modal="true" aria-labelledby="retry-review-title" class="bg-white rounded-xl shadow-xl max-w-xl w-full p-6 space-y-4">
        <h2 id="retry-review-title" class="text-xl font-semibold">Review {{ number(reviewRows.length) }} uploads</h2>
        <p class="text-sm text-gray-600">{{ reviewScope }}</p><p class="text-sm">{{ number(failedCount) }} failed · {{ number(unconfirmedCount) }} unconfirmed</p>
        <p class="text-sm text-gray-500">Only these selected uploads will be sent. New arrivals are not added to this retry.</p>
        <p v-if="unconfirmedCount" class="text-sm text-amber-800">Unconfirmed uploads may already exist in Payroll. Retrying can recreate an intentionally deleted log.</p>
        <label v-if="unconfirmedCount" class="flex gap-3 items-start text-sm"><input v-model="reviewedPayroll" type="checkbox" class="mt-1" />I checked these unconfirmed records in Payroll and verified they should be sent again.</label>
        <p v-if="error" role="alert" class="text-sm text-red-700">{{ error }}</p>
        <div class="flex justify-end gap-3"><button class="btn btn-secondary" :disabled="running" @click="review = false">Cancel</button><button class="btn btn-primary" :disabled="running || !reviewRows.length || (unconfirmedCount > 0 && !reviewedPayroll)" @click="retry">Retry {{ number(reviewRows.length) }} uploads now</button></div>
      </section>
    </div>
  </main>
</template>

<script setup>
import { nextTick, computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import bridge from '../services/bridge'
import RetryEmployeeFilter from './RetryEmployeeFilter.vue'
import TablePagination from './TablePagination.vue'
import DateRangeShortcuts from './DateRangeShortcuts.vue'
const props = defineProps({ initialContext: { type: Object, default: null } })
const empty = () => ({ rows: [], total: 0, uploads: 0, employees: 0, available: 0, page: 1, counts: { failed: 0, unconfirmed: 0 } })
const data = ref(empty()), employees = ref([]), selected = ref([]), focusEmployee = ref(null)
const filters = reactive({ date_from: '', date_to: '', slot: 0 })
const state = ref('failed'), mode = ref('employees'), page = ref(1), pageSize = ref(25)
const loading = ref(false), running = ref(false), preparing = ref(false), pickerOpen = ref(false)
const error = ref(''), notice = ref(''), review = ref(false), reviewedPayroll = ref(false), reviewRows = ref([]), reviewFilters = ref({})
const dialog = ref(null)
const tabs = [{ id: 'failed', label: 'Failed' }, { id: 'unconfirmed', label: 'Unconfirmed' }]
const number = value => Number(value || 0).toLocaleString()
const employeeSummary = computed(() => employees.value.length === 1 ? employees.value[0].employee_name : `${employees.value.length} employees selected`)
const scope = computed(() => ({ ...filters, state: state.value, employee_ids: focusEmployee.value ? [focusEmployee.value.employee_id] : employees.value.map(e => e.employee_id) }))
const invalidDates = computed(() => filters.date_from && filters.date_to && filters.date_from > filters.date_to)
const key = row => mode.value === 'employees' ? row.employee_id : `${row.id}:${row.slot}`
const available = row => mode.value === 'employees' ? row.available > 0 : !row.busy
const allPageSelected = computed(() => data.value.rows.some(available) && data.value.rows.filter(available).every(r => selected.value.some(s => key(s) === key(r))))
const unconfirmedCount = computed(() => reviewRows.value.filter(r => r.state === 'unconfirmed').length)
const failedCount = computed(() => reviewRows.value.length - unconfirmedCount.value)
const reviewScope = computed(() => {
  const people = [...new Set(reviewRows.value.map(r => r.employee_name))]
  const dates = reviewRows.value.map(r => r.date).sort()
  return `${people.slice(0, 3).join(', ')}${people.length > 3 ? ` and ${people.length - 3} more employees` : ''} · ${dates[0] || ''} to ${dates.at(-1) || ''}`
})
const shortReason = reason => reason?.length > 65 ? reason.slice(0, 65) + '…' : reason || 'Check details'
let ready = false, disposed = false, version = 0, loadTicket = 0, timer, previousFocus
watch([scope, mode, pageSize], () => {
  version++; loadTicket++; preparing.value = false; selected.value = []; review.value = false; page.value = 1; data.value = empty()
  if (ready) load()
}, { deep: true })
watch(page, () => { if (ready) load() })
watch(employees, () => { focusEmployee.value = null }, { deep: true })
function showEmployees() { focusEmployee.value = null; mode.value = 'employees' }
function openEmployee(row) { focusEmployee.value = row; mode.value = 'logs' }
function selectRow(row, checked) {
  selected.value = selected.value.filter(s => key(s) !== key(row))
  if (checked) selected.value.push(row)
}
function selectPage(checked) { data.value.rows.filter(available).forEach(row => selectRow(row, checked)) }
async function load() {
  const ticket = ++loadTicket
  if (invalidDates.value) { data.value = empty(); loading.value = false; return }
  loading.value = true
  try {
    const result = await bridge.getRetryQueuePage({ ...scope.value, mode: mode.value, page: page.value, page_size: pageSize.value })
    if (disposed || ticket !== loadTicket) return
    data.value = result.data; page.value = result.data.page; error.value = ''
  } catch (err) { if (ticket === loadTicket) { data.value = empty(); error.value = err.message } }
  finally { if (ticket === loadTicket) loading.value = false }
}
async function prepareReview(selectionScope, explicitRows = null) {
  const current = version
  previousFocus = document.activeElement; error.value = ''; preparing.value = true
  try {
    const rows = explicitRows || (await bridge.getRetrySelection(selectionScope)).data
    if (disposed || current !== version) return
    if (!rows.length) throw new Error('No selected uploads remain available. Refresh the queue.')
    reviewRows.value = rows; reviewFilters.value = JSON.parse(JSON.stringify(selectionScope))
    reviewedPayroll.value = false; review.value = true
    await nextTick(); dialog.value?.querySelector('input, button')?.focus()
  } catch (err) { if (current === version) error.value = err.message }
  finally { if (current === version) preparing.value = false }
}
function reviewFiltered() { return prepareReview({ ...scope.value }) }
function reviewSelected() {
  if (mode.value === 'employees') return prepareReview({ ...scope.value, employee_ids: selected.value.map(r => r.employee_id) })
  return prepareReview({ ...scope.value }, selected.value.filter(r => !r.busy))
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
    await bridge.retryTimesheets({ items: reviewRows.value.map(({ id, slot }) => ({ id, slot })), filters: reviewFilters.value, reviewed_payroll: reviewedPayroll.value })
    review.value = false; selected.value = []; notice.value = 'Manual retry started. Results will appear here.'
    await load()
  } catch (err) { error.value = err.message; running.value = false }
}
function completed(event) {
  if (event.detail?.type !== 'push') return
  if (event.detail.manual_retry) { running.value = false; notice.value = event.detail.result?.message || 'Manual retry completed.' }
  load()
}
function applyContext(context) {
  employees.value = context?.employee ? [context.employee] : []
  filters.date_from = context?.date || ''; filters.date_to = context?.date || ''; filters.slot = 0
  state.value = context?.state === 'unconfirmed' ? 'unconfirmed' : 'failed'
  mode.value = context?.employee ? 'logs' : 'employees'
}
watch(() => props.initialContext, applyContext)
applyContext(props.initialContext)
onMounted(async () => {
  window.addEventListener('syncCompleted', completed)
  await bridge.whenReady(); if (disposed) return
  ready = true; await load(); if (disposed) return
  timer = setInterval(() => { if (!review.value && !preparing.value && !pickerOpen.value && !selected.value.length && !loading.value) load() }, 15000)
})
onUnmounted(() => { disposed = true; version++; loadTicket++; clearInterval(timer); window.removeEventListener('syncCompleted', completed) })
</script>
<style scoped>
.retry-queue { font-variant-numeric: tabular-nums; }
.retry-queue button:focus-visible, .retry-queue input:focus-visible, .retry-queue summary:focus-visible { outline: 2px solid #2563eb; outline-offset: 3px; }
.retry-queue button:disabled { cursor: not-allowed; }
</style>
