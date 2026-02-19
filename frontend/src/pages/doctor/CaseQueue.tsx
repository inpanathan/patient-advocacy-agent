import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import api from '../../lib/api'
import StatusBadge from '../../components/StatusBadge'

interface DoctorCase {
  id: string
  case_number: string
  patient_id: string
  status: string
  escalated: boolean
  soap_note: unknown
  created_at: string
}

export default function CaseQueue() {
  const { user, logout } = useAuth()
  const [cases, setCases] = useState<DoctorCase[]>([])
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState('')

  useEffect(() => {
    const url = filterStatus ? `/doctor/cases?status=${filterStatus}` : '/doctor/cases'
    api.get(url)
      .then((res) => setCases(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [filterStatus])

  const escalatedCases = cases.filter((c) => c.escalated)
  const normalCases = cases.filter((c) => !c.escalated)

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900">Doctor Dashboard</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">{user?.name}</span>
            <button onClick={logout} className="text-sm text-red-600 hover:text-red-800">Logout</button>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Filters */}
        <div className="flex items-center gap-3 mb-6">
          <span className="text-sm font-medium text-gray-700">Filter:</span>
          {['', 'awaiting_review', 'under_review', 'completed', 'escalated'].map((s) => (
            <button
              key={s}
              onClick={() => { setFilterStatus(s); setLoading(true) }}
              className={`px-3 py-1 rounded-full text-xs font-medium ${filterStatus === s ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
            >
              {s || 'All'}
            </button>
          ))}
        </div>

        {loading ? (
          <p className="text-gray-500">Loading cases...</p>
        ) : cases.length === 0 ? (
          <p className="text-gray-500">No cases assigned to you.</p>
        ) : (
          <div className="space-y-6">
            {/* Escalated cases first */}
            {escalatedCases.length > 0 && (
              <div>
                <h2 className="text-sm font-bold text-red-700 uppercase mb-3">Escalated — Immediate Review Required</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {escalatedCases.map((c) => (
                    <CaseCard key={c.id} caseData={c} />
                  ))}
                </div>
              </div>
            )}

            {/* Normal cases */}
            {normalCases.length > 0 && (
              <div>
                <h2 className="text-sm font-semibold text-gray-700 uppercase mb-3">Cases</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {normalCases.map((c) => (
                    <CaseCard key={c.id} caseData={c} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

function CaseCard({ caseData }: { caseData: DoctorCase }) {
  return (
    <Link
      to={`/doctor/cases/${caseData.id}`}
      className={`block p-4 bg-white rounded-xl shadow-sm border-l-4 hover:shadow-md transition-shadow ${caseData.escalated ? 'border-red-500' : 'border-blue-400'}`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-sm font-medium">{caseData.case_number}</span>
        <StatusBadge status={caseData.status} escalated={caseData.escalated} />
      </div>
      <div className="text-xs text-gray-500">
        {new Date(caseData.created_at).toLocaleDateString()} {new Date(caseData.created_at).toLocaleTimeString()}
      </div>
    </Link>
  )
}
