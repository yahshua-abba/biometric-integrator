<template>
  <div class="p-6 space-y-6">
    <h1 class="text-3xl font-bold text-gray-900">Help & FAQ</h1>

    <!-- System Overview -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
        System Overview
      </h2>
      <p class="text-sm text-gray-700 mb-4">
        The Biometric Integration System connects ZKTeco devices with the YAHSHUA Payroll Solution using The ABBA Biometric Integration App. The system supports both push and pull synchronization modes with flexible connectivity options.
      </p>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
        <div class="bg-gray-50 rounded-lg p-4">
          <h3 class="font-semibold text-gray-800 mb-2">Connection Types</h3>
          <ul class="space-y-2 text-gray-600">
            <li><strong>Cable (Wired)</strong> &mdash; Direct UTP/Ethernet cable connection between ZKTeco device and router. Provides stable, secure connectivity with minimal latency. Ideal for permanent installations.</li>
            <li><strong>WiFi (Wireless)</strong> &mdash; Wireless network connection to the router allowing flexible device placement. Ideal for remote locations or environments where cabling is impractical.</li>
          </ul>
        </div>
        <div class="bg-gray-50 rounded-lg p-4">
          <h3 class="font-semibold text-gray-800 mb-2">Synchronization Modes</h3>
          <ul class="space-y-2 text-gray-600">
            <li><strong>Pull Mode</strong> &mdash; The app automatically retrieves attendance data from the ZKTeco device at scheduled intervals. Use "Pull Data Now" for manual, immediate syncing.</li>
            <li><strong>Push Mode</strong> &mdash; The system uploads retrieved attendance data to the Cloud Payroll system. Use "Push Data Now" to manually send logs when needed.</li>
          </ul>
        </div>
      </div>
      <div class="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <div class="bg-primary-50 rounded-lg p-3 text-center">
          <div class="font-semibold text-primary-800">Auto Sync</div>
          <div class="text-primary-600 text-xs mt-1">Real-time or scheduled data transfer</div>
        </div>
        <div class="bg-primary-50 rounded-lg p-3 text-center">
          <div class="font-semibold text-primary-800">Flexible Connectivity</div>
          <div class="text-primary-600 text-xs mt-1">Wired (UTP) and wireless (WiFi)</div>
        </div>
        <div class="bg-primary-50 rounded-lg p-3 text-center">
          <div class="font-semibold text-primary-800">Multi-Branch</div>
          <div class="text-primary-600 text-xs mt-1">Centralized data from multiple locations</div>
        </div>
        <div class="bg-primary-50 rounded-lg p-3 text-center">
          <div class="font-semibold text-primary-800">No Manual Entry</div>
          <div class="text-primary-600 text-xs mt-1">Automated attendance tracking</div>
        </div>
      </div>
    </div>

    <!-- A. How to Connect the Biometric Device -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        A. How to Connect the Biometric Device to a PC/Laptop
      </h2>
      <div class="mb-4">
        <h3 class="text-sm font-semibold text-gray-800 mb-2">Prerequisites</h3>
        <ul class="text-sm text-gray-600 list-disc ml-5 space-y-1">
          <li>Router with available ethernet ports</li>
          <li>ZKTeco biometric device with UTP port</li>
          <li>UTP/Ethernet cable (for wired connection)</li>
          <li>PC/Laptop with network connectivity</li>
        </ul>
      </div>
      <div>
        <h3 class="text-sm font-semibold text-gray-800 mb-2">Steps</h3>
        <ol class="space-y-3 text-sm text-gray-700">
          <li class="flex gap-3">
            <span class="flex-shrink-0 w-6 h-6 bg-green-100 text-green-700 rounded-full flex items-center justify-center text-xs font-bold">1</span>
            <span>Prepare the router, biometric device, and UTP cable.</span>
          </li>
          <li class="flex gap-3">
            <span class="flex-shrink-0 w-6 h-6 bg-green-100 text-green-700 rounded-full flex items-center justify-center text-xs font-bold">2</span>
            <span>Verify that your biometric device is a ZKTeco brand device with a UTP port.</span>
          </li>
          <li class="flex gap-3">
            <span class="flex-shrink-0 w-6 h-6 bg-green-100 text-green-700 rounded-full flex items-center justify-center text-xs font-bold">3</span>
            <span>Connect the biometric device to the router using the UTP cable.</span>
          </li>
          <li class="flex gap-3">
            <span class="flex-shrink-0 w-6 h-6 bg-green-100 text-green-700 rounded-full flex items-center justify-center text-xs font-bold">4</span>
            <span>Connect your PC/Laptop to the same router via UTP cable or WiFi.</span>
          </li>
        </ol>
      </div>
      <div class="mt-4 bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-800">
        Connection Complete! Your biometric device is now connected to your PC/Laptop through the router.
      </div>
    </div>

    <!-- B. How to Install the App -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        B. How to Install The ABBA Biometric Integration App
      </h2>
      <ol class="space-y-3 text-sm text-gray-700">
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold">1</span>
          <span>Download the installer from the <strong>Updates</strong> page in this app, or from <a href="https://showcase.yahshuapayroll.com/downloads" target="_blank" class="text-blue-600 hover:underline">showcase.yahshuapayroll.com/downloads</a>.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold">2</span>
          <span>Double-click the downloaded installer to run.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold">3</span>
          <span>A dialog box will appear. Click <strong>Next</strong> to proceed.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold">4</span>
          <span>Another dialog box will appear. Click <strong>Next</strong> again.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold">5</span>
          <span>A dialog box will show the installation progress.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold">6</span>
          <span>Wait for the installation to complete.</span>
        </li>
      </ol>
    </div>

    <!-- C. How to Login and Configure -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        C. How to Login and Configure the App
      </h2>

      <h3 class="text-sm font-semibold text-gray-800 mb-2">Add New Device</h3>
      <ol class="space-y-3 text-sm text-gray-700 mb-6">
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-purple-100 text-purple-700 rounded-full flex items-center justify-center text-xs font-bold">1</span>
          <span>Navigate to the <strong>Configuration</strong> tab.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-purple-100 text-purple-700 rounded-full flex items-center justify-center text-xs font-bold">2</span>
          <span>Click the <strong>"+ Add Device"</strong> button.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-purple-100 text-purple-700 rounded-full flex items-center justify-center text-xs font-bold">3</span>
          <span>Enter the device details: Name, IP Address, Port (default 4370), Comm Key (password), and Branch ID (optional).</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-purple-100 text-purple-700 rounded-full flex items-center justify-center text-xs font-bold">4</span>
          <span>Click <strong>"Add Device"</strong> to save.</span>
        </li>
      </ol>

      <h3 class="text-sm font-semibold text-gray-800 mb-2">Test Connection</h3>
      <ol class="space-y-3 text-sm text-gray-700 mb-6">
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-purple-100 text-purple-700 rounded-full flex items-center justify-center text-xs font-bold">5</span>
          <span>Click <strong>"Test"</strong> next to the device to verify the app can communicate with your ZKTeco device.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-purple-100 text-purple-700 rounded-full flex items-center justify-center text-xs font-bold">6</span>
          <span>If the connection is successful, a success message will appear.</span>
        </li>
      </ol>

      <h3 class="text-sm font-semibold text-gray-800 mb-2">Login to the Payroll System</h3>
      <ol class="space-y-3 text-sm text-gray-700">
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-purple-100 text-purple-700 rounded-full flex items-center justify-center text-xs font-bold">1</span>
          <span>Navigate to the <strong>Configuration</strong> tab.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-purple-100 text-purple-700 rounded-full flex items-center justify-center text-xs font-bold">2</span>
          <span>If needed, update the <strong>API URL</strong> to match your payroll server address. Only change this if directed by your administrator.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-purple-100 text-purple-700 rounded-full flex items-center justify-center text-xs font-bold">3</span>
          <span>Under "Push Configuration", enter your email/username and password, then click <strong>"Login"</strong>.</span>
        </li>
      </ol>
    </div>

    <!-- D. ID Reference Settings -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <svg class="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3.001 3.001 0 00-2.83 2M15 11h3m-3 4h2" />
        </svg>
        D. ID Reference Settings (Biometric Integration)
      </h2>
      <p class="text-sm text-gray-700 mb-4">
        Before registering employees in the biometric device, make sure the correct ID setting is enabled in YAHSHUA Payroll.
      </p>
      <div class="bg-orange-50 border border-orange-200 rounded-lg p-4 text-sm text-orange-800 mb-4">
        <strong>Where to find this setting:</strong> In Web Payroll, go to <em>Settings &rarr; Companies &rarr; General Settings &rarr; Timesheets and Timekeeper Settings</em>, then scroll down to "Biometric Integration".
      </div>
      <ul class="text-sm text-gray-700 space-y-3">
        <li>
          <strong>"Use System ID instead of Employee ID"</strong> &mdash; When checked, the system uses the auto-generated System ID. When unchecked, it uses the Employee ID (manual/employee code).
        </li>
        <li>
          <strong>"Use Biometrics ID"</strong> &mdash; This is the default ID used in the biometric device when registering employees.
        </li>
      </ul>
    </div>

    <!-- E. Register Employees in ZKTeco Device -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <svg class="w-6 h-6 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
        </svg>
        E. Register Employees in the ZKTeco Device
      </h2>
      <div class="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800 mb-4">
        <strong>Important:</strong> The ID used in ZKTeco <strong>must match</strong> the ID setting selected in Payroll. If not matched, attendance logs may sync to the wrong employee or may not sync at all.
      </div>
      <ol class="space-y-3 text-sm text-gray-700">
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center text-xs font-bold">1</span>
          <span>Open the ZKTeco device menu.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center text-xs font-bold">2</span>
          <span>Go to <strong>User Management / Add User</strong>.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center text-xs font-bold">3</span>
          <span>Enter the employee ID based on the Payroll setting (System ID, Employee ID, or Biometrics ID).</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center text-xs font-bold">4</span>
          <span>Register the employee's fingerprint or face (depending on device).</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center text-xs font-bold">5</span>
          <span>Save the employee record.</span>
        </li>
      </ol>
    </div>

    <!-- F. Pull Data Now -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        F. Pull Data Now
      </h2>
      <p class="text-sm text-gray-700 mb-3">Test the setup with one employee:</p>
      <ol class="space-y-3 text-sm text-gray-700">
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center text-xs font-bold">1</span>
          <span>Have the employee tap in or out on the ZKTeco device.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center text-xs font-bold">2</span>
          <span>Go to the <strong>Dashboard</strong> and click <strong>"Pull"</strong>. Select the date range and device.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center text-xs font-bold">3</span>
          <span>Confirm that the test attendance log appears correctly in the app's <strong>Timesheets</strong> page.</span>
        </li>
      </ol>
    </div>

    <!-- G. Push Data Now -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
        </svg>
        G. Push Data Now
      </h2>
      <ol class="space-y-3 text-sm text-gray-700">
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-green-100 text-green-700 rounded-full flex items-center justify-center text-xs font-bold">1</span>
          <span>Make sure you have pulled the latest attendance logs from the ZKTeco device.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-green-100 text-green-700 rounded-full flex items-center justify-center text-xs font-bold">2</span>
          <span>Click the <strong>"Push"</strong> button on the <strong>Dashboard</strong>.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-green-100 text-green-700 rounded-full flex items-center justify-center text-xs font-bold">3</span>
          <span>The system will upload the pulled logs to the Web Payroll system.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-green-100 text-green-700 rounded-full flex items-center justify-center text-xs font-bold">4</span>
          <span>A push notification will appear confirming the logs were successfully sent.</span>
        </li>
      </ol>
    </div>

    <!-- H. Verify Attendance in Web Payroll -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        H. Verify Attendance in Web Payroll
      </h2>
      <p class="text-sm text-gray-700 mb-3">After pushing the attendance data, verify it appears correctly in Web Payroll:</p>
      <ol class="space-y-3 text-sm text-gray-700">
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold">1</span>
          <span>Go to the <strong>payroll website</strong> and sign in with your credentials.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold">2</span>
          <span>Navigate to <strong>Timesheet &rarr; Daily Logs</strong>.</span>
        </li>
        <li class="flex gap-3">
          <span class="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold">3</span>
          <span>Check if the employee's attendance appears correctly in the logs.</span>
        </li>
      </ol>
      <div class="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
        <strong>Tip:</strong> If the test employee or pulled logs are not visible, review the Pull/Push steps and try again with a test entry.
      </div>
    </div>

    <!-- Troubleshooting -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        Troubleshooting Common Issues
      </h2>

      <div class="space-y-2">
        <div v-for="(item, index) in troubleshootingItems" :key="'ts-' + index" class="border rounded-lg">
          <button
            @click="toggleTroubleshooting(index)"
            class="w-full flex items-center justify-between px-4 py-3 text-left text-sm font-medium text-gray-800 hover:bg-gray-50 transition-colors"
          >
            <span>{{ item.issue }}</span>
            <svg
              class="w-5 h-5 text-gray-400 transition-transform duration-200"
              :class="{ 'rotate-180': openTroubleshooting === index }"
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          <div v-if="openTroubleshooting === index" class="px-4 pb-4 text-sm text-gray-600 border-t bg-gray-50">
            <div class="pt-3" v-html="item.solution"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- FAQ -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Frequently Asked Questions
      </h2>

      <div class="space-y-2">
        <div v-for="(item, index) in faqItems" :key="'faq-' + index" class="border rounded-lg">
          <button
            @click="toggleFaq(index)"
            class="w-full flex items-center justify-between px-4 py-3 text-left text-sm font-medium text-gray-800 hover:bg-gray-50 transition-colors"
          >
            <span>{{ item.question }}</span>
            <svg
              class="w-5 h-5 text-gray-400 transition-transform duration-200"
              :class="{ 'rotate-180': openFaq === index }"
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          <div v-if="openFaq === index" class="px-4 pb-4 text-sm text-gray-600 border-t bg-gray-50">
            <div class="pt-3" v-html="item.answer"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Compatible Biometrics -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <svg class="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
        </svg>
        Compatible ZKTeco Biometric Devices
      </h2>
      <div class="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm text-gray-700">
        <div v-for="device in compatibleDevices" :key="device" class="bg-gray-50 rounded-lg p-3 text-center font-medium">
          {{ device }}
        </div>
      </div>
    </div>

    <!-- Need More Help -->
    <div class="card bg-blue-50 border-blue-200">
      <h2 class="text-xl font-semibold mb-2 text-blue-900">Need More Help?</h2>
      <p class="text-sm text-blue-800 mb-3">
        If you're experiencing issues that aren't covered above, try the following:
      </p>
      <ul class="text-sm text-blue-800 space-y-1 list-disc ml-5">
        <li>Check the <strong>Logs</strong> page for sync activity and errors</li>
        <li>View <strong>System Logs</strong> in Configuration for detailed debug information</li>
        <li>Contact your system administrator or IT support team</li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const openFaq = ref(null)
