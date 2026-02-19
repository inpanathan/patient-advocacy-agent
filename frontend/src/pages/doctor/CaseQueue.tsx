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
  soap_note: { subjective?: string; assessment?: string } | null
  icd_codes: string[] | null
  image_count: number
  created_at: string
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

function chiefComplaint(soap: DoctorCase['soap_note']): string {
  if (!soap?.subjective) return 'No details yet'
  const text = soap.subjective
  // Take first sentence or first 120 chars
  const endIdx = text.search(/[.!?]/)
  const snippet = endIdx > 0 && endIdx < 120 ? text.slice(0, endIdx + 1) : text.slice(0, 120)
  return snippet + (text.length > snippet.length ? '...' : '')
}

export default function CaseQueue() {
  const { user, logout } = useAuth()
  const [cases, setCases] = useState<DoctorCase[]>([])
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState('')

  useEffect(() => {
    setLoading(true)
    const url = filterStatus ? `/doctor/cases?status=${filterStatus}` : '/doctor/cases'
    api.get(url)
      .then((res) => setCases(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [filterStatus])

  const escalatedCases = cases.filter((c) => c.escalated)
  const normalCases = cases.filter((c) => !c.escalated)

  // Stats
  const totalCases = cases.length
  const awaitingReview = cases.filter((c) => c.status === 'awaiting_review').length
  const underReview = cases.filter((c) => c.status === 'under_review').length
  const completed = cases.filter((c) => c.status === 'completed').length
  const escalatedCount = escalatedCases.length

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
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <StatCard label="Total Cases" value={totalCases} color="text-gray-900" />
          <StatCard label="Awaiting Review" value={awaitingReview} color="text-yellow-600" />
          <StatCard label="Under Review" value={underReview} color="text-blue-600" />
          <StatCard label="Completed" value={completed} color="text-green-600" />
          <StatCard label="Escalated" value={escalatedCount} color="text-red-600" />
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 mb-6">
          <span className="text-sm font-medium text-gray-700">Filter:</span>
          {['', 'awaiting_review', 'under_review', 'completed', 'escalated'].map((s) => (
            <button
              key={s}
              onClick={() => setFilterStatus(s)}
              className={`px-3 py-1 rounded-full text-xs font-medium ${filterStatus === s ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
            >
              {s ? s.replace('_', ' ') : 'All'}
            </button>
          ))}
        </div>

        {loading ? (
          <p className="text-gray-500">Loading cases...</p>
        ) : cases.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-400 text-lg">No cases {filterStatus ? `with status "${filterStatus.replace('_', ' ')}"` : 'assigned to you'}.</p>
          </div>
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
                {escalatedCases.length > 0 && (
                  <h2 className="text-sm font-semibold text-gray-700 uppercase mb-3">Cases</h2>
                )}
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

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="bg-white p-4 rounded-xl shadow-sm text-center">
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  )
}

function CaseCard({ caseData }: { caseData: DoctorCase }) {
  return (
    <Link
      to={`/doctor/cases/${caseData.id}`}
      className={`block p-4 bg-white rounded-xl shadow-sm border-l-4 hover:shadow-md transition-shadow ${caseData.escalated ? 'border-red-500' : caseData.status === 'awaiting_review' ? 'border-yellow-400' : caseData.status === 'under_review' ? 'border-blue-400' : 'border-green-400'}`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-sm font-medium">{caseData.case_number}</span>
        <StatusBadge status={caseData.status} escalated={caseData.escalated} />
      </div>

      {/* Chief complaint preview */}
      <p className="text-sm text-gray-600 mb-3 line-clamp-2">
        {chiefComplaint(caseData.soap_note)}
      </p>

      {/* ICD codes */}
      {caseData.icd_codes && caseData.icd_codes.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {caseData.icd_codes.slice(0, 3).map((code) => (
            <span key={code} className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs font-mono">{code}</span>
          ))}
          {caseData.icd_codes.length > 3 && (
            <span className="text-xs text-gray-400">+{caseData.icd_codes.length - 3}</span>
          )}
        </div>
      )}

      {/* Footer: time + image count */}
      <div className="flex items-center justify-between text-xs text-gray-400 pt-2 border-t border-gray-100">
        <span>{timeAgo(caseData.created_at)}</span>
        <div className="flex items-center gap-3">
          {caseData.image_count > 0 && (
            <span>{caseData.image_count} photo{caseData.image_count > 1 ? 's' : ''}</span>
          )}
          {caseData.soap_note ? (
            <span className="text-green-500">SOAP ready</span>
          ) : (
            <span className="text-yellow-500">Pending</span>
          )}
        </div>
      </div>
    </Link>
  )
}
