/**
 * Demo video recording automation.
 *
 * Records a 3-minute demo of the Patient Advocacy Agent by automating
 * the browser through all 5 scenes defined in demo/config.json.
 *
 * Playwright's built-in video capture produces a WebM file that is later
 * merged with Piper TTS narration via ffmpeg.
 */
import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { login, logout, showAsset, holdScene, smoothScroll, getDemoImagePath, typeWithDelay } from './helpers';

const DEMO_DIR = path.resolve(__dirname, '..');
const OUTPUT_DIR = path.join(DEMO_DIR, 'output');
const TIMING_PATH = path.join(OUTPUT_DIR, 'narration', 'timing.json');

// Load narration timing if available (for syncing scene durations)
function getSceneDuration(sceneId: string, fallbackMs: number): number {
  try {
    const timing = JSON.parse(fs.readFileSync(TIMING_PATH, 'utf-8'));
    if (timing[sceneId]) {
      // Add 2 second buffer after narration ends
      return Math.max(timing[sceneId] * 1000 + 2000, fallbackMs);
    }
  } catch {
    // timing.json not generated yet, use fallback
  }
  return fallbackMs;
}

test('Record full demo video', async ({ page }) => {
  // =========================================================================
  // SCENE 1: Problem Statement + Architecture (0:00 - 0:30)
  // =========================================================================

  // Title card
  await showAsset(page, 'title_card.html');
  await holdScene(page, getSceneDuration('scene_01_intro', 8000) * 0.3);

  // Architecture diagram (wait for Mermaid to render)
  await showAsset(page, 'architecture.html');
  await page.waitForTimeout(3000); // Mermaid render time
  await holdScene(page, getSceneDuration('scene_01_intro', 12000) * 0.4);

  // Stats overlay
  await showAsset(page, 'stats_overlay.html');
  await holdScene(page, getSceneDuration('scene_01_intro', 10000) * 0.3);

  // =========================================================================
  // SCENE 2: Patient Voice Session (0:30 - 1:30)
  // =========================================================================

  // Login as admin (patient-mode operator)
  await login(page, 'admin@test.com', 'test');
  await page.waitForTimeout(1500);

  // Navigate to patient dashboard — shows quick-action cards
  await page.goto('/patient/dashboard');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);

  // Click "Register New Patient" link card
  const registerLink = page.locator('a[href="/patient/register"]');
  if (await registerLink.isVisible({ timeout: 3000 }).catch(() => false)) {
    await registerLink.click();
  } else {
    await page.goto('/patient/register');
  }
  await page.waitForURL(/\/patient\/register/);
  await page.waitForTimeout(1000);

  // Fill registration form (3 select dropdowns: Age Range, Sex, Language)
  const selects = page.locator('select');
  await selects.nth(0).selectOption('30-40');
  await page.waitForTimeout(500);
  await selects.nth(1).selectOption('male');
  await page.waitForTimeout(500);
  await selects.nth(2).selectOption('hi');
  await page.waitForTimeout(500);

  await page.click('button:has-text("Register Patient")');
  await page.waitForTimeout(3000);

  // Start session — navigate to patient selection page
  await page.goto('/patient/start');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1500);

  // Select the first available patient radio button
  const patientRadio = page.locator('input[type="radio"][name="patient"]').first();
  if (await patientRadio.isVisible()) {
    await patientRadio.click();
    await page.waitForTimeout(800);
  }

  // Click "Start Voice Session" to create case (auto-assigns doctor)
  await page.click('button:has-text("Start Voice Session")');
  await page.waitForTimeout(3000);

  // Case created — click "Begin Voice Session" to enter voice chat
  const beginButton = page.locator('button:has-text("Begin Voice Session")');
  if (await beginButton.isVisible({ timeout: 5000 }).catch(() => false)) {
    await beginButton.click();
    await page.waitForTimeout(2000);
  }

  // We're now on /patient/session/:caseId (voice session page)
  // Wait for greeting from the assistant (auto-fetched via POST /cases/:caseId/greet)
  await page.waitForTimeout(5000);

  // Show the voice session chat with greeting message visible
  await page.waitForTimeout(3000);

  // Click "Take Photo & Assess" button in the nav bar to move to image capture
  const photoButton = page.locator('button:has-text("Take Photo & Assess")');
  if (await photoButton.isVisible({ timeout: 5000 }).catch(() => false)) {
    await photoButton.click();
    await page.waitForTimeout(2000);
  } else {
    // Fallback: navigate directly to image capture page
    const currentUrl = page.url();
    const caseIdMatch = currentUrl.match(/\/session\/([^/]+)/);
    if (caseIdMatch) {
      await page.goto(`/patient/session/${caseIdMatch[1]}/image`);
      await page.waitForTimeout(2000);
    }
  }

  // Image consent screen — "Image Consent Required" with consent button
  const consentButton = page.locator('button:has-text("Patient Has Given Consent")');
  if (await consentButton.isVisible({ timeout: 5000 }).catch(() => false)) {
    await page.waitForTimeout(2000); // Pause to show consent gate on camera
    await consentButton.click();
    await page.waitForTimeout(2000);
  }

  // Upload the demo SCIN image via "Upload Existing Photo" button
  const demoImage = getDemoImagePath();
  if (fs.existsSync(demoImage)) {
    const uploadBtn = page.locator('button:has-text("Upload Existing Photo")');
    if (await uploadBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      // The button triggers uploadInputRef.current.click() on a hidden file input.
      // Use Playwright's file chooser interception to set the file.
      const fileChooserPromise = page.waitForEvent('filechooser');
      await uploadBtn.click();
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(demoImage);
    } else {
      // Fallback: set files directly on the hidden input
      const fileInput = page.locator('input[type="file"]');
      if (await fileInput.count() > 0) {
        await fileInput.setInputFiles(demoImage);
      }
    }
    // Wait for upload + SOAP generation (image upload auto-triggers assessment).
    // The page auto-navigates to /patient/session/:caseId/result on success.
    await page.waitForTimeout(15000);
  }

  // We should now be on the result page (/patient/session/:caseId/result)
  // If not auto-navigated, navigate manually
  if (!page.url().includes('/result')) {
    const currentUrl2 = page.url();
    const caseIdMatch2 = currentUrl2.match(/\/session\/([^/]+)/);
    if (caseIdMatch2) {
      await page.goto(`/patient/session/${caseIdMatch2[1]}/result`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);
    }
  }

  // If SOAP note is not yet ready, click "Generate Assessment"
  const generateBtn = page.locator('button:has-text("Generate Assessment")');
  if (await generateBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await generateBtn.click();
    // Wait for SOAP generation (can take a while with real model)
    await page.waitForTimeout(15000);
  }

  // Show the SOAP note result (Case Assessment page)
  await page.waitForTimeout(3000);

  // Scroll through the SOAP note to show all sections
  await smoothScroll(page, 250, 4, 600);
  await page.waitForTimeout(2000);

  // Click "Listen" button to play patient explanation via TTS
  const listenBtn = page.locator('button:has-text("Listen")');
  if (await listenBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await listenBtn.click();
    // Let the audio play for a few seconds (the explanation is ~6 sentences)
    await page.waitForTimeout(8000);
    // Stop playback
    const stopBtn = page.locator('button:has-text("Stop")');
    if (await stopBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
      await stopBtn.click();
      await page.waitForTimeout(1000);
    }
  }

  // Hold to fill scene 2 duration
  await holdScene(page, getSceneDuration('scene_02_patient', 5000) * 0.1);

  // =========================================================================
  // SCENE 3: Doctor Portal (1:30 - 2:15)
  // =========================================================================

  // Logout admin
  await logout(page);
  await page.waitForTimeout(1000);

  // Login as doctor
  await login(page, 'doctor1@test.com', 'test');
  await page.waitForTimeout(2000);

  // Doctor case queue — shows stats cards + filterable case grid
  await page.goto('/doctor/cases');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(3000);

  // Click into the first case card (link to /doctor/cases/:caseId)
  const caseCard = page.locator('a[href*="/doctor/cases/"]').first();
  if (await caseCard.isVisible({ timeout: 5000 }).catch(() => false)) {
    await caseCard.click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
  }

  // Start review (changes status: awaiting_review → under_review)
  const startReviewBtn = page.locator('button:has-text("Start Review")');
  if (await startReviewBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await startReviewBtn.click();
    await page.waitForTimeout(2000);
  }

  // Scroll through SOAP note, ICD codes, and transcript in doctor view
  await smoothScroll(page, 200, 5, 500);
  await page.waitForTimeout(2000);

  // Add doctor notes (textarea placeholder: "Add your clinical notes here...")
  const notesTextarea = page.locator('textarea[placeholder="Add your clinical notes here..."]');
  if (await notesTextarea.isVisible({ timeout: 3000 }).catch(() => false)) {
    await typeWithDelay(
      page,
      'textarea[placeholder="Add your clinical notes here..."]',
      'Patient presents with localized eczema on forearms. Recommend topical corticosteroid and follow-up in 2 weeks.',
      30,
    );
    await page.waitForTimeout(1000);

    // Save notes
    const saveBtn = page.locator('button:has-text("Save Notes")');
    if (await saveBtn.isVisible()) {
      await saveBtn.click();
      await page.waitForTimeout(1500);
    }
  }

  // Complete review (changes status: under_review → completed)
  const completeBtn = page.locator('button:has-text("Complete Review")');
  if (await completeBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await completeBtn.click();
    await page.waitForTimeout(3000);
  }

  // Hold for scene 3 duration
  await holdScene(page, getSceneDuration('scene_03_doctor', 3000) * 0.1);

  // =========================================================================
  // SCENE 4: Monitoring Dashboard + Safety (2:15 - 2:45)
  // =========================================================================

  // Navigate to the server-rendered monitoring dashboard (served at GET /dashboard)
  // This is a backend HTML page with Plotly charts for health, safety, bias metrics
  await page.goto('http://localhost:8001/dashboard');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(4000); // Allow Plotly charts to render

  // Smooth scroll through the dashboard (health, performance, vector space, safety, bias)
  await smoothScroll(page, 300, 6, 700);
  await page.waitForTimeout(2000);

  // Scroll back to top
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
  await page.waitForTimeout(2000);

  // Hold for scene 4 duration
  await holdScene(page, getSceneDuration('scene_04_monitoring', 3000) * 0.1);

  // =========================================================================
  // SCENE 5: Closing — Edge Deployment + Impact (2:45 - 3:00)
  // =========================================================================

  // Architecture diagram one more time
  await showAsset(page, 'architecture.html');
  await page.waitForTimeout(3000); // Mermaid render
  await holdScene(page, 5000);

  // Closing card
  await showAsset(page, 'closing_card.html');
  await holdScene(page, getSceneDuration('scene_05_closing', 12000));

  // Done — Playwright will save the video automatically
});
