import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../../lib/api'

type Mode = 'choose' | 'camera'

export default function ImageCapture() {
  const { caseId } = useParams<{ caseId: string }>()
  const navigate = useNavigate()
  const uploadInputRef = useRef<HTMLInputElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [consentGiven, setConsentGiven] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [mode, setMode] = useState<Mode>('choose')
  const [cameraReady, setCameraReady] = useState(false)
  const [consenting, setConsenting] = useState(false)

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
    setCameraReady(false)
  }, [])

  // Clean up camera on unmount
  useEffect(() => {
    return () => stopCamera()
  }, [stopCamera])

  const handleConsent = async () => {
    setConsenting(true)
    setError('')
    try {
      await api.post(`/cases/${caseId}/consent`)
      setConsentGiven(true)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      setError(`Failed to record consent: ${msg}`)
    } finally {
      setConsenting(false)
    }
  }

  const uploadImage = async (blob: Blob) => {
    setUploading(true)
    setError('')
    const formData = new FormData()
    formData.append('image', blob, 'photo.jpg')

    try {
      await api.post(`/cases/${caseId}/image`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      // Image uploaded and assessment auto-generated — go to results
      navigate(`/patient/session/${caseId}/result`)
    } catch {
      setError('Failed to upload image. Please try again.')
      setUploading(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    await uploadImage(file)
  }

  const startCamera = async () => {
    setError('')

    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Camera access requires HTTPS. Make sure you are accessing the app via https://localhost:5173.')
      return
    }

    setMode('camera')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.onloadedmetadata = () => setCameraReady(true)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error('Camera error:', err)
      setError(`Could not access camera: ${msg}. Please check permissions or use "Upload Existing Photo" instead.`)
      setMode('choose')
    }
  }

  const takePhoto = () => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas) return

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.drawImage(video, 0, 0)
    stopCamera()
    setMode('choose')

    canvas.toBlob(
      (blob) => {
        if (blob) uploadImage(blob)
      },
      'image/jpeg',
      0.9,
    )
  }

  const cancelCamera = () => {
    stopCamera()
    setMode('choose')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
          <button onClick={() => { stopCamera(); navigate(`/patient/session/${caseId}`) }} className="text-gray-600 hover:text-gray-900">&larr; Back to Session</button>
          <h1 className="text-xl font-bold text-gray-900">Add Photo</h1>
        </div>
      </nav>

      <main className="max-w-lg mx-auto px-4 py-8 space-y-6">
        {error && <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{error}</div>}

        {uploading ? (
          <div className="bg-white p-6 rounded-xl shadow-sm text-center space-y-4">
            <div className="animate-spin text-5xl">{'\u2699\uFE0F'}</div>
            <h2 className="text-lg font-semibold text-gray-900">Analyzing photo...</h2>
            <p className="text-gray-600 text-sm">
              Uploading image and generating assessment from your interview and photo. This may take a moment.
            </p>
          </div>
        ) : !consentGiven ? (
          <div className="bg-white p-6 rounded-xl shadow-sm text-center space-y-4">
            <div className="text-5xl">{'\uD83D\uDCF7'}</div>
            <h2 className="text-lg font-semibold text-gray-900">Image Consent Required</h2>
            <p className="text-gray-600 text-sm">
              Before adding an image of the affected skin area, the patient must give verbal consent.
              Ask the patient for permission and confirm below.
            </p>
            <button
              onClick={handleConsent}
              disabled={consenting}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {consenting ? 'Recording consent...' : 'Patient Has Given Consent'}
            </button>
          </div>
        ) : mode === 'camera' ? (
          <div className="bg-white p-6 rounded-xl shadow-sm text-center space-y-4">
            <div className="relative rounded-lg overflow-hidden bg-black">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full rounded-lg"
              />
              {!cameraReady && (
                <div className="absolute inset-0 flex items-center justify-center text-white">
                  Starting camera...
                </div>
              )}
            </div>
            <canvas ref={canvasRef} className="hidden" />
            <div className="flex gap-3 justify-center">
              <button
                onClick={cancelCamera}
                className="px-6 py-3 bg-gray-500 text-white rounded-lg font-medium hover:bg-gray-600"
              >
                Cancel
              </button>
              <button
                onClick={takePhoto}
                disabled={!cameraReady || uploading}
                className="px-6 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50"
              >
                {uploading ? 'Uploading...' : 'Take Photo'}
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-white p-6 rounded-xl shadow-sm text-center space-y-6">
            <div className="text-5xl">{'\uD83D\uDCF7'}</div>
            <h2 className="text-lg font-semibold text-gray-900">Add Photo</h2>
            <p className="text-gray-600 text-sm">Provide a photo of the affected skin area.</p>

            <input
              ref={uploadInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileUpload}
              className="hidden"
            />

            <div className="flex flex-col gap-3">
              <button
                onClick={startCamera}
                disabled={uploading}
                className="px-6 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50"
              >
                Capture Photo
              </button>
              <button
                onClick={() => uploadInputRef.current?.click()}
                disabled={uploading}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                Upload Existing Photo
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
