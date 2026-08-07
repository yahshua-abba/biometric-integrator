<template>
  <div class="p-6 space-y-6">
    <h1 class="text-3xl font-bold text-gray-900">Configuration</h1>

    <!-- Push Configuration (Payroll API) - First -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
        </svg>
        Push Configuration 1 (Primary Payroll)
      </h2>

      <div class="space-y-4">
        <!-- API URL -->
        <div>
          <label class="label">API URL</label>
          <input
            v-model="form.push_url"
            @blur="persistUrl(1)"
            type="url"
            placeholder="https://yahshuapayroll.com/api"
            class="input"
          />
          <p class="text-sm text-gray-500 mt-1">
            Payroll API endpoint. Change only if directed by your administrator.
          </p>
        </div>

        <!-- Logged In State -->
        <div v-if="pushLoggedIn">
          <div class="bg-green-50 border border-green-200 rounded-lg p-4">
            <div class="flex items-center gap-2 mb-2">
              <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span class="font-semibold text-green-800">Connected to Payroll System</span>
            </div>
            <p class="text-green-800">
              Logged in as <strong>{{ pushUserLogged }}</strong><br/>
              <span class="text-sm">({{ form.push_username }})</span>
            </p>
            <p class="text-sm text-green-600 mt-2">
              Last login: {{ pushTokenCreatedAt }}
            </p>
          </div>

          <div class="mt-4">
            <label class="label">Sync Interval (minutes)</label>
            <input
              v-model.number="form.push_interval_minutes"
              type="number"
              min="1"
              max="1440"
              class="input"
            />
            <p class="text-sm text-gray-500 mt-1">
              How often to automatically push data (0 to disable automatic sync)
            </p>
          </div>

          <button
            @click="logoutPush"
            :disabled="loggingOut"
            class="btn btn-secondary mt-4"
          >
            <span v-if="!loggingOut">Logout</span>
            <span v-else>Logging out...</span>
          </button>
        </div>

        <!-- Logged Out State -->
        <div v-else>
          <div class="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4">
            <p class="text-sm text-gray-600">
              <strong>Payroll API</strong><br/>
              Login to connect and sync timesheet data.
            </p>
          </div>

          <div>
            <label class="label">Email / Username</label>
            <input
              v-model="form.push_username"
              type="email"
              placeholder="timekeeping@company.com"
              class="input"
            />
          </div>

          <div>
            <label class="label">Password</label>
            <input
              v-model="form.push_password"
              type="password"
              placeholder="Enter password"
              class="input"
            />
          </div>

          <button
            @click="loginPush"
            :disabled="!form.push_username || !form.push_password || loggingIn"
            class="btn btn-primary mt-4"
          >
            <span v-if="!loggingIn">Login</span>
            <span v-else>Logging in...</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Push Configuration 2 (Secondary Payroll) - optional -->
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-xl font-semibold flex items-center gap-2">
          <svg class="w-6 h-6 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          Push Configuration 2 (Secondary Payroll)
        </h2>
        <!-- Enable toggle -->
        <label class="inline-flex items-center cursor-pointer">
          <span class="mr-2 text-sm text-gray-600">{{ config2Enabled ? 'Enabled' : 'Disabled' }}</span>
          <input
            type="checkbox"
            class="sr-only peer"
            :checked="config2Enabled"
            :disabled="togglingConfig2"
            @change.prevent="handleToggleConfig2"
          />
          <div class="relative w-11 h-6 bg-gray-200 rounded-full peer peer-checked:bg-emerald-500 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
        </label>
      </div>

      <p class="text-sm text-gray-500 mb-4">
        Send a copy of every timesheet log to a second payroll system at the same time.
        Each destination tracks its own sync status independently.
      </p>

      <div v-if="config2Enabled" class="space-y-4">
        <!-- API URL -->
        <div>
          <label class="label">API URL</label>
          <input
            v-model="form.push_url_2"
            @blur="persistUrl(2)"
            type="url"
            placeholder="https://yahshuapayroll.com/api"
            class="input"
          />
          <p class="text-sm text-gray-500 mt-1">
            Second payroll API endpoint.
          </p>
        </div>

        <!-- Logged In State -->
        <div v-if="pushLoggedIn2">
          <div class="bg-green-50 border border-green-200 rounded-lg p-4">
            <div class="flex items-center gap-2 mb-2">
              <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span class="font-semibold text-green-800">Connected to Second Payroll System</span>
            </div>
            <p class="text-green-800">
              Logged in as <strong>{{ pushUserLogged2 }}</strong><br/>
              <span class="text-sm">({{ form.push_username_2 }})</span>
            </p>
            <p class="text-sm text-green-600 mt-2">
              Last login: {{ pushTokenCreatedAt2 }}
            </p>
          </div>

          <button
            @click="logoutPush2"
            :disabled="loggingOut2"
            class="btn btn-secondary mt-4"
          >
            <span v-if="!loggingOut2">Logout</span>
            <span v-else>Logging out...</span>
          </button>
        </div>

        <!-- Logged Out State -->
        <div v-else>
          <div class="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4">
            <p class="text-sm text-gray-600">
              <strong>Second Payroll API</strong><br/>
              Login to connect and sync timesheet data to this destination.
            </p>
          </div>

          <div>
            <label class="label">Email / Username</label>
            <input
              v-model="form.push_username_2"
              type="email"
              placeholder="timekeeping@company.com"
              class="input"
            />
          </div>

          <div>
            <label class="label">Password</label>
            <input
              v-model="form.push_password_2"
              type="password"
              placeholder="Enter password"
              class="input"
            />
          </div>

          <button
            @click="loginPush2"
            :disabled="!form.push_username_2 || !form.push_password_2 || loggingIn2"
            class="btn btn-primary mt-4"
          >
            <span v-if="!loggingIn2">Login</span>
            <span v-else>Logging in...</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Enable Config 2 history choice modal -->
    <div v-if="showEnable2Modal" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black bg-opacity-50" @click="showEnable2Modal = false"></div>
      <div class="relative bg-white rounded-lg shadow-xl p-6 w-full max-w-md mx-4">
        <h3 class="text-lg font-semibold mb-2">Enable second destination</h3>
        <p class="text-sm text-gray-600 mb-4">
          What should happen to timesheet logs that already exist in this app?
        </p>
        <div class="space-y-3">
          <button
            @click="confirmEnableConfig2(false)"
            :disabled="togglingConfig2"
            class="w-full text-left border rounded-lg p-3 hover:bg-gray-50"
          >
            <div class="font-medium text-gray-900">Only send new logs from now on <span class="text-emerald-600">(Recommended)</span></div>
            <div class="text-sm text-gray-500">Existing records are marked as already handled for this destination.</div>
          </button>
          <button
            @click="confirmEnableConfig2(true)"
            :disabled="togglingConfig2"
            class="w-full text-left border rounded-lg p-3 hover:bg-gray-50"
          >
            <div class="font-medium text-gray-900">Send all existing history too</div>
            <div class="text-sm text-gray-500">Every stored log not yet on this destination will be pushed on the next sync.</div>
          </button>
        </div>
        <div class="mt-4 text-right">
          <button @click="showEnable2Modal = false" :disabled="togglingConfig2" class="btn btn-secondary">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Device Configuration (ZKTeco) - Second -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Device Configuration (ZKTeco)
      </h2>

      <div class="space-y-4">
        <div>
          <label class="label">Pull Interval (minutes)</label>
          <input
            v-model.number="form.pull_interval_minutes"
            type="number"
            min="0"
            max="1440"
            class="input w-32"
          />
          <p class="text-sm text-gray-500 mt-1">
            How often to automatically pull data from all enabled devices (0 to disable automatic sync)
          </p>
        </div>

        <!-- Device List -->
        <div class="border rounded-lg overflow-hidden">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">IP Address</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Port</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Branch ID</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Pull</th>
                <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-if="devices.length === 0">
                <td colspan="7" class="px-4 py-8 text-center text-gray-500">
                  No devices configured. Click "Add Device" to get started.
                </td>
              </tr>
              <tr v-for="device in devices" :key="device.id" :class="{ 'bg-gray-50': !device.enabled }">
                <td class="px-4 py-3 whitespace-nowrap">
                  <span :class="{ 'text-gray-400': !device.enabled }">{{ device.name }}</span>
                </td>
                <td class="px-4 py-3 whitespace-nowrap font-mono text-sm">
                  <span :class="{ 'text-gray-400': !device.enabled }">{{ device.ip }}</span>
                </td>
                <td class="px-4 py-3 whitespace-nowrap font-mono text-sm">
                  <span :class="{ 'text-gray-400': !device.enabled }">{{ device.port }}</span>
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-sm">
                  <span :class="{ 'text-gray-400': !device.enabled }">{{ device.branch_id || '-' }}</span>
                </td>
                <td class="px-4 py-3 whitespace-nowrap">
                  <span v-if="device.enabled" class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Enabled
                  </span>
                  <span v-else class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                    Disabled
                  </span>
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                  {{ device.last_pull_at ? formatDateTime(device.last_pull_at) : 'Never' }}
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-right text-sm">
                  <button
                    @click="testDevice(device)"
                    :disabled="testingDeviceId === device.id"
                    class="text-blue-600 hover:text-blue-800 mr-3"
                    title="Test Connection"
                  >
                    <span v-if="testingDeviceId === device.id">Testing...</span>
                    <span v-else>Test</span>
                  </button>
                  <button
                    @click="editDevice(device)"
                    class="text-gray-600 hover:text-gray-800 mr-3"
                    title="Edit"
                  >
                    Edit
                  </button>
                  <button
                    @click="confirmDeleteDevice(device)"
                    class="text-red-600 hover:text-red-800"
                    title="Delete"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <button @click="openAddDeviceModal" class="btn btn-primary">
          + Add Device
        </button>
      </div>
    </div>

    <!-- Add/Edit Device Modal -->
    <div v-if="showDeviceModal" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black bg-opacity-50" @click="closeDeviceModal"></div>
      <div class="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div class="flex items-center justify-between p-4 border-b">
          <h3 class="text-lg font-semibold">{{ editingDevice ? 'Edit Device' : 'Add Device' }}</h3>
          <button @click="closeDeviceModal" class="text-gray-500 hover:text-gray-700">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="p-4 space-y-4">
          <div>
            <label class="label">Device Name</label>
            <input
              v-model="deviceForm.name"
              type="text"
              placeholder="e.g., Main Entrance, Building A"
              class="input"
            />
          </div>
          <div>
            <label class="label">IP Address</label>
            <input
              v-model="deviceForm.ip"
              type="text"
              placeholder="192.168.1.100"
              class="input"
            />
          </div>
          <div>
            <label class="label">Port</label>
            <input
              v-model.number="deviceForm.port"
              type="number"
              placeholder="4370"
              class="input"
            />
          </div>
          <div>
            <label class="label">Comm Key (Password)</label>
            <input
              v-model.number="deviceForm.comm_key"
              type="number"
              placeholder="0"
              class="input"
            />
            <p class="text-xs text-gray-500 mt-1">Leave as 0 if device has no password</p>
          </div>
          <div>
            <label class="label">Branch ID</label>
            <input
              v-model="deviceForm.branch_id"
              type="text"
              placeholder="e.g., BRANCH001"
              class="input"
            />
            <p class="text-xs text-gray-500 mt-1">Branch identifier for Payroll system (optional)</p>
          </div>
          <div v-if="editingDevice" class="flex items-center gap-2">
            <input
              type="checkbox"
              id="deviceEnabled"
              v-model="deviceForm.enabled"
              class="h-4 w-4 text-primary-600 rounded"
            />
            <label for="deviceEnabled" class="text-sm text-gray-700">Enabled</label>
          </div>
        </div>
        <div class="flex justify-end gap-2 p-4 border-t">
          <button @click="closeDeviceModal" class="btn btn-secondary">Cancel</button>
          <button
            @click="saveDevice"
            :disabled="!deviceForm.name || !deviceForm.ip || savingDevice"
            class="btn btn-primary"
          >
            <span v-if="!savingDevice">{{ editingDevice ? 'Save Changes' : 'Add Device' }}</span>
            <span v-else>Saving...</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteModal" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black bg-opacity-50" @click="closeDeleteModal"></div>
      <div class="relative bg-white rounded-lg shadow-xl w-full max-w-sm mx-4">
        <div class="p-6">
          <h3 class="text-lg font-semibold mb-2">Delete Device</h3>
          <p class="text-gray-600 mb-4">
            Are you sure you want to delete "{{ deviceToDelete?.name }}"? This action cannot be undone.
          </p>
          <div class="flex justify-end gap-2">
            <button @click="closeDeleteModal" class="btn btn-secondary">Cancel</button>
            <button
              @click="deleteDevice"
              :disabled="deletingDevice"
              class="btn bg-red-600 text-white hover:bg-red-700"
            >
              <span v-if="!deletingDevice">Delete</span>
              <span v-else>Deleting...</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- System Logs Section -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <svg class="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        System Logs
      </h2>
      <p class="text-sm text-gray-500 mb-4">View application logs for debugging and troubleshooting.</p>
      <button @click="openLogModal" class="btn btn-secondary">
        View System Logs
      </button>
    </div>

    <!-- Log Modal -->
    <div v-if="showLogModal" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black bg-opacity-50" @click="closeLogModal"></div>
      <div class="relative bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[80vh] flex flex-col">
        <!-- Modal Header -->
        <div class="flex items-center justify-between p-4 border-b">
          <h3 class="text-lg font-semibold">System Logs</h3>
          <button @click="closeLogModal" class="text-gray-500 hover:text-gray-700">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Modal Body -->
        <div class="p-4 flex-1 overflow-hidden flex flex-col">
          <!-- Log File Selector -->
          <div class="flex items-center gap-4 mb-4">
            <select v-model="selectedLogFile" @change="loadLogContent" class="input w-64">
              <option value="">Select a log file...</option>
              <option v-for="file in logFiles" :key="file.filename" :value="file.filename">
                {{ formatLogDate(file.date) }} ({{ formatFileSize(file.size) }})
              </option>
            </select>
            <button @click="loadLogContent" :disabled="!selectedLogFile || loadingLog" class="btn btn-secondary">
              <span v-if="!loadingLog">Refresh</span>
              <span v-else>Loading...</span>
            </button>
            <button @click="downloadLog" :disabled="!selectedLogFile || !logContent" class="btn btn-secondary">
              Download
            </button>
            <span v-if="logInfo" class="text-sm text-gray-500">
              Showing {{ logInfo.showing_lines }} of {{ logInfo.total_lines }} lines
            </span>
          </div>

          <!-- Log Content -->
          <div class="flex-1 overflow-auto bg-gray-900 rounded-lg p-4">
            <pre v-if="logContent" class="text-green-400 text-xs font-mono whitespace-pre-wrap">{{ logContent }}</pre>
            <p v-else class="text-gray-500 text-center py-8">Select a log file to view its contents</p>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="flex justify-end p-4 border-t">
          <button @click="closeLogModal" class="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import bridgeService from '../services/bridge'
