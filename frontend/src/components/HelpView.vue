<template>
  <main class="p-6 lg:p-8 max-w-screen-2xl mx-auto space-y-5">
    <header class="flex flex-wrap items-start justify-between gap-4">
      <div><h1 class="text-2xl font-semibold tracking-tight text-gray-900">Help & FAQ</h1><p class="text-sm text-gray-500 mt-1">Set up your device, understand attendance, and review uploads safely.</p></div>
      <div class="flex gap-2"><button class="btn btn-secondary text-sm" :disabled="busy" @click="copyGuide">Copy Guide</button><button class="btn btn-primary text-sm" :disabled="busy" @click="askChatGPT">Ask ChatGPT <span aria-hidden="true">↗</span></button></div>
    </header>
    <section class="rounded-lg border border-primary-100 bg-primary-50 p-4 text-sm text-gray-700">
      <p>Ask ChatGPT opens your browser with this guide included. Then ask your question. Only the guide is shared; employee records and credentials are not included.</p>
      <p class="mt-1 text-xs text-gray-500">You may need to sign in. If the guide does not appear, use Copy Guide and paste it into ChatGPT.</p>
      <p v-if="notice" role="status" class="mt-2 text-primary-700">{{ notice }}</p>
      <p v-if="error" role="alert" class="mt-2 text-red-700">{{ error }}</p>
      <textarea v-if="manualCopy" :value="guidePrompt" readonly aria-label="Guide to copy" class="input mt-3 h-40 text-xs" @focus="$event.target.select()"></textarea>
    </section>
    <label class="block"><span class="sr-only">Search the guide</span><input v-model="search" type="search" placeholder="Search the guide: retries, duplicates, devices…" class="input text-sm" /></label>
    <section v-for="section in visibleSections" :key="section.id" class="bg-white border border-gray-200 rounded-lg p-5">
      <h2 class="text-base font-semibold text-gray-900">{{ section.title }}</h2>
      <ul class="mt-3 space-y-3 text-sm leading-6 text-gray-600 list-disc pl-5"><li v-for="item in section.items" :key="item">{{ item }}</li></ul>
    </section>
    <p v-if="!visibleSections.length" class="py-8 text-center text-sm text-gray-500">No matching guide sections. Try another search or clear the search.</p>
  </main>
</template>
<script setup>
import { computed, ref } from 'vue'
import bridge from '../services/bridge'
import { helpSections, guidePrompt, chatGptGuideUrl } from '../content/helpGuide'
const search = ref(''), busy = ref(false), notice = ref(''), error = ref(''), manualCopy = ref(false)
const visibleSections = computed(() => helpSections.filter(section => (section.title + ' ' + section.items.join(' ')).toLowerCase().includes(search.value.trim().toLowerCase())))
async function copyGuide() {
  error.value = ''; notice.value = ''; busy.value = true
  try {
    if (bridge.isReady) await bridge.copyHelpGuide(guidePrompt)
    else await navigator.clipboard.writeText(guidePrompt)
    notice.value = 'Guide copied. Paste it into ChatGPT and ask your question.'
  } catch { error.value = 'Copy was unavailable. Select and copy the guide below.'; manualCopy.value = true }
  finally { busy.value = false }
}
async function askChatGPT() {
  error.value = ''; notice.value = ''; busy.value = true
  try {
    if (bridge.isReady) {
      const result = await bridge.openChatGPTGuide(guidePrompt)
      notice.value = result.message
    } else {
      // Open during the click so browser popup blockers can recognize user intent.
      const tab = window.open(chatGptGuideUrl, '_blank')
      if (!tab) throw new Error('The browser blocked the ChatGPT tab. Allow popups or copy the guide and open chatgpt.com.')
      tab.opener = null
      notice.value = 'ChatGPT opened with the guide. Sign in if needed, then ask your question.'
    }
  } catch (err) { error.value = err.message; manualCopy.value = true }
  finally { busy.value = false }
}
</script>
