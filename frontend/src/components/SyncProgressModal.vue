<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center">
    <!-- Backdrop -->
    <div class="absolute inset-0 bg-black bg-opacity-50"></div>

    <!-- Modal -->
    <div class="relative bg-white rounded-lg shadow-xl p-6 w-full max-w-md mx-4">
      <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
        </svg>
        Syncing to YAHSHUA Payroll
      </h2>

      <!-- Per-destination progress -->
      <div class="space-y-5">
        <div v-for="cfg in configList" :key="cfg.slot">
          <!-- Destination label (shown only when more than one destination) -->
          <div v-if="configList.length > 1" class="text-sm font-semibold text-gray-700 mb-1">
            {{ cfg.label }}
            <span v-if="cfg.completed" class="text-green-600 ml-1">✓ done</span>
          </div>

          <div class="text-sm font-medium text-gray-600 mb-1">
            Processing batch {{ cfg.batch_current }} / {{ cfg.batch_total }}
          </div>

          <!-- Progress Bar -->
          <div class="w-full bg-gray-200 rounded-full h-4 mb-1">
            <div
              class="bg-green-500 h-4 rounded-full transition-all duration-300"
              :style="{ width: percent(cfg) + '%' }"
            ></div>
          </div>

          <div class="flex items-center justify-between text-sm">
            <div class="flex items-center gap-3">
              <span class="text-green-600 font-medium">{{ cfg.success.toLocaleString() }} synced</span>
              <span class="text-gray-300">|</span>
              <span class="text-red-600 font-medium">{{ cfg.failed.toLocaleString() }} failed</span>
            </div>
            <span class="text-gray-500">{{ percent(cfg) }}%</span>
          </div>
        </div>
      </div>

      <!-- Spinner -->
      <div class="flex justify-center mt-4">
        <svg class="animate-spin h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  // Map/array of per-destination progress. Falls back to a single default row.
  configs: {
    type: Array,
    default: () => []
  }
})

const configList = computed(() => {
  if (props.configs && props.configs.length > 0) return props.configs
  return [{
    slot: 1,
    label: 'Payroll 1',
    batch_current: 0,
    batch_total: 0,
    success: 0,
    failed: 0,
    completed: false
  }]
})

const percent = (cfg) => {
  if (!cfg.batch_total) return 0
  return Math.round((cfg.batch_current / cfg.batch_total) * 100)
}
</script>
