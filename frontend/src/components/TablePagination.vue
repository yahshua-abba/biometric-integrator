<template>
  <footer class="border-t px-4 py-3 flex flex-wrap items-center justify-between gap-3 text-xs text-gray-500">
    <label>Rows per page <select :value="pageSize" class="ml-2 rounded border border-gray-200 p-1" @change="$emit('update:pageSize', Number($event.target.value))"><option :value="25">25</option><option :value="50">50</option><option :value="100">100</option></select></label>
    <div class="flex items-center gap-4">
      <span>{{ number(total ? (page - 1) * pageSize + 1 : 0) }}–{{ number(Math.min(page * pageSize, total)) }} of {{ number(total) }} {{ unit }}</span>
      <button :disabled="page <= 1 || loading" @click="$emit('update:page', page - 1)">Previous</button>
      <button :disabled="page * pageSize >= total || loading" @click="$emit('update:page', page + 1)">Next</button>
    </div>
  </footer>
</template>
<script setup>
defineProps({ page: { type: Number, required: true }, pageSize: { type: Number, required: true }, total: { type: Number, required: true }, unit: { type: String, required: true }, loading: Boolean })
defineEmits(['update:page', 'update:pageSize'])
const number = value => Number(value || 0).toLocaleString()
</script>
