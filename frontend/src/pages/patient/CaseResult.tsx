import { useEffect, useState } from 'react'
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

  const handleComplete = async () => {
    setCompleting(true)
    setError('')
    try {
      const res = await api.post(`/cases/${caseId}/complete`)
      setSummary(res.data)
    } catch {
      setError('Failed to complete case')
    } finally {
      setCompleting(false)
    }
  }

  useEffect(() => {
    // Try to get existing summary first
    api.get(`/cases/${caseId}/summary`)
      .then((res) => setSummary(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [caseId])

  if (loading) return <div className="flex items-center justify-center h-screen">Loading...</div>

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b print:hidden">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/patient/dashboard')} className="text-gray-600 hover:text-gray-900">&larr; Dashboard</button>
            <h1 className="text-xl font-bold text-gray-900">Case Result</h1>
          </div>
          <div className="flex gap-3">
            {!summary?.soap_note && (
              <button
                onClick={handleComplete}
                disabled={completing}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700 disabled:opacity-50"
              >
                {completing ? 'Generating...' : 'Generate SOAP & Complete'}
              </button>
            )}
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
          <PrintableReport summary={summary} />
        ) : (
          <div className="bg-white p-6 rounded-xl shadow-sm text-center">
            <p className="text-gray-600">Click "Generate SOAP & Complete" to finalize this case and generate the clinical summary.</p>
          </div>
        )}
      </main>
    </div>
  )
}
