import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: 'demo-recording.spec.ts',
  timeout: 300_000, // 5 minutes for the full recording
  expect: { timeout: 30_000 },
  use: {
    baseURL: 'https://localhost:5173',
    viewport: { width: 1920, height: 1080 },
    video: {
      mode: 'on',
      size: { width: 1920, height: 1080 },
    },
    screenshot: 'off',
    trace: 'off',
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    ignoreHTTPSErrors: true,
    launchOptions: {
      slowMo: 120,
      args: [
        '--use-fake-ui-for-media-stream',
        '--use-fake-device-for-media-stream',
        '--no-sandbox',
      ],
    },
  },
  projects: [
    {
      name: 'demo',
      use: {
        browserName: 'chromium',
      },
    },
  ],
  reporter: [['list']],
  outputDir: '../output/playwright-results',
});
