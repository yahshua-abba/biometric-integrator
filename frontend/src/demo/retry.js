// Separate demo bundle: this adapter is never imported by the shipping desktop app.
import { createApp } from 'vue'
import '../style.css'
import Demo from './RetryDemo.vue'
import bridge from '../services/bridge'
import { request } from './api'
bridge.whenReady = async () => {}
bridge.getRetryQueue = filters => request('getRetryQueue', filters)
bridge.retryTimesheets = async payload => {
  const result = await request('retryTimesheets', payload)
  setTimeout(() => window.dispatchEvent(new CustomEvent('syncCompleted', { detail: { type: 'push', manual_retry: true, result } })), 0)
  return result
}
createApp(Demo).mount('#app')
