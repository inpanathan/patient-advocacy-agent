import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../../lib/api'
import StatusBadge from '../../components/StatusBadge'

interface CaseDetail {
  id: string
  case_number: string
  status: string
  escalated: boolean
  soap_note: {
    subjective: string
    objective: string
    assessment: string
    plan: string
    disclaimer: string
  } | null
  icd_codes: string[] | null
  interview_transcript: Array<{ role: string; text: string }> | null
  doctor_notes: string | null
  images: Array<{ id: string; file_path: string; rag_results: unknown }>
}

export default function CaseReview() {
  const { caseId } = useParams<{ caseId: string }>()
  const navigate = useNavigate()
  const [caseData, setCaseData] = useState<CaseDetail | null>(null)
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.get(`/cases/${caseId}/summary`)
      .then((res) => {
        setCaseData(res.data)
        setNotes(res.data.doctor_notes || '')
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [caseId])

  const handleStartReview = async () => {
    try {
      await api.put(`/doctor/cases/${caseId}/review`)
      setCaseData((prev) => prev ? { ...prev, status: 'under_review' } : prev)
    } catch { /* ignore */ }
  }

  const handleSaveNotes = async () => {
    setSaving(true)
    try {
      await api.put(`/doctor/cases/${caseId}/notes`, { notes })
    } catch { /* ignore */ }
    finally { setSaving(false) }
  }

  const handleComplete = async () => {
    setSaving(true)
    try {
      const res = await api.put(`/doctor/cases/${caseId}/complete`, {
        notes: notes || null,
        final_icd_codes: caseData?.icd_codes || null,
      })
      setCaseData(res.data)
    } catch { /* ignore */ }
    finally { setSaving(false) }
  }

  if (loading) return <div className="flex items-center justify-center h-screen">Loading...</div>
  if (!caseData) return <div className="flex items-center justify-center h-screen text-red-600">Case not found</div>

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/doctor/cases')} className="text-gray-600 hover:text-gray-900">&larr; Back</button>
            <h1 className="text-xl font-bold text-gray-900">{caseData.case_number}</h1>
            <StatusBadge status={caseData.status} escalated={caseData.escalated} />
          </div>
          <div className="flex gap-3">
            {caseData.status === 'awaiting_review' && (
              <button onClick={handleStartReview} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
                Start Review
              </button>
            )}
            {caseData.status === 'under_review' && (
              <button onClick={handleComplete} disabled={saving} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50">
                {saving ? 'Completing...' : 'Complete Review'}
              </button>
            )}
          </div>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* SOAP Note */}
        <div className="lg:col-span-2 space-y-6">
          {caseData.escalated && (
            <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg">
              <p className="font-bold text-red-800">ESCALATED: Suspected malignancy</p>
            </div>
          )}

          {caseData.soap_note && (
            <div className="bg-white p-6 rounded-xl shadow-sm space-y-4">
              <h2 className="text-lg font-semibold">SOAP Note</h2>
              {(['subjective', 'objective', 'assessment', 'plan'] as const).map((section) => (
                <div key={section}>
                  <h3 className="text-sm font-bold text-gray-700 uppercase">{section}</h3>
                  <p className="text-sm text-gray-800 mt-1 whitespace-pre-wrap">
                    {caseData.soap_note?.[section]}
                  </p>
                </div>
              ))}
              {caseData.soap_note.disclaimer && (
                <p className="text-xs text-red-600 italic mt-4">{caseData.soap_note.disclaimer}</p>
              )}
            </div>
          )}

          {caseData.icd_codes && caseData.icd_codes.length > 0 && (
            <div className="bg-white p-6 rounded-xl shadow-sm">
              <h2 className="text-lg font-semibold mb-3">ICD Codes</h2>
              <div className="flex flex-wrap gap-2">
                {caseData.icd_codes.map((code) => (
                  <span key={code} className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-mono">{code}</span>
                ))}
              </div>
            </div>
          )}

          {/* Transcript */}
          {caseData.interview_transcript && caseData.interview_transcript.length > 0 && (
            <div className="bg-white p-6 rounded-xl shadow-sm">
              <h2 className="text-lg font-semibold mb-3">Interview Transcript</h2>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {caseData.interview_transcript.map((entry, i) => (
                  <div key={i} className="text-sm">
                    <span className="font-medium text-gray-700">{entry.role}:</span>{' '}
                    <span className="text-gray-600">{entry.text}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar: notes + images */}
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-xl shadow-sm">
            <h2 className="text-lg font-semibold mb-3">Doctor Notes</h2>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={6}
              className="w-full p-3 border border-gray-300 rounded-lg text-sm"
              placeholder="Add your clinical notes here..."
              disabled={caseData.status === 'completed'}
            />
            {caseData.status !== 'completed' && (
              <button
                onClick={handleSaveNotes}
                disabled={saving}
                className="mt-2 px-4 py-2 bg-gray-600 text-white rounded-lg text-sm hover:bg-gray-700 disabled:opacity-50"
              >
                Save Notes
              </button>
            )}
          </div>

          {caseData.images && caseData.images.length > 0 && (
            <div className="bg-white p-6 rounded-xl shadow-sm">
              <h2 className="text-lg font-semibold mb-3">Images ({caseData.images.length})</h2>
              <div className="space-y-2">
                {caseData.images.map((img) => (
                  <div key={img.id} className="p-2 border rounded-lg text-xs text-gray-500 font-mono truncate">
                    {img.file_path.split('/').pop()}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
