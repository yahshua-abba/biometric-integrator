<template>
  <div class="p-6 space-y-6">
    <h1 class="text-3xl font-bold text-gray-900">Dashboard</h1>

    <!-- Push Progress Modal -->
    <SyncProgressModal :show="showProgressModal" :progress="pushProgress" />

    <!-- Pull Date Range Modal -->
    <div v-if="showPullDateModal" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black bg-opacity-50" @click="closePullDateModal"></div>
      <div class="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <!-- Modal Header -->
        <div class="flex items-center justify-between p-4 border-b">
          <h3 class="text-lg font-semibold">Pull Date Range</h3>
          <button @click="closePullDateModal" class="text-gray-500 hover:text-gray-700">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Modal Body -->
        <div class="p-4 space-y-4">
          <!-- Date picker (shown when not loading) -->
          <div v-if="!pullLoading">
            <p class="text-sm text-gray-600 mb-4">Select the date range and device to pull attendance data.</p>

            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 mb-1">Device</label>
              <select v-model="selectedDeviceId" class="input w-full">
                <option :value="-1">All Enabled Devices</option>
                <option v-for="device in devices" :key="device.id" :value="device.id">
                  {{ device.name }} ({{ device.ip }})
                </option>
              </select>
            </div>

            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 mb-1">From</label>
              <input
                v-model="pullDateFrom"
                type="date"
                class="input w-full"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">To</label>
              <input
                v-model="pullDateTo"
                type="date"
                class="input w-full"
              />
            </div>
          </div>

          <!-- Progress indicator (shown when loading) -->
          <div v-else class="py-4">
            <div class="flex items-center justify-center mb-4">
              <svg class="animate-spin h-8 w-8 text-primary-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
            <p class="text-center text-gray-700 font-medium">
              {{ pullProgress.device_name ? `Pulling from ${pullProgress.device_name}` : 'Pulling from ZKTeco Device' }}
            </p>
            <p v-if="pullProgress.device_total > 1" class="text-center text-sm text-gray-500 mt-1">
              Device {{ pullProgress.device_index }} of {{ pullProgress.device_total }}
            </p>
            <p class="text-center text-sm text-gray-500 mt-2">
              {{ pullProgress.status || 'Connecting...' }}
            </p>
            <div class="mt-4 bg-gray-100 rounded-lg p-3 text-sm">
              <div class="flex justify-between text-gray-600">
                <span>Attendance records:</span>
                <span class="font-medium">{{ pullProgress.records_fetched || 0 }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="flex justify-end gap-2 p-4 border-t">
          <button @click="closePullDateModal" :disabled="pullLoading" class="btn btn-secondary">
            {{ pullLoading ? 'Please wait...' : 'Cancel' }}
          </button>
          <button v-if="!pullLoading" @click="executePullSync" :disabled="devices.length === 0 && selectedDeviceId === -1" class="btn btn-primary">
            Pull Data
          </button>
        </div>
      </div>
    </div>

    <!-- Sync Controls -->
    <div class="grid grid-cols-2 gap-6">
      <!-- Pull Sync Card -->
      <div class="card">
        <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
          <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Pull from ZKTeco Device
        </h2>
        <p class="text-gray-600 mb-4">
          Pull attendance data from ZKTeco device
        </p>
        <div v-if="config" class="text-sm text-gray-500 mb-4">
          Last pull: {{ formatDateTime(config.last_pull_at) || 'Never' }}
        </div>
        <button
          @click="handlePullSync"
          :disabled="pullLoading"
          class="btn btn-primary w-full"
        >
          <span v-if="!pullLoading">Pull Data Now</span>
          <span v-else class="flex items-center justify-center gap-2">
            <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Pulling...
          </span>
        </button>
      </div>

      <!-- Push Sync Card -->
      <div class="card">
        <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
          <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          Push to Cloud Payroll
        </h2>
        <p class="text-gray-600 mb-4">
          Sync timesheet data to cloud payroll system
        </p>
        <div v-if="config" class="text-sm text-gray-500 mb-4">
          Last push: {{ formatDateTime(config.last_push_at) || 'Never' }}
        </div>
        <button
          @click="handlePushSync"
          :disabled="pushLoading || stats.pending === 0"
          class="btn btn-success w-full"
        >
          <span v-if="!pushLoading">Push Data Now</span>
          <span v-else class="flex items-center justify-center gap-2">
            <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Pushing...
          </span>
        </button>
      </div>
    </div>

    <!-- Statistics -->
    <div class="grid grid-cols-4 gap-4">
      <div class="card">
        <div class="text-sm text-gray-600 mb-1">Total Records</div>
        <div class="text-3xl font-bold text-gray-900">{{ stats.total || 0 }}</div>
      </div>
      <div class="card">
        <div class="text-sm text-gray-600 mb-1">Synced</div>
        <div class="text-3xl font-bold text-green-600">{{ stats.synced || 0 }}</div>
      </div>
      <div class="card">
        <div class="text-sm text-gray-600 mb-1">Pending</div>
        <div class="text-3xl font-bold text-yellow-600">{{ stats.pending || 0 }}</div>
      </div>
      <div class="card">
        <div class="text-sm text-gray-600 mb-1">Errors</div>
        <div class="text-3xl font-bold text-red-600">{{ stats.errors || 0 }}</div>
      </div>
    </div>

    <!-- Recent Sync Activity -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4">Recent Sync Activity</h2>
      <div v-if="loadingLogs" class="text-center py-8 text-gray-500">
        Loading...
      </div>
      <div v-else-if="recentLogs.length === 0" class="text-center py-8 text-gray-500">
        No sync activity yet
      </div>
      <div v-else class="space-y-2">
        <div
          v-for="log in recentLogs"
          :key="log.id"
          class="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
        >
          <div class="flex items-center gap-3">
            <span
              :class="[
                'badge',
                log.sync_type === 'pull' ? 'badge-info' : 'badge-success'
              ]"
            >
              {{ log.sync_type.toUpperCase() }}
            </span>
            <span class="text-sm text-gray-700">
              {{ log.records_success || 0 }} records processed
            </span>
            <span
              v-if="log.status === 'error'"
              class="badge badge-error"
            >
              Error
            </span>
          </div>
          <div class="text-sm text-gray-500">
            {{ formatDateTime(log.started_at) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import bridgeService from '../services/bridge'
import { useToast } from '../composables/useToast'
import SyncProgressModal from './SyncProgressModal.vue'

const { success, error } = useToast()

const stats = ref({
  total: 0,
  synced: 0,
  pending: 0,
  errors: 0
})

const config = ref(null)
const recentLogs = ref([])
const pullLoading = ref(false)
const pushLoading = ref(false)
const loadingLogs = ref(false)

// Push progress modal state
const showProgressModal = ref(false)
const pushProgress = ref({
  batch_current: 0,
  batch_total: 0,
  batch_size: 0,
  success: 0,
  failed: 0
})

// Pull date picker modal state
const showPullDateModal = ref(false)
const pullDateFrom = ref('')
const pullDateTo = ref('')
const selectedDeviceId = ref(-1)  // -1 means all devices
const devices = ref([])

// Pull progress state
const pullProgress = ref({
  page: 0,
  records_fetched: 0,
  records_processed: 0,
  status: '',
  device_name: '',
  device_index: 0,
  device_total: 0
})

// Helper to get date in YYYY-MM-DD format
const getDateString = (date) => {
  return date.toISOString().split('T')[0]
}

// Initialize default dates (yesterday and today)
const initPullDates = () => {
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  pullDateFrom.value = getDateString(yesterday)
  pullDateTo.value = getDateString(today)
}

const loadData = async () => {
  try {
    // Load stats
    const statsResult = await bridgeService.getTimesheetStats()
    stats.value = statsResult.data

    // Load config
    const configResult = await bridgeService.getApiConfig()
    config.value = configResult.data

    // Load devices
    const devicesResult = await bridgeService.getDevices()
    devices.value = (devicesResult.data || []).filter(d => d.enabled)

    // Load recent logs
    loadingLogs.value = true
    const logsResult = await bridgeService.getSyncLogs()
    recentLogs.value = logsResult.data.slice(0, 10)
  } catch (err) {
    console.error('Error loading dashboard data:', err)
    error('Failed to load dashboard data')
  } finally {
    loadingLogs.value = false
  }
}

const handlePullSync = () => {
  // Open date picker modal with default dates
  initPullDates()
  selectedDeviceId.value = -1  // Default to all devices
  showPullDateModal.value = true
}

const closePullDateModal = () => {
  showPullDateModal.value = false
}

const executePullSync = async () => {
  pullLoading.value = true
  // Reset progress
  pullProgress.value = {
    page: 0,
    records_fetched: 0,
    records_processed: 0,
    status: 'starting',
    device_name: '',
    device_index: 0,
    device_total: 0
  }
  try {
    // This returns immediately - actual result comes via syncCompleted signal
    // Pass selectedDeviceId (-1 means all devices)
    await bridgeService.startPullSync(pullDateFrom.value, pullDateTo.value, selectedDeviceId.value)
  } catch (err) {
    error(`Pull sync failed: ${err.message}`)
    pullLoading.value = false
    showPullDateModal.value = false
  }
}

const handlePushSync = async () => {
  pushLoading.value = true
  showProgressModal.value = true
  // Reset progress
  pushProgress.value = {
    batch_current: 0,
    batch_total: 0,
    batch_size: 0,
    success: 0,
    failed: 0
  }
  try {
    // This returns immediately - actual result comes via syncCompleted signal
    await bridgeService.startPushSync()
  } catch (err) {
    error(`Push sync failed: ${err.message}`)
    pushLoading.value = false
    showProgressModal.value = false
  }
}

// Handle progress updates from backend
const handleProgressUpdate = (event) => {
  const progress = event.detail

  if (progress.type === 'pull') {
    // Handle pull progress
    pullProgress.value = {
      page: progress.page || 0,
      records_fetched: progress.records_fetched || 0,
      records_processed: progress.records_processed || 0,
      records_success: progress.records_success || 0,
      status: progress.status || progress.message || '',
      device_name: progress.device_name || '',
      device_index: progress.device_index || 0,
      device_total: progress.device_total || 0
    }
  } else {
    // Handle push progress
    pushProgress.value = {
      batch_current: progress.batch_current || 0,
      batch_total: progress.batch_total || 0,
      batch_size: progress.batch_size || 0,
      success: progress.success || 0,
      failed: progress.failed || 0
    }
  }
}

const formatDateTime = (dateTime) => {
  if (!dateTime) return 'Never'
  const date = new Date(dateTime)
  return date.toLocaleString()
}

// Listen for sync events
onMounted(async () => {
  await bridgeService.whenReady()
  await loadData()

  // Listen for sync progress updates
  window.addEventListener('syncProgressUpdated', handleProgressUpdate)

  // Listen for sync completion
  window.addEventListener('syncCompleted', async (event) => {
    const data = event.detail

    // Handle pull completion
    if (data.type === 'pull') {
      pullLoading.value = false
      showPullDateModal.value = false

      if (data.result.success) {
        success(data.result.message)
      } else {
        error(data.result.message || data.result.error || 'Pull sync failed')
      }
    }

    // Handle push completion
    if (data.type === 'push') {
      pushLoading.value = false
      showProgressModal.value = false

      if (data.result.success) {
        success(data.result.message)
      } else {
        error(data.result.message || data.result.error || 'Push sync failed')
      }
    }

    await loadData()
  })
})

onUnmounted(() => {
  window.removeEventListener('syncProgressUpdated', handleProgressUpdate)
})
</script>