const openTroubleshooting = ref(null)

const toggleFaq = (index) => {
  openFaq.value = openFaq.value === index ? null : index
}

const toggleTroubleshooting = (index) => {
  openTroubleshooting.value = openTroubleshooting.value === index ? null : index
}

const compatibleDevices = [
  'K14', 'K20', 'K30', 'K40',
  'U580', 'T4-C', 'iClock260',
  'MA300', 'RSP10K1', 'iFace402/ID'
]

const troubleshootingItems = [
  {
    issue: 'Connection Test Failed',
    solution: `
      <ul class="list-disc ml-5 space-y-2">
        <li>Verify the device is <strong>powered ON</strong> and connected to the same network.</li>
        <li>Check the <strong>IP address and port</strong> settings on the ZKTeco device.</li>
        <li><strong>Ping the device</strong> from your PC to test connectivity:
          <div class="bg-gray-800 text-green-400 rounded p-2 mt-1 font-mono text-xs">ping 192.168.1.201</div>
          <ul class="list-disc ml-5 mt-1">
            <li>If <em>Request Timed Out</em> &rarr; device is not reachable on the network.</li>
            <li>If <em>Reply received</em> &rarr; network connection is OK, check Comm Key and port.</li>
          </ul>
        </li>
      </ul>
    `
  },
  {
    issue: 'IP Address Conflict',
    solution: `
      <p>Assign a new free IP address to the ZKTeco device:</p>
      <ol class="list-decimal ml-5 mt-2 space-y-1">
        <li>Ping a random IP in your network range to check if it's available:
          <div class="bg-gray-800 text-green-400 rounded p-2 mt-1 font-mono text-xs">ping 192.168.1.250</div>
        </li>
        <li>If <em>Request Timed Out</em>, the IP is likely free to use.</li>
        <li>Set that IP on the ZKTeco device via its network settings menu.</li>
        <li>Update the new IP in the Integration App under <strong>Configuration &rarr; Edit Device</strong>.</li>
      </ol>
    `
  },
  {
    issue: 'UTP / LAN Cable Issue',
    solution: `
      <ul class="list-disc ml-5 space-y-1">
        <li><strong>Replace the UTP/LAN cable</strong> &mdash; it may be old or damaged.</li>
        <li>Plug the cable into a <strong>different switch/router port</strong>.</li>
        <li>Check if <strong>LAN port LED lights are active</strong> on both the device and the switch/router.</li>
      </ul>
    `
  },
  {
    issue: 'Wrong Network Configuration',
    solution: `
      <p>Check the following settings on the ZKTeco device:</p>
      <ul class="list-disc ml-5 mt-2 space-y-1">
        <li><strong>IP Address</strong> &mdash; must be in the same subnet as your PC</li>
        <li><strong>Subnet Mask</strong> &mdash; typically <code class="bg-gray-200 px-1 rounded text-xs">255.255.255.0</code></li>
        <li><strong>Gateway</strong> &mdash; your router IP, e.g., <code class="bg-gray-200 px-1 rounded text-xs">192.168.1.1</code></li>
        <li><strong>DNS</strong> &mdash; if required by your network</li>
      </ul>
    `
  },
  {
    issue: 'Upload Failed / Sync Errors',
    solution: `
      <ul class="list-disc ml-5 space-y-1">
        <li>Check your <strong>internet connection</strong>.</li>
        <li>Verify your <strong>login credentials</strong> in the Configuration page.</li>
        <li>Make sure <strong>employee IDs match</strong> between the Payroll System and the ZKTeco Device.</li>
        <li>Retry sync using the <strong>Pull</strong> or <strong>Push</strong> button on the Dashboard.</li>
        <li>Restart the Integration App.</li>
      </ul>
    `
  }
]

