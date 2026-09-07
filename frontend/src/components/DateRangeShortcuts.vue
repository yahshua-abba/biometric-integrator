<template>
  <div class="flex flex-wrap items-center gap-3 text-xs text-gray-500">
    <span>Quick dates:</span><button @click="choose(7)">Last 7 days</button><button @click="choose(30)">Last 30 days</button><button @click="choose(0)">All dates</button>
  </div>
</template>
<script setup>
const emit = defineEmits(['change'])
function choose(days) {
  if (!days) { emit('change', { date_from: '', date_to: '' }); return }
  const format = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  const now = new Date(), from = new Date(now)
  from.setDate(from.getDate() - days + 1)
  emit('change', { date_from: format(from), date_to: format(now) })
}
</script>
