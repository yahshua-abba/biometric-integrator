<template>
  <div class="p-6 space-y-6">
    <h1 class="text-3xl font-bold text-gray-900">Updates</h1>

    <!-- Version Info -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Version Info
      </h2>

      <div class="space-y-4">
        <div class="flex items-center gap-4">
          <span class="text-sm text-gray-600">Current version: <strong>{{ currentVersion }}</strong></span>
          <span v-if="latestVersion && updateAvailable" class="text-sm text-blue-600">
            Latest version: <strong>{{ latestVersion }}</strong>
          </span>
          <span v-if="latestVersion && !updateAvailable" class="inline-flex items-center gap-1 text-sm text-green-600">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            You're up to date
          </span>
        </div>

        <div class="flex items-center gap-3">
          <button
            @click="checkUpdates"
            :disabled="checkingUpdates"
            class="btn btn-secondary"
          >
            <span v-if="!checkingUpdates">Check for Updates</span>
            <span v-else>Checking...</span>
          </button>

          <button
            v-if="updateAvailable && updateDownloadUrl"
            @click="startDownload"
            :disabled="downloading"
            class="btn btn-primary"
          >
            <span v-if="!downloading">Download Update</span>
            <span v-else>Downloading...</span>
          </button>
        </div>

        <!-- Download progress -->
        <div v-if="downloading || downloadComplete" class="space-y-2">
          <div class="w-full bg-gray-200 rounded-full h-3">
            <div
              class="h-3 rounded-full transition-all duration-300"
              :class="downloadComplete ? 'bg-green-500' : 'bg-blue-500'"
              :style="{ width: downloadPercent + '%' }"
            ></div>
          </div>
          <p v-if="!downloadComplete && !downloadError" class="text-sm text-gray-600">
            {{ downloadedMb }} / {{ totalMb }} MB ({{ downloadPercent }}%)
          </p>
          <p v-if="downloadError" class="text-sm text-red-600">{{ downloadError }}</p>
        </div>

        <!-- Install prompt after download -->
        <div v-if="downloadComplete" class="bg-green-50 border border-green-200 rounded-lg p-4 space-y-3">
          <div class="flex items-center gap-2 text-green-700 font-medium">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Download complete
          </div>
          <p class="text-sm text-gray-600">
            Saved to: <span class="font-mono text-xs">{{ downloadSavePath }}</span>
          </p>
          <button
            @click="installUpdate"
            class="btn btn-primary flex items-center gap-2"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Install Update
          </button>
          <p class="text-xs text-gray-500">
            This will open the installer. The app will need to be restarted after installation.
          </p>
        </div>

        <p v-if="updateError" class="text-sm text-red-600">{{ updateError }}</p>
      </div>
    </div>

    <!-- All Releases -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <svg class="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        Release History
      </h2>

      <div v-if="loadingReleases" class="text-sm text-gray-500">Loading releases...</div>
      <div v-else-if="releasesError" class="text-sm text-red-600">{{ releasesError }}</div>
      <div v-else-if="releases.length === 0" class="text-sm text-gray-500">No releases found.</div>

      <div v-else class="space-y-2">
        <div
          v-for="(release, index) in releases"
          :key="release.tag_name"
          class="border border-gray-200 rounded-lg overflow-hidden"
        >
          <!-- Release header (clickable) -->
          <button
            @click="toggleRelease(index)"
            class="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition-colors"
          >
            <div class="flex items-center gap-3">
              <svg
                class="w-4 h-4 text-gray-400 transition-transform duration-200"
                :class="{ 'rotate-90': expandedReleases[index] }"
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
              <span class="font-medium text-gray-900">{{ release.name }}</span>
              <span
                v-if="release.tag_name.replace('v', '') === currentVersion"
                class="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full"
              >
                Current
              </span>
              <span
                v-else-if="index === 0 && updateAvailable"
                class="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full"
              >
                Latest
              </span>
            </div>
            <span class="text-xs text-gray-500">{{ formatDate(release.published_at) }}</span>
          </button>

          <!-- Release body (expandable) -->
          <div v-if="expandedReleases[index]" class="px-4 pb-4 border-t border-gray-100 bg-gray-50">
            <div
              v-if="release.body"
              class="prose prose-sm max-w-none text-gray-700 pt-3"
              v-html="renderMarkdown(release.body)"
            ></div>
            <p v-else class="text-sm text-gray-400 pt-3">No release notes.</p>
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

const { success, error, info } = useToast()

const currentVersion = ref('')
const latestVersion = ref('')
const updateAvailable = ref(false)
const updateDownloadUrl = ref('')
const checkingUpdates = ref(false)
const downloading = ref(false)
const downloadComplete = ref(false)
const downloadPercent = ref(0)
const downloadedMb = ref(0)
const totalMb = ref(0)
const downloadSavePath = ref('')
const downloadError = ref('')
const updateError = ref('')

