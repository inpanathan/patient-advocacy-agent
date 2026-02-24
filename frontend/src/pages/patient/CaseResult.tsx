import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../../lib/api'
import PrintableReport from '../../components/PrintableReport'

interface CaseSummary {
  id: string
  case_number: string
  status: string
  soap_note: {
    subjective: string
    objective: string
    assessment: string
    plan: string
    disclaimer: string
    patient_explanation?: string
  } | null
  icd_codes: string[] | null
  interview_transcript: Array<{ role: string; text: string }> | null
  escalated: boolean
  images: Array<{ id: string; file_path: string }>
}

export default function CaseResult() {
  const { caseId } = useParams<{ caseId: string }>()
  const navigate = useNavigate()
  const [summary, setSummary] = useState<CaseSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [completing, setCompleting] = useState(false)
  const [error, setError] = useState('')

  // TTS playback state
  const [audioLoading, setAudioLoading] = useState(false)
  const [audioPlaying, setAudioPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const audioUrlRef = useRef<string | null>(null)

  const handleComplete = async () => {
    setCompleting(true)
    setError('')
    try {
      const res = await api.post(`/cases/${caseId}/complete`)
      setSummary(res.data)
    } catch {
      setError('Failed to complete case. The photo may not have been uploaded yet.')
    } finally {
      setCompleting(false)
    }
  }

  const handlePlayExplanation = async () => {
    // If already playing, stop
    if (audioPlaying && audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
      setAudioPlaying(false)
      return
    }

    // If we already have the audio cached, replay it
    if (audioUrlRef.current) {
      const audio = new Audio(audioUrlRef.current)
      audioRef.current = audio
      audio.onended = () => setAudioPlaying(false)
      audio.onerror = () => setAudioPlaying(false)
      setAudioPlaying(true)
      audio.play().catch(() => setAudioPlaying(false))
      return
    }

    // Fetch TTS audio from backend
    setAudioLoading(true)
    try {
      const res = await api.post(`/cases/${caseId}/explain-audio`)
      const { audio_base64, audio_format } = res.data

      const audioBytes = Uint8Array.from(atob(audio_base64), (c) => c.charCodeAt(0))
      const audioBlob = new Blob([audioBytes], { type: `audio/${audio_format || 'wav'}` })
      const url = URL.createObjectURL(audioBlob)
      audioUrlRef.current = url

      const audio = new Audio(url)
      audioRef.current = audio
      audio.onended = () => setAudioPlaying(false)
      audio.onerror = () => setAudioPlaying(false)
      setAudioPlaying(true)
      await audio.play()
    } catch {
      setError('Failed to generate voice explanation.')
    } finally {
      setAudioLoading(false)
    }
  }

  // Clean up audio URL on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
      }
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current)
      }
    }
  }, [])

  useEffect(() => {
    api.get(`/cases/${caseId}/summary`)
      .then((res) => setSummary(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [caseId])

  if (loading) return <div className="flex items-center justify-center h-screen">Loading assessment...</div>

  const hasExplanation = !!summary?.soap_note?.patient_explanation

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b print:hidden">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/patient/dashboard')} className="text-gray-600 hover:text-gray-900">&larr; Dashboard</button>
            <h1 className="text-xl font-bold text-gray-900">Case Assessment</h1>
          </div>
          <div className="flex gap-3">
            {summary?.soap_note && (
              <button
                onClick={() => window.print()}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg text-sm hover:bg-gray-700"
              >
                Print Report
              </button>
            )}
          </div>
        </div>
      </nav>

      <main className="max-w-3xl mx-auto px-4 py-8">
        {error && <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm mb-6">{error}</div>}

        {summary?.escalated && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6 rounded-r-lg">
            <p className="font-bold text-red-800">ESCALATED: Suspected malignancy detected</p>
            <p className="text-red-700 text-sm">This case requires immediate professional medical review.</p>
          </div>
        )}

        {summary?.soap_note ? (
          <>
            <PrintableReport summary={summary} />

            {/* Patient Explanation — Voice Playback */}
            {hasExplanation && (
              <div className="mt-6 bg-white p-6 rounded-xl shadow-sm print:hidden">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-lg font-semibold text-gray-900">Patient Explanation</h2>
                  <button
                    onClick={handlePlayExplanation}
                    disabled={audioLoading}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      audioPlaying
                        ? 'bg-red-100 text-red-700 hover:bg-red-200'
                        : 'bg-blue-600 text-white hover:bg-blue-700'
                    } disabled:opacity-50`}
                  >
                    {audioLoading ? (
                      <>
                        <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Generating...
                      </>
                    ) : audioPlaying ? (
                      <>
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><rect x="6" y="5" width="4" height="14" rx="1" /><rect x="14" y="5" width="4" height="14" rx="1" /></svg>
                        Stop
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
                        Listen
                      </>
                    )}
                  </button>
                </div>
                <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                  {summary.soap_note.patient_explanation}
                </p>
              </div>
            )}
          </>
        ) : (
          <div className="bg-white p-6 rounded-xl shadow-sm text-center space-y-4">
            <p className="text-gray-600">
              No assessment available yet. Make sure a photo has been uploaded, then generate the assessment.
            </p>
            <button
              onClick={handleComplete}
              disabled={completing}
              className="px-6 py-3 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50"
            >
              {completing ? 'Generating assessment...' : 'Generate Assessment'}
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