import { useToast } from '../composables/useToast'

const { success, error, info } = useToast()

const DEFAULT_PUSH_URL = 'https://yahshuapayroll.com/api'

const form = ref({
  pull_interval_minutes: 30,
  push_url: DEFAULT_PUSH_URL,
  push_username: '',
  push_password: '',
  push_interval_minutes: 15,
  // Second push destination (Config 2)
  push_url_2: DEFAULT_PUSH_URL,
  push_username_2: '',
  push_password_2: ''
})

const saving = ref(false)
const configLoaded = ref(false)  // Prevent auto-save on initial load

// Debounce helper
let saveTimeout = null
const debouncedSave = () => {
  if (!configLoaded.value) return  // Don't save during initial load

  if (saveTimeout) clearTimeout(saveTimeout)
  saveTimeout = setTimeout(async () => {
    await saveConfig()
  }, 500)
}

// Auto-save only the standalone sync intervals. The API URLs are intentionally
// NOT auto-saved — they are persisted as part of the Login action so that merely
// editing the connection form does not announce "Settings saved" before the user
// has logged in.
watch(() => form.value.pull_interval_minutes, debouncedSave)
watch(() => form.value.push_interval_minutes, debouncedSave)

// Payroll login state (Config 1)
const pushLoggedIn = ref(false)
const pushUserLogged = ref('')
const pushTokenCreatedAt = ref('')
const loggingIn = ref(false)
const loggingOut = ref(false)

