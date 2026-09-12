/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: 'localhost',
    port: 5173,
    // Thà chết hẳn còn hơn nhảy sang 5174: cổng khác sẽ trượt CORS của backend
    // và biểu hiện thành một lỗi rất khó lần ra nguyên nhân.
    strictPort: true,
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
