<template>
  <footer class="border-t px-4 py-3 flex flex-wrap items-center justify-between gap-3 text-xs text-gray-500">
    <div class="flex items-center gap-2"><span>Rows per page</span><AppSelect :model-value="pageSize" :options="[{ value: 25, label: '25' }, { value: 50, label: '50' }, { value: 100, label: '100' }]" label="Rows per page" compact @update:model-value="$emit('update:pageSize', $event)" /></div>
    <div class="flex items-center gap-4">
      <span>{{ number(total ? (page - 1) * pageSize + 1 : 0) }}–{{ number(Math.min(page * pageSize, total)) }} of {{ number(total) }} {{ unit }}</span>
      <button :disabled="page <= 1 || loading" @click="$emit('update:page', page - 1)">Previous</button>
      <button :disabled="page * pageSize >= total || loading" @click="$emit('update:page', page + 1)">Next</button>
    </div>
  </footer>
</template>
<script setup>
import AppSelect from './AppSelect.vue'
defineProps({ page: { type: Number, required: true }, pageSize: { type: Number, required: true }, total: { type: Number, required: true }, unit: { type: String, required: true }, loading: Boolean })
defineEmits(['update:page', 'update:pageSize'])
const number = value => Number(value || 0).toLocaleString()
</script>