// Second payroll destination (Config 2) state
const config2Enabled = ref(false)
const togglingConfig2 = ref(false)
const showEnable2Modal = ref(false)
const pushLoggedIn2 = ref(false)
const pushUserLogged2 = ref('')
const pushTokenCreatedAt2 = ref('')
const loggingIn2 = ref(false)
const loggingOut2 = ref(false)

// Device management state
const devices = ref([])
const showDeviceModal = ref(false)
const showDeleteModal = ref(false)
const editingDevice = ref(null)
const deviceToDelete = ref(null)
const savingDevice = ref(false)
const deletingDevice = ref(false)
const testingDeviceId = ref(null)
const deviceForm = ref({
  name: '',
  ip: '',
  port: 4370,
  comm_key: 0,
  branch_id: '',
  enabled: true
})

// System logs state
const showLogModal = ref(false)
const logFiles = ref([])
const selectedLogFile = ref('')
const logContent = ref('')
const logInfo = ref(null)
const loadingLog = ref(false)

const loadConfig = async () => {
  configLoaded.value = false  // Prevent auto-save during load
  try {
    const result = await bridgeService.getApiConfig()
    if (result.data) {
      form.value = {
        pull_interval_minutes: result.data.pull_interval_minutes || 30,
        push_url: result.data.push_url || DEFAULT_PUSH_URL,
        push_username: result.data.push_username || '',
        push_password: '',  // Never prefill password
        push_interval_minutes: result.data.push_interval_minutes || 15,
        push_url_2: result.data.push_url_2 || DEFAULT_PUSH_URL,
        push_username_2: result.data.push_username_2 || '',
        push_password_2: ''  // Never prefill password
      }

      // Set Payroll login state (Config 1)
      pushLoggedIn.value = result.data.push_token_exists || false
      pushUserLogged.value = result.data.push_user_logged || ''
      pushTokenCreatedAt.value = result.data.push_token_created_at || ''

      // Set second destination state (Config 2)
      config2Enabled.value = result.data.push_enabled_2 || false
      pushLoggedIn2.value = result.data.push_token_2_exists || false
      pushUserLogged2.value = result.data.push_user_logged_2 || ''
      pushTokenCreatedAt2.value = result.data.push_token_created_at_2 || ''
    }

    // Load devices
    await loadDevices()
  } catch (err) {
    console.error('Error loading config:', err)
    error('Failed to load configuration')
  } finally {
    // Allow auto-save after config is loaded
    setTimeout(() => {
      configLoaded.value = true
    }, 100)
  }
}

