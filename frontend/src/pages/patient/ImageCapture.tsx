import { useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../../lib/api'

export default function ImageCapture() {
  const { caseId } = useParams<{ caseId: string }>()
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [consentGiven, setConsentGiven] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<{ image_id: string; rag_results: unknown } | null>(null)
  const [error, setError] = useState('')

  const handleConsent = async () => {
    try {
      await api.post(`/cases/${caseId}/consent`)
      setConsentGiven(true)
    } catch {
      setError('Failed to record consent')
    }
  }

  const handleCapture = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError('')
    const formData = new FormData()
    formData.append('image', file)

    try {
      const res = await api.post(`/cases/${caseId}/image`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResult(res.data)
    } catch {
      setError('Failed to upload image')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
          <button onClick={() => navigate(`/patient/session/${caseId}`)} className="text-gray-600 hover:text-gray-900">&larr; Back to Session</button>
          <h1 className="text-xl font-bold text-gray-900">Image Capture</h1>
        </div>
      </nav>

      <main className="max-w-lg mx-auto px-4 py-8 space-y-6">
        {error && <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{error}</div>}

        {!consentGiven ? (
          <div className="bg-white p-6 rounded-xl shadow-sm text-center space-y-4">
            <div className="text-5xl">&#128247;</div>
            <h2 className="text-lg font-semibold text-gray-900">Image Consent Required</h2>
            <p className="text-gray-600 text-sm">
              Before capturing an image of the affected skin area, the patient must give verbal consent.
              Ask the patient for permission and confirm below.
            </p>
            <button
              onClick={handleConsent}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700"
            >
              Patient Has Given Consent
            </button>
          </div>
        ) : result ? (
          <div className="bg-white p-6 rounded-xl shadow-sm text-center space-y-4">
            <div className="text-5xl text-green-600">&#10003;</div>
            <h2 className="text-lg font-semibold text-gray-900">Image Uploaded</h2>
            <p className="text-gray-600 text-sm">The image has been analyzed for similar cases.</p>
            <button
              onClick={() => navigate(`/patient/session/${caseId}`)}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700"
            >
              Return to Session
            </button>
          </div>
        ) : (
          <div className="bg-white p-6 rounded-xl shadow-sm text-center space-y-4">
            <div className="text-5xl">&#128247;</div>
            <h2 className="text-lg font-semibold text-gray-900">Capture Image</h2>
            <p className="text-gray-600 text-sm">Take a photo of the affected skin area.</p>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleCapture}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="px-6 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50"
            >
              {uploading ? 'Uploading...' : 'Take Photo'}
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