// Releases list
const releases = ref([])
const expandedReleases = ref({})
const loadingReleases = ref(false)
const releasesError = ref('')

function toggleRelease(index) {
  expandedReleases.value[index] = !expandedReleases.value[index]
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

function renderMarkdown(text) {
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  html = html.replace(/^### (.+)$/gm, '<h3 class="text-base font-semibold mt-4 mb-1">$1</h3>')
  html = html.replace(/^## (.+)$/gm, '<h2 class="text-lg font-semibold mt-4 mb-2">$1</h2>')
  html = html.replace(/^# (.+)$/gm, '<h1 class="text-xl font-bold mt-4 mb-2">$1</h1>')

  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')

  html = html.replace(/`([^`]+)`/g, '<code class="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono">$1</code>')

  html = html.replace(/^[*-] (.+)$/gm, '<li class="ml-4 list-disc">$1</li>')
  html = html.replace(/((?:<li[^>]*>.*<\/li>\n?)+)/g, '<ul class="my-2">$1</ul>')

  html = html.replace(/\n\n/g, '</p><p class="my-2">')
  html = '<p class="my-2">' + html + '</p>'

  html = html.replace(/<p class="my-2"><\/p>/g, '')
  html = html.replace(/<p class="my-2">(<h[123])/g, '$1')
  html = html.replace(/(<\/h[123]>)<\/p>/g, '$1')
  html = html.replace(/<p class="my-2">(<ul)/g, '$1')
  html = html.replace(/(<\/ul>)<\/p>/g, '$1')

  return html
}

const checkUpdates = async () => {
  checkingUpdates.value = true
  updateError.value = ''
  downloadComplete.value = false
  downloadError.value = ''
  try {
    const result = await bridgeService.checkForUpdates()
    if (result.success && result.data) {
      latestVersion.value = result.data.latest_version
      updateAvailable.value = result.data.update_available
      updateDownloadUrl.value = result.data.download_url || ''
      if (!result.data.update_available) {
        info('You are running the latest version')
      } else {
        info(`Update available: v${result.data.latest_version}`)
      }
    }
  } catch (err) {
    updateError.value = err.message
    error(`Failed to check for updates: ${err.message}`)
  } finally {
    checkingUpdates.value = false
  }
}

const loadReleases = async () => {
  loadingReleases.value = true
  releasesError.value = ''
  try {
    const result = await bridgeService.getAllReleases()
    if (result.success && result.data) {
      releases.value = result.data
      // Auto-expand the first release
      if (result.data.length > 0) {
        expandedReleases.value[0] = true
      }
    }
  } catch (err) {
    releasesError.value = err.message
  } finally {
    loadingReleases.value = false
  }
}

const startDownload = async () => {
  downloading.value = true
  downloadComplete.value = false
  downloadPercent.value = 0
  downloadedMb.value = 0
  totalMb.value = 0
  downloadSavePath.value = ''
  downloadError.value = ''

  const saveDir = '~/Downloads'

  try {
    await bridgeService.downloadUpdate(saveDir)
  } catch (err) {
    downloading.value = false
    downloadError.value = err.message
    error(`Download failed: ${err.message}`)
  }
}

const installUpdate = async () => {
  try {
    const result = await bridgeService.openDownloadedUpdate(downloadSavePath.value)
    if (result.success) {
      info('Installer opened. Please follow the installation steps, then restart the app.')
    } else {
      error(`Could not open installer: ${result.error}`)
    }
  } catch (err) {
    error(`Could not open installer: ${err.message}`)
  }
}

const onUpdateDownloadProgress = (event) => {
  const data = event.detail
  if (data.error) {
    downloading.value = false
    downloadError.value = data.error
    error(`Download failed: ${data.error}`)
    return
  }
  downloadPercent.value = data.percent || 0
  downloadedMb.value = data.downloaded_mb || 0
  totalMb.value = data.total_mb || 0
  if (data.completed) {
    downloading.value = false
    downloadComplete.value = true
    downloadSavePath.value = data.save_path || ''
    success('Update downloaded successfully')
  }
}

onMounted(async () => {
  await bridgeService.whenReady()

  try {
    const appInfo = await bridgeService.getAppInfo()
    if (appInfo.data) {
      currentVersion.value = appInfo.data.version
    }
  } catch (err) {
    console.error('Error loading app info:', err)
  }

  window.addEventListener('updateDownloadProgress', onUpdateDownloadProgress)

  await checkUpdates()
  await loadReleases()
})

onUnmounted(() => {
  window.removeEventListener('updateDownloadProgress', onUpdateDownloadProgress)
})
</script>
