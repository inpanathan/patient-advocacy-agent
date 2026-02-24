import { Page } from '@playwright/test';
import * as path from 'path';

const DEMO_DIR = path.resolve(__dirname, '..');
const ASSETS_DIR = path.join(DEMO_DIR, 'assets');
const PROJECT_ROOT = path.resolve(DEMO_DIR, '..');

/**
 * Login to the application.
 * Uses form fields: #email, #password and button "Sign in".
 * After login, redirects to /patient/ (admin) or /doctor/ (doctor).
 */
export async function login(page: Page, email: string, password: string): Promise<void> {
  await page.goto('/login');
  await page.waitForLoadState('networkidle');
  await page.fill('#email', email);
  await page.fill('#password', password);
  await page.click('button:has-text("Sign in")');
  await page.waitForURL(/\/(patient|doctor)\//);
  await page.waitForLoadState('networkidle');
}

/**
 * Logout from the application.
 * Clicks the "Logout" button (text-red-600) present in the nav bar.
 */
export async function logout(page: Page): Promise<void> {
  const logoutBtn = page.locator('button:has-text("Logout")');
  if (await logoutBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await logoutBtn.click();
    await page.waitForURL(/\/login/);
    await page.waitForLoadState('networkidle');
  } else {
    // Fallback: navigate directly to login
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
  }
}

/**
 * Type text character by character with a delay for visual effect.
 */
export async function typeWithDelay(page: Page, selector: string, text: string, delay = 50): Promise<void> {
  await page.click(selector);
  for (const char of text) {
    await page.keyboard.type(char, { delay });
  }
}

/**
 * Smooth scroll to the bottom of the page in increments.
 */
export async function smoothScroll(page: Page, distance = 300, steps = 5, interval = 400): Promise<void> {
  for (let i = 0; i < steps; i++) {
    await page.mouse.wheel(0, distance);
    await page.waitForTimeout(interval);
  }
}

/**
 * Navigate to a local HTML asset file.
 */
export async function showAsset(page: Page, filename: string): Promise<void> {
  const filePath = path.join(ASSETS_DIR, filename);
  await page.goto(`file://${filePath}`);
  await page.waitForLoadState('domcontentloaded');
}

/**
 * Get the absolute path to the demo SCIN image for upload.
 */
export function getDemoImagePath(): string {
  return path.join(PROJECT_ROOT, 'data', 'raw', 'scin', 'images', '-101827005996397499_1.jpg');
}

/**
 * Wait for a specific duration with a visual countdown (for timing with narration).
 */
export async function holdScene(page: Page, durationMs: number): Promise<void> {
  await page.waitForTimeout(durationMs);
}

/**
 * Simulate sending a voice message via the API (bypasses mic recording).
 *
 * Creates a minimal valid WAV file and sends it as multipart form-data
 * to POST /api/v1/cases/:caseId/audio, matching the actual endpoint.
 */
export async function sendChatMessage(
  page: Page,
  caseId: string,
  message: string,
  token: string,
): Promise<void> {
  await page.evaluate(
    async ({ caseId, message, token }) => {
      // Create a minimal 1-second silent WAV (44-byte header + 22050 zero samples)
      const sampleRate = 22050;
      const numSamples = sampleRate; // 1 second
      const dataSize = numSamples * 2; // 16-bit mono
      const buffer = new ArrayBuffer(44 + dataSize);
      const view = new DataView(buffer);

      // WAV header
      const writeString = (offset: number, s: string) => {
        for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i));
      };
      writeString(0, 'RIFF');
      view.setUint32(4, 36 + dataSize, true);
      writeString(8, 'WAVE');
      writeString(12, 'fmt ');
      view.setUint32(16, 16, true); // chunk size
      view.setUint16(20, 1, true);  // PCM
      view.setUint16(22, 1, true);  // mono
      view.setUint32(24, sampleRate, true);
      view.setUint32(28, sampleRate * 2, true); // byte rate
      view.setUint16(32, 2, true);  // block align
      view.setUint16(34, 16, true); // bits per sample
      writeString(36, 'data');
      view.setUint32(40, dataSize, true);
      // Data is all zeros (silence) — the STT will return empty/fallback text

      const blob = new Blob([buffer], { type: 'audio/wav' });
      const formData = new FormData();
      formData.append('audio', blob, 'recording.wav');

      await fetch(`/api/v1/cases/${caseId}/audio`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });
    },
    { caseId, message, token },
  );
  // Wait for UI to update with the response
  await page.waitForTimeout(5000);
}

/**
 * Get auth token from localStorage after login.
 */
export async function getAuthToken(page: Page): Promise<string> {
  return await page.evaluate(() => {
    return localStorage.getItem('access_token') || '';
  });
}
