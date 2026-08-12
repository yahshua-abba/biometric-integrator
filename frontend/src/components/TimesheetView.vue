<template>
  <div class="p-6 space-y-6">
    <!-- Clear Timesheets Modal -->
    <div v-if="showClearModal" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black bg-opacity-50" @click="closeClearModal"></div>
      <div class="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <!-- Modal Header -->
        <div class="flex items-center justify-between p-4 border-b">
          <h3 class="text-lg font-semibold text-red-600">Clear Timesheet Records</h3>
          <button @click="closeClearModal" class="text-gray-500 hover:text-gray-700">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Modal Body -->
        <div class="p-4 space-y-4">
          <div class="bg-red-50 border border-red-200 rounded-lg p-3">
            <p class="text-sm text-red-700">
              <strong>Warning:</strong> This will permanently delete timesheet records within the selected date range. This action cannot be undone.
            </p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">From</label>
            <input
              v-model="clearDateFrom"
              type="date"
              class="input w-full"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">To</label>
            <input
              v-model="clearDateTo"
              type="date"
              class="input w-full"
            />
          </div>

          <div class="flex items-center">
            <input
              id="onlySynced"
              v-model="clearOnlySynced"
              type="checkbox"
              class="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
            />
            <label for="onlySynced" class="ml-2 text-sm text-gray-700">
              Only delete synced records
            </label>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="flex justify-end gap-2 p-4 border-t">
          <button @click="closeClearModal" class="btn btn-secondary">Cancel</button>
          <button @click="executeClear" :disabled="clearing" class="btn bg-red-600 text-white hover:bg-red-700">
            <span v-if="!clearing">Delete Records</span>
            <span v-else>Deleting...</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Mark Do Not Sync by Date Range Modal -->
    <div v-if="showExcludeRangeModal" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black bg-opacity-50" @click="showExcludeRangeModal = false"></div>
      <div class="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div class="flex items-center justify-between p-4 border-b">
          <h3 class="text-lg font-semibold text-gray-800">Mark Do Not Sync by Date Range</h3>
          <button @click="showExcludeRangeModal = false" class="text-gray-500 hover:text-gray-700">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="p-4 space-y-4">
          <p class="text-sm text-gray-600">
            All <strong>unsynced</strong> records within the selected date range will be marked as
            do-not-sync. Already-synced records are not affected.
          </p>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">From</label>
            <input v-model="excludeRangeDateFrom" type="date" class="input w-full" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">To</label>
            <input v-model="excludeRangeDateTo" type="date" class="input w-full" />
          </div>
        </div>
        <div class="flex justify-end gap-2 p-4 border-t">
          <button @click="showExcludeRangeModal = false" class="btn btn-secondary">Cancel</button>
          <button @click="executeExcludeByRange" :disabled="excludingByRange" class="btn bg-gray-700 text-white hover:bg-gray-800">
            <span v-if="!excludingByRange">Mark Do Not Sync</span>
            <span v-else>Marking...</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Delete Selected Confirmation Modal -->
    <div v-if="showDeleteSelectedModal" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black bg-opacity-50" @click="showDeleteSelectedModal = false"></div>
      <div class="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div class="flex items-center justify-between p-4 border-b">
          <h3 class="text-lg font-semibold text-red-600">Delete Selected Records</h3>
          <button @click="showDeleteSelectedModal = false" class="text-gray-500 hover:text-gray-700">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="p-4 space-y-3">
          <div class="bg-red-50 border border-red-200 rounded-lg p-3">
            <p class="text-sm text-red-700">
              <strong>{{ selectedIds.length }} record(s)</strong> will be deleted. They will no longer appear
              in the timesheet list and will not be synced to payroll — even if the biometric device
              re-supplies the same logs on a future pull.
            </p>
          </div>
        </div>
        <div class="flex justify-end gap-2 p-4 border-t">
          <button @click="showDeleteSelectedModal = false" class="btn btn-secondary">Cancel</button>
          <button @click="executeDeleteSelected" :disabled="deletingSelected" class="btn bg-red-600 text-white hover:bg-red-700">
            <span v-if="!deletingSelected">Delete {{ selectedIds.length }} Record(s)</span>
            <span v-else>Deleting...</span>
          </button>
        </div>
      </div>
    </div>

    <SyncProgressModal :show="showProgressModal" :configs="pushConfigs" />

    <div class="flex items-center justify-between">
      <h1 class="text-3xl font-bold text-gray-900">Timesheet Records</h1>
      <div class="flex gap-2">
        <button
          @click="syncSelected"
          :disabled="selectedIds.length === 0 || pushLoading"
          class="btn bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          :title="selectedIds.length === 0 ? 'Select pending or failed records to sync' : `Sync ${selectedIds.length} selected record(s)`"
        >
          <svg class="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          Sync Selected ({{ selectedIds.length }})
        </button>
        <button
          v-if="selectedIds.length > 0"
          @click="bulkSetExcluded(true)"
          class="btn bg-gray-200 text-gray-800 hover:bg-gray-300"
          title="Mark selected records as do-not-sync"
        >
          <svg class="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636m12.728 12.728L5.636 5.636" />
          </svg>
          Mark Do Not Sync
        </button>
        <button
          @click="openExcludeRangeModal"
          class="btn bg-gray-200 text-gray-800 hover:bg-gray-300"
          title="Mark all unsynced records in a date range as do-not-sync"
        >
          <svg class="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          Mark by Date Range
        </button>
        <button
          v-if="selectedIds.length > 0 && filterStatus === 'excluded'"
          @click="bulkSetExcluded(false)"
          class="btn bg-gray-200 text-gray-800 hover:bg-gray-300"
          title="Restore selected records so they sync again"
        >
          <svg class="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Unmark Do Not Sync
        </button>
        <button
          v-if="selectedIds.length > 0"
          @click="confirmDeleteSelected"
          class="btn bg-red-600 text-white hover:bg-red-700"
          :title="`Delete ${selectedIds.length} selected record(s)`"
        >
          <svg class="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
          Delete Selected ({{ selectedIds.length }})
        </button>
        <button @click="openClearModal" class="btn bg-red-100 text-red-700 hover:bg-red-200">
          <svg class="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
          Clear Records
        </button>
        <button @click="loadData" class="btn btn-secondary">
          <svg class="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="card">
      <div class="flex gap-4 items-center flex-wrap">
        <div class="flex-1 min-w-[200px]">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search by employee name or ID..."
            class="input"
          />
        </div>
        <div class="flex items-center gap-2">
          <label class="text-sm text-gray-600">From:</label>
          <input
            v-model="filterDateFrom"
            type="date"
            class="input w-40"
          />
        </div>
        <div class="flex items-center gap-2">
          <label class="text-sm text-gray-600">To:</label>
          <input
            v-model="filterDateTo"
            type="date"
            class="input w-40"
          />
        </div>
        <select v-model="filterDevice" class="input w-48">
          <option value="all">All Devices</option>
          <option v-for="device in devices" :key="device.id" :value="device.id">
            {{ device.name }}
          </option>
        </select>
        <select v-model="filterStatus" class="input w-48">
          <option value="all">All Records</option>
          <option value="synced">Synced</option>
          <option value="pending">Pending</option>
          <option value="error">Errors</option>
          <option value="excluded">Do Not Sync</option>
          <option value="deleted">Deleted</option>
        </select>
      </div>
    </div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div v-if="loading" class="text-center py-8 text-gray-500">
        Loading timesheets...
      </div>
      <div v-else-if="filteredTimesheets.length === 0" class="text-center py-8 text-gray-500">
        No timesheet records found
      </div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-4 py-3 text-left">
                <input
                  type="checkbox"
                  class="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                  :checked="allSelectableSelected"
                  :indeterminate.prop="someSelected && !allSelectableSelected"
                  :disabled="selectableIdsOnPage.length === 0"
                  @change="toggleSelectAll($event.target.checked)"
                  title="Select all syncable rows on this page"
                />
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Date & Time
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Employee
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Device
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Sync ID
              </th>
              <th v-if="filterStatus === 'error'" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Error Message
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="entry in paginatedTimesheets" :key="entry.id" :class="filterStatus === 'deleted' ? 'opacity-60' : ''">
              <td class="px-4 py-4">
                <input
                  v-if="isSelectable(entry) && filterStatus !== 'deleted'"
                  type="checkbox"
                  class="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                  :checked="selectedIds.includes(entry.id)"
                  @change="toggleSelection(entry.id, $event.target.checked)"
                />
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ entry.date }} {{ entry.time }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">{{ entry.employee_name }}</div>
                <div class="text-sm text-gray-500">{{ entry.employee_code || 'N/A' }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                {{ entry.device_name || '-' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  :class="[
                    'badge',
                    entry.log_type === 'in' ? 'badge-success' : 'badge-warning'
                  ]"
                >
                  {{ entry.log_type.toUpperCase() }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  v-if="combinedStatus(entry) === 'deleted'"
                  class="badge bg-red-100 text-red-600"
                  :title="`Deleted on ${formatDateTime(entry.deleted_at)}${isFullySynced(entry) ? ' · Was synced' : ' · Was not fully synced'}`"
                >
                  Deleted
                </span>
                <span
                  v-else-if="combinedStatus(entry) === 'synced'"
                  class="badge badge-success"
                  :title="statusTitle(entry)"
                >
                  Synced
                </span>
                <span
                  v-else-if="combinedStatus(entry) === 'excluded'"
                  class="badge bg-gray-200 text-gray-700"
                  title="Marked as do-not-sync"
                >
                  Do Not Sync
                </span>
                <span
                  v-else-if="combinedStatus(entry) === 'error'"
                  class="badge badge-error"
                  :title="statusTitle(entry)"
                >
                  {{ config2Active ? 'Partial / Error' : 'Error' }}
                </span>
                <span v-else class="badge badge-warning" :title="statusTitle(entry)">
                  Pending
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                {{ entry.sync_id }}
              </td>
              <td v-if="filterStatus === 'error'" class="px-6 py-4 text-sm text-red-600 max-w-md">
                <div
                  v-for="line in errorLines(entry)"
                  :key="line.slot"
                  class="truncate"
                  :title="line.label ? `${line.label}: ${line.msg}` : line.msg"
                >
                  <span v-if="line.label" class="font-semibold">{{ line.label }}:</span>
                  {{ line.msg }}
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm">
                <div v-if="!entry.deleted_at" class="flex items-center gap-3">
                  <button
                    v-if="combinedStatus(entry) === 'error'"
                    @click="retrySync(entry.id)"
                    class="text-primary-600 hover:text-primary-900"
                    title="Retry sync"
                  >
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </button>
                  <button
                    v-if="!isFullySynced(entry)"
                    @click="toggleExcluded(entry)"
                    class="text-gray-500 hover:text-gray-800"
                    :title="entry.excluded_from_sync ? 'Restore — allow syncing' : 'Mark as do-not-sync'"
                  >
                    <svg v-if="!entry.excluded_from_sync" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636" />
                    </svg>
                    <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </button>
                </div>
                <span v-else class="text-xs text-gray-400 italic">{{ formatDateTime(entry.deleted_at) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="bg-gray-50 px-6 py-4 flex items-center justify-between border-t">
        <div class="text-sm text-gray-700">
          Showing {{ (currentPage - 1) * pageSize + 1 }} to {{ Math.min(currentPage * pageSize, filteredTimesheets.length) }}
          of {{ filteredTimesheets.length }} results
        </div>
        <div class="flex gap-2">
          <button
            @click="currentPage = 1"
            :disabled="currentPage === 1"
            class="btn btn-secondary"
          >
            First
          </button>
          <button
            @click="currentPage--"
            :disabled="currentPage === 1"
            class="btn btn-secondary"
          >
            Previous
          </button>
          <span class="px-3 py-2 text-sm text-gray-600">
            Page {{ currentPage }} of {{ totalPages }}
          </span>
          <button
            @click="currentPage++"
            :disabled="currentPage === totalPages"
            class="btn btn-secondary"
          >
            Next
          </button>
          <button
            @click="currentPage = totalPages"
            :disabled="currentPage === totalPages"
            class="btn btn-secondary"
          >
            Last
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import bridgeService from '../services/bridge'
import { useToast } from '../composables/useToast'
import { showPushResultToasts } from '../utils/pushResultToast'
import SyncProgressModal from './SyncProgressModal.vue'

const { success, error, info } = useToast()

const timesheets = ref([])
const devices = ref([])
const loading = ref(false)
const searchQuery = ref('')
const filterStatus = ref('pending')
const filterDevice = ref('all')
const filterDateFrom = ref('')
const filterDateTo = ref('')
const currentPage = ref(1)
const pageSize = 50

// Selection state for manual sync
const selectedIds = ref([])
const pushLoading = ref(false)
const showProgressModal = ref(false)
const pushProgressMap = ref({})
const pushConfigs = computed(() =>
  Object.values(pushProgressMap.value).sort((a, b) => a.slot - b.slot)
)

// Whether the optional second push destination is active (loaded from config).
const config2Active = ref(false)

// Per-destination status. Slot 1 uses the original columns; slot 2 the _2 columns.
const slotSynced = (entry, slot) => {
  const b = slot === 2 ? entry.backend_timesheet_id_2 : entry.backend_timesheet_id
  return b !== null && b !== undefined
}
const slotError = (entry, slot) => {
  if (slotSynced(entry, slot)) return false
  return !!(slot === 2 ? entry.sync_error_message_2 : entry.sync_error_message)
}

const activeSlots = computed(() => (config2Active.value ? [1, 2] : [1]))

// Synced only when delivered to every active destination.
const isFullySynced = (entry) => activeSlots.value.every(s => slotSynced(entry, s))
const hasAnyError = (entry) => activeSlots.value.some(s => slotError(entry, s))

// One combined status label for the badge column.
const combinedStatus = (entry) => {
  if (entry.deleted_at) return 'deleted'
  if (isFullySynced(entry)) return 'synced'
  if (entry.excluded_from_sync) return 'excluded'
  if (hasAnyError(entry)) return 'error'
  return 'pending'
}

// Human-readable name for each push destination (matches the Configuration page).
const slotLabel = (slot) => (slot === 2 ? 'Payroll 2 (Secondary)' : 'Payroll 1 (Primary)')

const slotErrorMessage = (entry, slot) =>
  slot === 2 ? entry.sync_error_message_2 : entry.sync_error_message

// Labelled error lines for a record — one per destination that failed.
// When only one destination is active, the label is omitted (single-config view).
const errorLines = (entry) => {
  const lines = []
  for (const slot of activeSlots.value) {
    if (slotError(entry, slot)) {
      lines.push({
        slot,
        label: config2Active.value ? slotLabel(slot) : '',
        msg: slotErrorMessage(entry, slot) || 'Sync failed'
      })
    }
  }
  return lines
}

// Tooltip describing each destination when the second one is active.
const statusTitle = (entry) => {
  if (!config2Active.value) {
    return entry.backend_timesheet_id ? `Backend ID: ${entry.backend_timesheet_id}` : (entry.sync_error_message || '')
  }
  const describe = (slot) => {
    if (slotSynced(entry, slot)) return 'synced'
    if (slotError(entry, slot)) return `error — ${slotErrorMessage(entry, slot)}`
    return 'pending'
  }
  return `${slotLabel(1)}: ${describe(1)}\n${slotLabel(2)}: ${describe(2)}`
}

// A row is selectable if it has not yet been fully synced (to all active destinations).
// (Excluded rows are still selectable so the user can unmark them in bulk.)
const isSelectable = (entry) => !isFullySynced(entry)

const selectableIdsOnPage = computed(() =>
  paginatedTimesheets.value.filter(isSelectable).map(e => e.id)
)

const allSelectableSelected = computed(() =>
  selectableIdsOnPage.value.length > 0 &&
  selectableIdsOnPage.value.every(id => selectedIds.value.includes(id))
)

const someSelected = computed(() =>
  selectableIdsOnPage.value.some(id => selectedIds.value.includes(id))
)

const toggleSelection = (id, checked) => {
  if (checked) {
    if (!selectedIds.value.includes(id)) selectedIds.value.push(id)
  } else {
    selectedIds.value = selectedIds.value.filter(x => x !== id)
  }
}

const toggleSelectAll = (checked) => {
  const pageIds = selectableIdsOnPage.value
  if (checked) {
    const set = new Set([...selectedIds.value, ...pageIds])
    selectedIds.value = Array.from(set)
  } else {
    selectedIds.value = selectedIds.value.filter(id => !pageIds.includes(id))
  }
}

// Reset to page 1 and clear selection when any filter changes
watch([searchQuery, filterStatus, filterDevice, filterDateFrom, filterDateTo], () => {
  currentPage.value = 1
  selectedIds.value = []
})

// Reload from the right endpoint when switching to/from deleted view
watch(filterStatus, (newVal, oldVal) => {
  const crossesBoundary = (newVal === 'deleted') !== (oldVal === 'deleted')
  if (crossesBoundary) loadData()
})

// Initialize date filters (30 days ago to today)
const initDateFilters = () => {
  const today = new Date()
  const thirtyDaysAgo = new Date(today)
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

  filterDateFrom.value = thirtyDaysAgo.toISOString().split('T')[0]
  filterDateTo.value = today.toISOString().split('T')[0]
}

// Mark by date range state
const showExcludeRangeModal = ref(false)
const excludeRangeDateFrom = ref('')
const excludeRangeDateTo = ref('')
const excludingByRange = ref(false)

const openExcludeRangeModal = () => {
  const today = new Date()
  const weekAgo = new Date(today)
  weekAgo.setDate(weekAgo.getDate() - 7)
  excludeRangeDateFrom.value = getDateString(weekAgo)
  excludeRangeDateTo.value = getDateString(today)
  showExcludeRangeModal.value = true
}

const executeExcludeByRange = async () => {
  excludingByRange.value = true
  try {
    const result = await bridgeService.setTimesheetExcludedByDateRange(
      excludeRangeDateFrom.value,
      excludeRangeDateTo.value,
      true
    )
    success(result.message)
    showExcludeRangeModal.value = false
    await loadData()
  } catch (err) {
    error(`Failed to mark records: ${err.message}`)
  } finally {
    excludingByRange.value = false
  }
}

// Delete selected state
const showDeleteSelectedModal = ref(false)
const deletingSelected = ref(false)

const confirmDeleteSelected = () => {
  if (selectedIds.value.length === 0) return
  showDeleteSelectedModal.value = true
}

const executeDeleteSelected = async () => {
  deletingSelected.value = true
  try {
    const result = await bridgeService.deleteTimesheetsByIds(selectedIds.value)
    success(result.message)
    showDeleteSelectedModal.value = false
    selectedIds.value = []
    await loadData()
  } catch (err) {
    error(`Failed to delete records: ${err.message}`)
  } finally {
    deletingSelected.value = false
  }
}

// Clear modal state
const showClearModal = ref(false)
const clearDateFrom = ref('')
const clearDateTo = ref('')
const clearOnlySynced = ref(true)
const clearing = ref(false)

// Helper to get date in YYYY-MM-DD format
const getDateString = (date) => {
  return date.toISOString().split('T')[0]
}

const openClearModal = () => {
  // Default: last 7 days
  const today = new Date()
  const weekAgo = new Date(today)
  weekAgo.setDate(weekAgo.getDate() - 7)

  clearDateFrom.value = getDateString(weekAgo)
  clearDateTo.value = getDateString(today)
  showClearModal.value = true
}

const closeClearModal = () => {
  showClearModal.value = false
}

const executeClear = async () => {
  clearing.value = true
  try {
    const result = await bridgeService.clearTimesheets(clearDateFrom.value, clearDateTo.value, clearOnlySynced.value)
    success(result.message)
    showClearModal.value = false
    await loadData()
  } catch (err) {
    error(`Failed to clear records: ${err.message}`)
  } finally {
    clearing.value = false
  }
}

const filteredTimesheets = computed(() => {
  let filtered = timesheets.value

  // Filter by date range
  if (filterDateFrom.value) {
    filtered = filtered.filter(t => t.date >= filterDateFrom.value)
  }
  if (filterDateTo.value) {
    filtered = filtered.filter(t => t.date <= filterDateTo.value)
  }

  // Filter by device
  if (filterDevice.value !== 'all') {
    filtered = filtered.filter(t => t.device_id === filterDevice.value)
  }

  // Filter by status
  // 'deleted' records are pre-filtered by the backend endpoint — no extra filter needed
  if (filterStatus.value === 'synced') {
    filtered = filtered.filter(t => combinedStatus(t) === 'synced')
  } else if (filterStatus.value === 'pending') {
    filtered = filtered.filter(t => combinedStatus(t) === 'pending')
  } else if (filterStatus.value === 'error') {
    filtered = filtered.filter(t => combinedStatus(t) === 'error')
  } else if (filterStatus.value === 'excluded') {
    filtered = filtered.filter(t => combinedStatus(t) === 'excluded')
  }

  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(t =>
      t.employee_name?.toLowerCase().includes(query) ||
      t.employee_code?.toLowerCase().includes(query) ||
      t.sync_id?.toLowerCase().includes(query)
    )
  }

  return filtered
})

const totalPages = computed(() => {
  return Math.ceil(filteredTimesheets.value.length / pageSize)
})

const paginatedTimesheets = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  const end = start + pageSize
  return filteredTimesheets.value.slice(start, end)
})

const formatDateTime = (isoStr) => {
  if (!isoStr) return ''
  // SQLite returns strings like "2026-06-01 08:00:00.123456"
  const d = new Date(isoStr.replace(' ', 'T'))
  if (isNaN(d)) return isoStr
  return d.toLocaleString()
}

const loadData = async () => {
  loading.value = true
  try {
    // Deleted records come from a separate endpoint; they're never mixed with live records
    if (filterStatus.value === 'deleted') {
      const result = await bridgeService.getDeletedTimesheets(5000, 0)
      timesheets.value = result.data
    } else {
      const result = await bridgeService.getAllTimesheets(5000, 0)
      timesheets.value = result.data
    }

    // Load devices for filter dropdown
    const devicesResult = await bridgeService.getDevices()
    devices.value = devicesResult.data || []
  } catch (err) {
    console.error('Error loading timesheets:', err)
    error('Failed to load timesheets')
  } finally {
    loading.value = false
  }
}

const syncSelected = async () => {
  if (selectedIds.value.length === 0 || pushLoading.value) return

  // Skip excluded records — they're marked do-not-sync.
  const byId = new Map(timesheets.value.map(t => [t.id, t]))
  const syncableIds = selectedIds.value.filter(id => {
    const t = byId.get(id)
    return t && !t.excluded_from_sync && !isFullySynced(t)
  })
  if (syncableIds.length === 0) {
    error('All selected records are marked do-not-sync or already synced.')
    return
  }
  if (syncableIds.length < selectedIds.value.length) {
    success(`Skipping ${selectedIds.value.length - syncableIds.length} do-not-sync record(s).`)
  }

  pushLoading.value = true
  showProgressModal.value = true
  pushProgressMap.value = {}
  try {
    await bridgeService.startPushSyncForIds(syncableIds)
  } catch (err) {
    error(`Sync failed: ${err.message}`)
    pushLoading.value = false
    showProgressModal.value = false
  }
}

const handlePushProgress = (event) => {
  const progress = event.detail
  if (progress.type === 'pull') return
  const slot = progress.slot || 1
  pushProgressMap.value = {
    ...pushProgressMap.value,
    [slot]: {
      slot,
      label: progress.config_label || `Payroll ${slot}`,
      batch_current: progress.batch_current || 0,
      batch_total: progress.batch_total || 0,
      success: progress.success || 0,
      failed: progress.failed || 0,
      completed: !!progress.completed
    }
  }
}

const handleSyncCompleted = (event) => {
  const data = event.detail
  // Only push results drive this view's toast/modal; pull just refreshes the table.
  if (data.type === 'push') {
    pushLoading.value = false
    showProgressModal.value = false
    selectedIds.value = []
    showPushResultToasts(data.result, { success, error, info })
  }
  loadData()
}

const toggleExcluded = async (entry) => {
  const newValue = !entry.excluded_from_sync
  try {
    const result = await bridgeService.setTimesheetExcluded([entry.id], newValue)
    success(result.message)
    await loadData()
  } catch (err) {
    error(`Failed to update record: ${err.message}`)
  }
}

const bulkSetExcluded = async (excluded) => {
  // Only operate on non-synced rows.
  const byId = new Map(timesheets.value.map(t => [t.id, t]))
  const eligible = selectedIds.value.filter(id => {
    const t = byId.get(id)
    return t && !isFullySynced(t)
  })
  if (eligible.length === 0) {
    error('No eligible records selected (already-synced rows cannot be excluded).')
    return
  }
  try {
    const result = await bridgeService.setTimesheetExcluded(eligible, excluded)
    success(result.message)
    selectedIds.value = []
    await loadData()
  } catch (err) {
    error(`Failed to update records: ${err.message}`)
  }
}

const retrySync = async (timesheetId) => {
  try {
    await bridgeService.retryFailedTimesheet(timesheetId)
    success('Timesheet marked for retry. It will sync on next push.')
    await loadData()
  } catch (err) {
    error('Failed to retry timesheet sync')
  }
}

onMounted(async () => {
  // Initialize date filters
  initDateFilters()

  await bridgeService.whenReady()

  // Determine whether the second push destination is active (affects status logic)
  try {
    const cfg = await bridgeService.getApiConfig()
    config2Active.value = !!(cfg.data && cfg.data.push_enabled_2 && cfg.data.push_username_2)
  } catch (e) {
    config2Active.value = false
  }

  await loadData()

  // Single, named listeners so they can be removed on unmount (prevents
  // duplicate handlers — and duplicate toasts — accumulating across navigations).
  window.addEventListener('syncProgressUpdated', handlePushProgress)
  window.addEventListener('syncCompleted', handleSyncCompleted)
})

onUnmounted(() => {
  window.removeEventListener('syncProgressUpdated', handlePushProgress)
  window.removeEventListener('syncCompleted', handleSyncCompleted)
})
</script>
