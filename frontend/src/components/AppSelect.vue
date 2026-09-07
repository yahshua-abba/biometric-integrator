<template>
  <div>
    <button ref="trigger" type="button" role="combobox" :aria-label="label" :aria-expanded="open" :aria-controls="listId" aria-haspopup="listbox" :aria-activedescendant="open ? `${listId}-${active}` : undefined" :disabled="disabled" :class="['flex w-full items-center justify-between gap-3 rounded-lg border border-gray-300 bg-white text-left text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50', compact ? 'px-2 py-1 text-xs' : 'px-4 py-2 text-sm']" @click="toggle" @keydown="keydown">
      <span class="truncate">{{ selected?.label || 'Select…' }}</span>
      <svg class="w-4 h-4 shrink-0 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" /></svg>
    </button>
    <Teleport to="body">
      <ul v-if="open" :id="listId" ref="menu" role="listbox" :aria-label="label" :style="position" class="fixed z-50 overflow-y-auto rounded-lg border border-gray-200 bg-white p-1 shadow-lg text-sm">
        <li v-for="(option, index) in options" :id="`${listId}-${index}`" :key="option.value" role="option" :aria-selected="option.value === modelValue" :class="['flex cursor-pointer items-center justify-between gap-3 rounded-md px-3 py-2', active === index ? 'bg-primary-50 text-primary-700' : 'text-gray-700 hover:bg-gray-50']" @pointermove="active = index" @mousedown.prevent @click="choose(index)">
          <span>{{ option.label }}</span><svg v-if="option.value === modelValue" class="w-4 h-4 shrink-0 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg>
        </li>
      </ul>
    </Teleport>
  </div>
</template>
<script>
let nextId = 0
</script>
<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
const props = defineProps({ modelValue: [String, Number], options: { type: Array, required: true }, label: { type: String, required: true }, compact: Boolean, disabled: Boolean })
const emit = defineEmits(['update:modelValue'])
const listId = `app-select-${++nextId}`
const trigger = ref(null), menu = ref(null), open = ref(false), active = ref(0), position = ref({})
const selected = computed(() => props.options.find(option => option.value === props.modelValue))
let search = '', searchAt = 0
function place() {
  if (!open.value || !trigger.value) return
  const rect = trigger.value.getBoundingClientRect(), gap = 6
  if (rect.bottom < 0 || rect.top > window.innerHeight) { close(); return }
  const below = window.innerHeight - rect.bottom - 8 - gap, above = rect.top - 8 - gap
  const desired = Math.min(264, props.options.length * 38 + 8)
  const upward = below < desired && above > below
  const height = Math.max(40, Math.min(desired, upward ? above : below))
  const width = Math.min(Math.max(rect.width, 176), window.innerWidth - 16)
  position.value = { left: `${Math.max(8, Math.min(rect.left, window.innerWidth - width - 8))}px`, width: `${width}px`, maxHeight: `${height}px`, ...(upward ? { bottom: `${window.innerHeight - rect.top + gap}px` } : { top: `${rect.bottom + gap}px` }) }
}
function show() {
  if (props.disabled || !props.options.length) return
  active.value = Math.max(0, props.options.findIndex(option => option.value === props.modelValue))
  open.value = true; place(); reveal()
}
function close() { open.value = false; search = '' }
function toggle() { if (open.value) close(); else show() }
function choose(index) {
  if (!props.options[index]) return
  emit('update:modelValue', props.options[index].value); close(); trigger.value?.focus()
}
async function reveal() { await nextTick(); menu.value?.children[active.value]?.scrollIntoView?.({ block: 'nearest' }) }
function keydown(event) {
  const key = event.key
  if (key === 'Tab') { close(); return }
  if (key === 'Escape') { if (open.value) event.preventDefault(); close(); return }
  if (key === 'Enter' || key === ' ') { event.preventDefault(); if (open.value) choose(active.value); else show(); return }
  if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(key)) {
    event.preventDefault()
    if (!open.value) show()
    else if (key === 'ArrowDown') active.value = Math.min(props.options.length - 1, active.value + 1)
    else if (key === 'ArrowUp') active.value = Math.max(0, active.value - 1)
    if (key === 'Home') active.value = 0
    if (key === 'End') active.value = props.options.length - 1
    reveal(); return
  }
  if (key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
    event.preventDefault(); if (!open.value) show()
    const now = Date.now(); search = (now - searchAt < 800 ? search : '') + key.toLowerCase(); searchAt = now
    const match = props.options.findIndex(option => option.label.toLowerCase().startsWith(search))
    if (match >= 0) { active.value = match; reveal() }
  }
}
function outside(event) { if (!trigger.value?.contains(event.target) && !menu.value?.contains(event.target)) close() }
watch(() => props.disabled, value => { if (value) close() })
watch(() => props.options, () => { if (open.value) { active.value = Math.min(active.value, props.options.length - 1); if (!props.options.length) close(); else place() } })
onMounted(() => { document.addEventListener('pointerdown', outside); document.addEventListener('focusin', outside); window.addEventListener('resize', place); window.addEventListener('scroll', place, true) })
onUnmounted(() => { document.removeEventListener('pointerdown', outside); document.removeEventListener('focusin', outside); window.removeEventListener('resize', place); window.removeEventListener('scroll', place, true) })
</script>
