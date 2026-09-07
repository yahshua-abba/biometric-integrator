<template>
  <div>
    <header class="bg-slate-900 text-white p-6 space-y-4">
      <div class="flex flex-wrap justify-between gap-3"><h1 class="text-xl font-semibold">Mini Payroll · Manual retry demo</h1><a class="underline" href="/">Deletion replay demo</a></div>
      <p class="text-slate-300">Synthetic employees only. This is the app’s actual Logs Needing Review page, connected to a local test Payroll.</p>
      <ol class="list-decimal ml-5 text-sm space-y-1 text-slate-300"><li>Run ordinary sync: employee mapping failures and missing confirmations enter the queue.</li><li>Fix employee mappings, then run ordinary sync again: the failed records stay in the queue.</li><li>View employees, filter a date range, and open an employee’s logs. Review a selection before retrying.</li></ol>
      <div class="flex flex-wrap gap-3"><button v-for="[method, label] in controls" :key="method" :disabled="busy" class="btn bg-slate-700 hover:bg-slate-600 disabled:opacity-50" @click="action(method)">{{ label }}</button></div>
      <p role="status">{{ message }}</p>
      <div class="border-t border-slate-700 pt-4"><p class="font-semibold">Mini Payroll: {{ state.payroll?.length || 0 }} saved records · {{ state.requests || 0 }} upload requests · Employee mappings {{ state.mapping_fixed ? 'fixed' : 'missing' }}</p>
        <div class="flex flex-wrap gap-3 mt-3"><div v-for="row in state.payroll" :key="row.sync_id" class="rounded border border-slate-600 px-3 py-2 text-sm">{{ row.employee }} · {{ row.date }} · {{ row.log_time }} {{ row.log_type }}</div></div>
      </div>
    </header>
    <RetryQueueView :key="generation" />
  </div>
</template>
<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import RetryQueueView from '../components/RetryQueueView.vue'
import { request } from './api'
const state = ref({}), busy = ref(false), message = ref('Ready. Run ordinary sync to create the test cases.'), generation = ref(0)
const controls = [['sync', 'Run ordinary sync'], ['large', 'Load 300-employee example'], ['fix', 'Fix employee mappings'], ['delete', 'HR deletes saved logs'], ['reset', 'Reset demo']]
async function load() {
  try { const result = await fetch('/retry-state'); state.value = await result.json() }
  catch (err) { message.value = err.message }
}
async function action(method) {
  busy.value = true
  try { const result = await request(method); message.value = result.message; generation.value++; await load() }
  catch (err) { message.value = err.message }
  finally { busy.value = false }
}
let timer
onMounted(() => { load(); timer = setInterval(load, 1000) })
onUnmounted(() => clearInterval(timer))
</script>
