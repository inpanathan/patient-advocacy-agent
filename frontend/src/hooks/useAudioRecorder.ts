import { useCallback, useRef, useState } from 'react'

export function useAudioRecorder() {
  const [recording, setRecording] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const start = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
    chunksRef.current = []

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data)
    }

    mediaRecorderRef.current = recorder
    recorder.start()
    setRecording(true)
  }, [])

  const stop = useCallback((): Promise<Blob> => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current
      if (!recorder) {
        resolve(new Blob())
        return
      }

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        // Stop all tracks to release the mic
        recorder.stream.getTracks().forEach((t) => t.stop())
        setRecording(false)
        resolve(blob)
      }

      recorder.stop()
    })
  }, [])

  return { recording, start, stop }
}
