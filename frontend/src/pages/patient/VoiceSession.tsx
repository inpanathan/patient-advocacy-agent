import { useState, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAudioRecorder } from '../../hooks/useAudioRecorder'
import api from '../../lib/api'
import MicrophoneButton from '../../components/MicrophoneButton'
import AudioPlayer from '../../components/AudioPlayer'

interface ChatMessage {
  role: 'patient' | 'system'
  text: string
  audioUrl?: string
}

export default function VoiceSession() {
  const { caseId } = useParams<{ caseId: string }>()
  const navigate = useNavigate()
  const { recording, start, stop } = useAudioRecorder()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [processing, setProcessing] = useState(false)
  const [stage, setStage] = useState('in_progress')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleRelease = async () => {
    const blob = await stop()
    if (blob.size === 0) return

    setProcessing(true)
    const formData = new FormData()
    formData.append('audio', blob, 'recording.webm')

    try {
      const res = await api.post(`/cases/${caseId}/audio`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      // Add patient message (from STT)
      setMessages((prev) => [...prev, { role: 'patient', text: '(audio recorded)' }])

      // Add system response with audio
      const audioBytes = Uint8Array.from(atob(res.data.audio_base64), (c) => c.charCodeAt(0))
      const audioBlob = new Blob([audioBytes], { type: `audio/${res.data.audio_format || 'wav'}` })
      const audioUrl = URL.createObjectURL(audioBlob)

      setMessages((prev) => [...prev, { role: 'system', text: res.data.response, audioUrl }])
      setStage(res.data.stage)

      // Auto-play response
      const audio = new Audio(audioUrl)
      audio.play().catch(() => {})

      scrollToBottom()
    } catch {
      setMessages((prev) => [...prev, { role: 'system', text: 'Error processing audio. Please try again.' }])
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/patient/dashboard')} className="text-gray-600 hover:text-gray-900">&larr;</button>
            <h1 className="text-xl font-bold text-gray-900">Voice Session</h1>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge stage={stage} />
            <button
              onClick={() => navigate(`/patient/session/${caseId}/image`)}
              className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700"
            >
              Capture Image
            </button>
            <button
              onClick={() => navigate(`/patient/session/${caseId}/result`)}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700"
            >
              Complete
            </button>
          </div>
        </div>
      </nav>

      <main className="flex-1 max-w-3xl mx-auto w-full px-4 py-6 flex flex-col">
        {/* Chat messages */}
        <div className="flex-1 space-y-4 overflow-y-auto mb-6">
          {messages.length === 0 && (
            <p className="text-center text-gray-500 mt-8">Hold the microphone button and speak to begin the interview.</p>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'patient' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] p-3 rounded-lg ${msg.role === 'patient' ? 'bg-blue-100 text-blue-900' : 'bg-white border shadow-sm'}`}>
                <p className="text-sm">{msg.text}</p>
                {msg.audioUrl && <AudioPlayer src={msg.audioUrl} />}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Push-to-talk */}
        <div className="flex flex-col items-center pb-8">
          {processing && <p className="text-sm text-gray-500 mb-2">Processing...</p>}
          <MicrophoneButton
            recording={recording}
            onPress={start}
            onRelease={handleRelease}
            disabled={processing}
          />
          <p className="text-xs text-gray-400 mt-2">Hold to talk, release to send</p>
        </div>
      </main>
    </div>
  )
}

function StatusBadge({ stage }: { stage: string }) {
  const colors: Record<string, string> = {
    in_progress: 'bg-yellow-100 text-yellow-800',
    analysis: 'bg-blue-100 text-blue-800',
    complete: 'bg-green-100 text-green-800',
    escalated: 'bg-red-100 text-red-800',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[stage] || 'bg-gray-100 text-gray-800'}`}>
      {stage.replace('_', ' ')}
    </span>
  )
}
