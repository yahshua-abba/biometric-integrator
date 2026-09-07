import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({
  plugins: [vue()], base: '/retry/',
  build: { outDir: 'dist-demo', rollupOptions: { input: 'retry-demo.html' } },
})