const faqItems = [
  {
    question: 'What is the Comm Key (password)?',
    answer: `
      <p>The Comm Key is a numeric password set on some ZKTeco devices to restrict access. If your device has a communication password configured, you must enter the same value here. Leave it as <strong>0</strong> if your device has no password.</p>
      <p class="mt-2">You can find or change the Comm Key in your ZKTeco device's menu under <em>Communication Settings</em>.</p>
    `
  },
  {
    question: 'What is the Branch ID for?',
    answer: `
      <p>The Branch ID is an optional field that tells the payroll system which branch or location the attendance data belongs to. This is useful when you have multiple ZKTeco devices across different office locations.</p>
      <p class="mt-2">If your organization uses a single branch, you can leave this blank. Check with your payroll administrator for the correct Branch ID value.</p>
    `
  },
  {
    question: 'Which ID should I use when registering employees in the ZKTeco device?',
    answer: `
      <p>The ID must match the setting selected in YAHSHUA Payroll under <em>Settings &rarr; Companies &rarr; General Settings &rarr; Timesheets and Timekeeper Settings &rarr; Biometric Integration</em>.</p>
      <ul class="list-disc ml-5 mt-2 space-y-1">
        <li><strong>"Use System ID instead of Employee ID"</strong> checked &rarr; use the auto-generated System ID</li>
        <li><strong>"Use System ID instead of Employee ID"</strong> unchecked &rarr; use the Employee ID (manual/employee code)</li>
        <li><strong>"Use Biometrics ID"</strong> &rarr; use the default biometric device ID</li>
      </ul>
      <p class="mt-2 text-red-600"><strong>Important:</strong> If the IDs don't match, attendance logs may sync to the wrong employee or may not sync at all.</p>
    `
  },
  {
    question: 'What do the timesheet statuses mean?',
    answer: `
      <ul class="list-disc ml-5 mt-1 space-y-1">
        <li><strong>Synced</strong> (green) &mdash; Successfully pushed to the payroll system</li>
        <li><strong>Pending</strong> (yellow) &mdash; Pulled from device but not yet pushed to payroll</li>
        <li><strong>Error</strong> (red) &mdash; Push failed. Check the error message for details. You can retry failed records from the Timesheets page.</li>
      </ul>
    `
  },
  {
    question: 'Can I manage multiple devices and branches?',
    answer: `
      <p>Yes. You can add as many ZKTeco devices as needed from the <strong>Configuration</strong> page. Each device can have its own IP, port, Comm Key, and Branch ID. When pulling data, you can choose to pull from all enabled devices at once or select a specific device.</p>
      <p class="mt-2">For multi-branch setups, each branch has its own ZKTeco device(s) connected via WiFi or cable. All attendance data is synced to the centralized Web Payroll system.</p>
    `
  },
  {
    question: 'What is the difference between Pull and Push?',
    answer: `
      <ul class="list-disc ml-5 space-y-2">
        <li><strong>Pull</strong> &mdash; Retrieves (downloads) attendance data <em>from</em> the ZKTeco device into the Integration App. The data is stored locally until pushed.</li>
        <li><strong>Push</strong> &mdash; Uploads (sends) the locally stored attendance data <em>to</em> the YAHSHUA Web Payroll system.</li>
      </ul>
      <p class="mt-2">Both can run automatically on a schedule or be triggered manually from the Dashboard.</p>
    `
  },
  {
    question: 'How do I verify that attendance data was synced correctly?',
    answer: `
      <p>After pushing data, sign in to the <strong>payroll website</strong> and navigate to <strong>Timesheet &rarr; Daily Logs</strong>. Check if the employee's attendance appears correctly.</p>
      <p class="mt-2">If logs are not visible, review the Pull/Push steps and try again with a test entry.</p>
    `
  },
  {
    question: 'How do I view sync activity and errors?',
    answer: `
      <p>There are two places to check:</p>
      <ul class="list-disc ml-5 mt-2 space-y-1">
        <li><strong>Logs page</strong> &mdash; Shows sync operation history (pull/push) with status, record counts, and error messages</li>
        <li><strong>Timesheets page</strong> &mdash; Filter by "Errors" status to see individual records that failed to sync, along with the specific error reason</li>
      </ul>
      <p class="mt-2">For deeper debugging, use <strong>System Logs</strong> in Configuration to view raw application log files.</p>
    `
  }
]
</script>
