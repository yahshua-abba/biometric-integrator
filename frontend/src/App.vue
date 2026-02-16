<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Sidebar -->
    <div class="fixed inset-y-0 left-0 w-64 bg-white shadow-lg">
      <div class="flex flex-col h-full">
        <!-- Logo/Title -->
        <div class="p-6 bg-primary-600 text-white">
          <h1 class="text-xl font-bold">Biometrics</h1>
          <p class="text-sm text-primary-100">Integration Sync Tool</p>
        </div>

        <!-- Navigation -->
        <nav class="flex-1 p-4 space-y-2">
          <button
            v-for="view in views"
            :key="view.id"
            @click="currentView = view.id"
            :class="[
              'w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors',
              currentView === view.id
                ? 'bg-primary-50 text-primary-700 font-medium'
                : 'text-gray-700 hover:bg-gray-100'
            ]"
          >
            <component :is="view.icon" class="w-5 h-5" />
            <span>{{ view.label }}</span>
          </button>
        </nav>

        <!-- App Info -->
        <div class="p-4 border-t text-xs text-gray-500">
          <div>Version {{ appVersion }}</div>
          <div>© {{ new Date().getFullYear() }} The ABBA Initiative, OPC</div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="ml-64">
      <component :is="currentViewComponent" />
    </div>

    <!-- Toast Notifications -->
    <ToastNotification />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue'
import DashboardView from './components/DashboardView.vue'
import TimesheetView from './components/TimesheetView.vue'
import ConfigView from './components/ConfigView.vue'
import LogsView from './components/LogsView.vue'
import UpdatesView from './components/UpdatesView.vue'
import HelpView from './components/HelpView.vue'
import ToastNotification from './components/ToastNotification.vue'
import bridgeService from './services/bridge'

const currentView = ref('dashboard')
const appVersion = ref('1.0.15')

// Icon components (SVG)
const DashboardIcon = () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
  h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' })
])

const TimesheetIcon = () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
  h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01' })
])

const ConfigIcon = () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
  h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' }),
  h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z' })
])

const LogsIcon = () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
  h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' })
])

const UpdatesIcon = () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
  h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4' })
])

const HelpIcon = () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
  h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' })
])

const views = [
  { id: 'dashboard', label: 'Dashboard', icon: DashboardIcon, component: DashboardView },
  { id: 'timesheets', label: 'Timesheets', icon: TimesheetIcon, component: TimesheetView },
  { id: 'config', label: 'Configuration', icon: ConfigIcon, component: ConfigView },
  { id: 'logs', label: 'Logs', icon: LogsIcon, component: LogsView },
  { id: 'updates', label: 'Updates', icon: UpdatesIcon, component: UpdatesView },
  { id: 'help', label: 'Help & FAQ', icon: HelpIcon, component: HelpView }
]

const currentViewComponent = computed(() => {
  const view = views.find(v => v.id === currentView.value)
  return view ? view.component : DashboardView
})

onMounted(async () => {
  try {
    await bridgeService.init()
    console.log('Bridge initialized')

    // Fetch app version from backend
    const appInfo = await bridgeService.getAppInfo()
    if (appInfo?.data?.version) {
      appVersion.value = appInfo.data.version
    }
  } catch (err) {
    console.warn('Bridge initialization failed:', err)
    console.log('Running in browser mode (no PyQt6 bridge)')
  }
})
</script>