const loadDevices = async () => {
  try {
    const result = await bridgeService.getDevices()
    if (result.success) {
      devices.value = result.data || []
    }
  } catch (err) {
    console.error('Error loading devices:', err)
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    await bridgeService.updateApiConfig(form.value)
    info('Settings saved')
  } catch (err) {
    console.error('Error saving config:', err)
    error('Failed to save settings')
  } finally {
    saving.value = false
  }
}

// Device management functions
const openAddDeviceModal = () => {
  editingDevice.value = null
  deviceForm.value = {
    name: '',
    ip: '',
    port: 4370,
    comm_key: 0,
    branch_id: '',
    enabled: true
  }
  showDeviceModal.value = true
}

const editDevice = (device) => {
  editingDevice.value = device
  deviceForm.value = {
    name: device.name,
    ip: device.ip,
    port: device.port,
    comm_key: device.comm_key || 0,
    branch_id: device.branch_id || '',
    enabled: !!device.enabled
  }
  showDeviceModal.value = true
}

const closeDeviceModal = () => {
  showDeviceModal.value = false
  editingDevice.value = null
}

const saveDevice = async () => {
  savingDevice.value = true
  try {
    if (editingDevice.value) {
      // Update existing device
      await bridgeService.updateDevice(
        editingDevice.value.id,
        deviceForm.value.name,
        deviceForm.value.ip,
        deviceForm.value.port,
        deviceForm.value.comm_key || 0,
        deviceForm.value.branch_id || '',
        deviceForm.value.enabled
      )
      success('Device updated successfully')
    } else {
      // Add new device
      await bridgeService.addDevice(
        deviceForm.value.name,
        deviceForm.value.ip,
        deviceForm.value.port,
        deviceForm.value.comm_key || 0,
        deviceForm.value.branch_id || ''
      )
      success('Device added successfully')
    }
    closeDeviceModal()
    await loadDevices()
  } catch (err) {
    error(`Failed to save device: ${err.message}`)
  } finally {
    savingDevice.value = false
  }
}

