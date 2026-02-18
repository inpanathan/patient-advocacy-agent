# ADR-001: Voice-Only Interface via WebRTC

**Status:** Accepted
**Date:** 2026-02-18
**Context:** Target patients are illiterate and cannot interact with text-based UIs.

## Decision
Use a voice-only interface with WebRTC for real-time audio streaming, Whisper for STT, and a TTS service for spoken responses.

## Consequences
- No text UI needed, reducing frontend complexity
- Requires robust STT for multiple Indian languages
- WebRTC adds infrastructure complexity but enables real-time camera access
- Mock implementations allow development without audio hardware
