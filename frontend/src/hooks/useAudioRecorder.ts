import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Audio recorder that keeps the mic stream open across recordings.
 *
 * The stream is acquired once (on first `start()` call) and reused.
 * Only the MediaRecorder is started/stopped on each press/release,
 * so there is zero latency when the user begins speaking.
 */
export function useAudioRecorder() {
  const [recording, setRecording] = useState(false)
  const [ready, setReady] = useState(false)
  const streamRef = useRef<MediaStream | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  // Acquire mic stream once on mount
  useEffect(() => {
    let cancelled = false

    navigator.mediaDevices
      .getUserMedia({ audio: true })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop())
          return
        }
        streamRef.current = stream
        setReady(true)
      })
      .catch(() => {
        // Mic permission denied — will be handled on start
      })

    return () => {
      cancelled = true
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop())
        streamRef.current = null
      }
    }
  }, [])

  const start = useCallback(() => {
    const stream = streamRef.current
    if (!stream) return

    chunksRef.current = []

    const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data)
    }

    mediaRecorderRef.current = recorder
    // Produce a chunk every 200ms so short recordings still have data
    recorder.start(200)
    setRecording(true)
  }, [])

  const stop = useCallback((): Promise<Blob> => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current
      if (!recorder || recorder.state === 'inactive') {
        setRecording(false)
        resolve(new Blob())
        return
      }

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        mediaRecorderRef.current = null
        setRecording(false)
        resolve(blob)
      }

      recorder.stop()
    })
  }, [])

  return { recording, ready, start, stop }
}