const confirmDeleteDevice = (device) => {
  deviceToDelete.value = device
  showDeleteModal.value = true
}

const closeDeleteModal = () => {
  showDeleteModal.value = false
  deviceToDelete.value = null
}

const deleteDevice = async () => {
  if (!deviceToDelete.value) return

  deletingDevice.value = true
  try {
    await bridgeService.deleteDevice(deviceToDelete.value.id)
    success('Device deleted successfully')
    closeDeleteModal()
    await loadDevices()
  } catch (err) {
    error(`Failed to delete device: ${err.message}`)
  } finally {
    deletingDevice.value = false
  }
}

const testDevice = async (device) => {
  testingDeviceId.value = device.id
  try {
    const result = await bridgeService.testDeviceConnection(device.id)
    if (result.success) {
      success(result.message)
    } else {
      error(result.error || 'Connection test failed')
    }
  } catch (err) {
    error(`Connection test failed: ${err.message}`)
  } finally {
    testingDeviceId.value = null
  }
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return ''
  try {
    const date = new Date(dateStr)
    return date.toLocaleString()
  } catch {
    return dateStr
  }
}

// Silently persist just the API URL (no toast). Used on blur so an edited URL is
// kept without implying that login/credentials were saved.
const persistUrl = async (slot) => {
  if (!configLoaded.value) return
  const isSecond = slot === 2
  const url = isSecond ? form.value.push_url_2 : form.value.push_url
  if (!url) return
  try {
    await bridgeService.updateApiConfig(isSecond ? { push_url_2: url } : { push_url: url })
  } catch (err) {
    console.error('Failed to persist API URL:', err)
  }
}

