<template>
  <div class="relative" @keydown.esc="close">
    <span class="block text-xs font-medium text-gray-500 mb-1.5">Employees</span>
    <button ref="trigger" class="input flex items-center justify-between gap-2 text-sm text-left" :aria-expanded="open" aria-controls="employee-filter-panel" @click="toggle">
      <span class="truncate">{{ modelValue.length ? `${modelValue.length} employee${modelValue.length === 1 ? '' : 's'} selected` : 'All employees' }}</span><span aria-hidden="true">⌄</span>
    </button>
    <div v-if="open" id="employee-filter-panel" class="absolute right-0 top-full mt-2 w-80 max-w-[85vw] bg-white border border-gray-200 rounded-lg shadow-lg z-20 p-3 space-y-3">
      <input ref="searchInput" v-model="search" aria-label="Find employees" placeholder="Search name or employee code" class="input text-sm" maxlength="100" />
      <p v-if="error" role="alert" class="text-xs text-red-700">{{ error }}</p>
      <div class="max-h-52 overflow-y-auto" :aria-busy="loading">
        <label v-for="employee in rows" :key="employee.employee_id" class="flex items-center gap-3 p-2 rounded hover:bg-gray-50 cursor-pointer text-sm">
          <input type="checkbox" :checked="modelValue.some(e => e.employee_id === employee.employee_id)" @change="select(employee, $event.target.checked)" />
          <span class="min-w-0"><span class="block truncate">{{ employee.employee_name }}</span><span class="text-xs text-gray-500">{{ employee.employee_code }}</span></span>
        </label>
        <p v-if="!rows.length" class="p-3 text-sm text-gray-500">{{ loading ? 'Finding employees…' : 'No employees match this search.' }}</p>
      </div>
      <div class="flex items-center justify-between text-xs"><button :disabled="page <= 1 || loading" @click="page--">Previous</button><span>{{ total.toLocaleString() }} {{ total === 1 ? 'employee' : 'employees' }}</span><button :disabled="page * 20 >= total || loading" @click="page++">Next</button></div>
      <div class="border-t pt-3 flex items-center justify-between text-sm"><button class="text-gray-500" @click="$emit('update:modelValue', [])">Clear ({{ modelValue.length }})</button><button class="text-primary-700 font-medium" @click="close">Done</button></div>
    </div>
  </div>
</template>
<script setup>
import { nextTick, onUnmounted, ref, watch } from 'vue'
import bridge from '../services/bridge'
const props = defineProps({ modelValue: { type: Array, default: () => [] }, filters: { type: Object, required: true } })
const emit = defineEmits(['update:modelValue', 'open-change'])
const open = ref(false), search = ref(''), page = ref(1), rows = ref([]), total = ref(0), loading = ref(false), error = ref('')
const trigger = ref(null), searchInput = ref(null)
let revision = 0, timer
async function load() {
  const ticket = ++revision
  loading.value = true
  try {
    const result = await bridge.getRetryQueuePage({ ...props.filters, employee_ids: [], state: 'all', search: search.value, mode: 'employees', page: page.value, page_size: 20 })
    if (ticket !== revision) return
    rows.value = result.data.rows; total.value = result.data.total; error.value = ''
  } catch (err) { if (ticket === revision) error.value = err.message }
  finally { if (ticket === revision) loading.value = false }
}
async function toggle() {
  open.value = !open.value; emit('open-change', open.value)
  if (open.value) { load(); await nextTick(); searchInput.value?.focus() }
}
function close() { open.value = false; emit('open-change', false); trigger.value?.focus() }
function select(employee, checked) {
  emit('update:modelValue', checked ? [...props.modelValue, employee] : props.modelValue.filter(e => e.employee_id !== employee.employee_id))
}
watch(search, () => { revision++; rows.value = []; loading.value = true; page.value = 1; clearTimeout(timer); timer = setTimeout(load, 200) })
watch(page, () => { if (open.value) load() })
watch(() => [props.filters.date_from, props.filters.date_to, props.filters.slot], () => { if (open.value) { page.value = 1; load() } })
onUnmounted(() => { revision++; clearTimeout(timer) })
</script>
