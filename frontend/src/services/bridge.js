/**
 * Biometric Integration - Bridge Service
 * Handles communication with PyQt6 backend via QWebChannel
 */

class BridgeService {
  constructor() {
    this.bridge = null
    this.isReady = false
    this.readyCallbacks = []
  }

  /**
   * Initialize the bridge connection
   */
  async init() {
    return new Promise((resolve, reject) => {
      if (typeof QWebChannel === 'undefined') {
        console.warn('QWebChannel not available - running in browser mode')
        this.isReady = false
        reject(new Error('QWebChannel not available'))
        return
      }

      new QWebChannel(qt.webChannelTransport, (channel) => {
        this.bridge = channel.objects.bridge
        this.isReady = true

        // Set up signal listeners
        this.setupSignalListeners()

        // Notify ready callbacks
        this.readyCallbacks.forEach(callback => callback())
        this.readyCallbacks = []

        console.log('Bridge initialized successfully')
        resolve()
      })
    })
  }

  /**
   * Set up listeners for signals from Python
   */
  setupSignalListeners() {
    if (!this.bridge) return

    // Listen for sync status updates
    this.bridge.syncStatusUpdated.connect((statusJson) => {
      const status = JSON.parse(statusJson)
      window.dispatchEvent(new CustomEvent('syncStatusUpdated', { detail: status }))
    })

    // Listen for sync progress updates
    this.bridge.syncProgressUpdated.connect((progressJson) => {
      const progress = JSON.parse(progressJson)
      window.dispatchEvent(new CustomEvent('syncProgressUpdated', { detail: progress }))
    })

    // Listen for sync completion
    this.bridge.syncCompleted.connect((resultJson) => {
      const result = JSON.parse(resultJson)
      window.dispatchEvent(new CustomEvent('syncCompleted', { detail: result }))
    })
  }

  /**
   * Wait for bridge to be ready
   */
  async whenReady() {
    if (this.isReady) return Promise.resolve()

    return new Promise((resolve) => {
      this.readyCallbacks.push(resolve)
    })
  }

  /**
   * Call a Python method and get the result
   */
  async call(method, ...args) {
    if (!this.isReady || !this.bridge) {
      throw new Error('Bridge not initialized')
    }

    return new Promise((resolve, reject) => {
      try {
        this.bridge[method](...args, (result) => {
          try {
            const parsed = JSON.parse(result)
            if (parsed.success) {
              resolve(parsed)
            } else {
              reject(new Error(parsed.error || 'Unknown error'))
            }
          } catch (e) {
            reject(new Error('Failed to parse bridge response'))
          }
        })
      } catch (error) {
        reject(error)
      }
    })
  }

  // ==================== TIMESHEET METHODS ====================

  async getTimesheetStats() {
    return this.call('getTimesheetStats')
  }

  async getAllTimesheets(limit = 1000, offset = 0) {
    return this.call('getAllTimesheets', limit, offset)
  }

  async getUnsyncedTimesheets(limit = 100) {
    return this.call('getUnsyncedTimesheets', limit)
  }

  async retryFailedTimesheet(timesheetId) {
    return this.call('retryFailedTimesheet', timesheetId)
  }

  async clearTimesheets(dateFrom, dateTo, onlySynced = true) {
    return this.call('clearTimesheets', dateFrom, dateTo, onlySynced)
  }

  // ==================== EMPLOYEE METHODS ====================

  async getAllEmployees() {
    return this.call('getAllEmployees')
  }

  // ==================== SYNC METHODS ====================

  async startPullSync(dateFrom, dateTo, deviceId = -1) {
    // deviceId = -1 means all devices, otherwise specific device ID
    return this.call('startPullSyncWithDevice', dateFrom, dateTo, deviceId)
  }

  async startPushSync() {
    return this.call('startPushSync')
  }

  async getSyncLogs() {
    return this.call('getSyncLogs')
  }

  // ==================== CONFIG METHODS ====================

  async getApiConfig() {
    return this.call('getApiConfig')
  }

  async updateApiConfig(config) {
    return this.call('updateApiConfig', JSON.stringify(config))
  }

  async testConnection(connectionType) {
    return this.call('testConnection', connectionType)
  }

  async loginPush(username, password) {
    return this.call('loginPush', username, password)
  }

  async logoutPush() {
    return this.call('logoutPush')
  }

  // ==================== DEVICE MANAGEMENT METHODS ====================

  async getDevices() {
    return this.call('getDevices')
  }

  async addDevice(name, ip, port = 4370, commKey = 0) {
    return this.call('addDevice', name, ip, port, commKey)
  }

  async updateDevice(deviceId, name, ip, port, commKey, enabled) {
    return this.call('updateDevice', deviceId, name, ip, port, commKey, enabled)
  }

  async deleteDevice(deviceId) {
    return this.call('deleteDevice', deviceId)
  }

  async testDeviceConnection(deviceId) {
    return this.call('testDeviceConnection', deviceId)
  }

  // ==================== UTILITY METHODS ====================

  async getAppInfo() {
    return this.call('getAppInfo')
  }

  logMessage(message) {
    if (this.isReady && this.bridge) {
      this.bridge.logMessage(message)
    }
  }

  async triggerCleanup() {
    return this.call('triggerCleanup')
  }

  // ==================== SYSTEM LOG METHODS ====================

  async getSystemLogFiles() {
    return this.call('getSystemLogFiles')
  }

  async getSystemLogContent(filename) {
    return this.call('getSystemLogContent', filename)
  }
}

// Create singleton instance
const bridgeService = new BridgeService()

export default bridgeService