const doLoginPush = async (slot) => {
  const isSecond = slot === 2
  const username = isSecond ? form.value.push_username_2 : form.value.push_username
  const password = isSecond ? form.value.push_password_2 : form.value.push_password
  const url = isSecond ? form.value.push_url_2 : form.value.push_url
  const loadingRef = isSecond ? loggingIn2 : loggingIn
  loadingRef.value = true
  try {
    // Persist the API URL first (silently) so authentication uses the entered endpoint
    if (url) {
      await bridgeService.updateApiConfig(isSecond ? { push_url_2: url } : { push_url: url })
    }
    const result = await bridgeService.loginPush(username, password, slot)
    if (isSecond) {
      pushLoggedIn2.value = true
      pushUserLogged2.value = result.user_logged
      pushTokenCreatedAt2.value = new Date().toLocaleString()
      form.value.push_password_2 = ''
    } else {
      pushLoggedIn.value = true
      pushUserLogged.value = result.user_logged
      pushTokenCreatedAt.value = new Date().toLocaleString()
      form.value.push_password = ''
    }
    success(result.message)
  } catch (err) {
    error(`Login failed: ${err.message}`)
  } finally {
    loadingRef.value = false
  }
}

const doLogoutPush = async (slot) => {
  const isSecond = slot === 2
  const loadingRef = isSecond ? loggingOut2 : loggingOut
  loadingRef.value = true
  try {
    await bridgeService.logoutPush(slot)
    if (isSecond) {
      pushLoggedIn2.value = false
      pushUserLogged2.value = ''
      pushTokenCreatedAt2.value = ''
    } else {
      pushLoggedIn.value = false
      pushUserLogged.value = ''
      pushTokenCreatedAt.value = ''
    }
    success('Logged out successfully')
  } catch (err) {
    error(`Logout failed: ${err.message}`)
  } finally {
    loadingRef.value = false
  }
}

const loginPush = () => doLoginPush(1)
const logoutPush = () => doLogoutPush(1)
const loginPush2 = () => doLoginPush(2)
const logoutPush2 = () => doLogoutPush(2)

// Enable/disable the second push destination
const handleToggleConfig2 = async () => {
  if (config2Enabled.value) {
    // Currently enabled -> disable
    togglingConfig2.value = true
    try {
      await bridgeService.setPushConfig2Enabled(false, false)
      config2Enabled.value = false
      info('Second destination disabled')
    } catch (err) {
      error(`Failed to disable: ${err.message}`)
    } finally {
      togglingConfig2.value = false
    }
  } else {
    // Ask how to treat existing history before enabling
    showEnable2Modal.value = true
  }
}

const confirmEnableConfig2 = async (pushHistory) => {
  togglingConfig2.value = true
  try {
    const result = await bridgeService.setPushConfig2Enabled(true, pushHistory)
    config2Enabled.value = true
    showEnable2Modal.value = false
    success(result.message || 'Second destination enabled')
  } catch (err) {
    error(`Failed to enable: ${err.message}`)
  } finally {
    togglingConfig2.value = false
  }
}

// System log functions
const openLogModal = async () => {
  showLogModal.value = true
  selectedLogFile.value = ''
  logContent.value = ''
  logInfo.value = null

  try {
    const result = await bridgeService.getSystemLogFiles()
    if (result.success) {
      logFiles.value = result.data
      // Auto-select first (most recent) file
      if (logFiles.value.length > 0) {
        selectedLogFile.value = logFiles.value[0].filename
        await loadLogContent()
      }
    }
  } catch (err) {
    console.error('Error loading log files:', err)
    error('Failed to load log files')
  }
}

const closeLogModal = () => {
  showLogModal.value = false
}

const loadLogContent = async () => {
  if (!selectedLogFile.value) return

  loadingLog.value = true
  try {
    const result = await bridgeService.getSystemLogContent(selectedLogFile.value)
    if (result.success) {
      logContent.value = result.data.content
      logInfo.value = result.data
    } else {
      error(result.error || 'Failed to load log content')
    }
  } catch (err) {
    console.error('Error loading log content:', err)
    error('Failed to load log content')
  } finally {
    loadingLog.value = false
  }
}

const formatLogDate = (dateStr) => {
  // Convert YYYYMMDD to readable format
  if (!dateStr || dateStr.length !== 8) return dateStr
  const year = dateStr.substring(0, 4)
  const month = dateStr.substring(4, 6)
  const day = dateStr.substring(6, 8)
  return `${year}-${month}-${day}`
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const downloadLog = () => {
  if (!logContent.value || !selectedLogFile.value) return

  const blob = new Blob([logContent.value], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = selectedLogFile.value
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  await bridgeService.whenReady()
  await loadConfig()
})
</script>
