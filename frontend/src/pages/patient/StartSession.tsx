import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import api from '../../lib/api'

interface Patient {
  id: string
  patient_number: string
  age_range: string | null
  sex: string
  language: string
}

export default function StartSession() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [patients, setPatients] = useState<Patient[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (user?.facility_id) {
      api.get(`/patients/?facility_id=${user.facility_id}`)
        .then((res) => setPatients(res.data))
        .catch(() => {})
    }
  }, [user])

  const handleStart = async () => {
    if (!selectedId || !user?.facility_id) return
    setError('')
    setLoading(true)
    try {
      const res = await api.post('/cases/', {
        facility_id: user.facility_id,
        patient_id: selectedId,
      })
      navigate(`/patient/session/${res.data.id}`)
    } catch {
      setError('Failed to start session')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
          <button onClick={() => navigate('/patient/dashboard')} className="text-gray-600 hover:text-gray-900">&larr; Back</button>
          <h1 className="text-xl font-bold text-gray-900">Start Session</h1>
        </div>
      </nav>

      <main className="max-w-lg mx-auto px-4 py-8">
        <div className="bg-white p-6 rounded-xl shadow-sm space-y-6">
          {error && <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{error}</div>}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Select Patient</label>
            {patients.length === 0 ? (
              <p className="text-gray-500 text-sm">No patients registered. <button onClick={() => navigate('/patient/register')} className="text-blue-600 underline">Register one first</button>.</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {patients.map((p) => (
                  <label
                    key={p.id}
                    className={`block p-3 border rounded-lg cursor-pointer ${selectedId === p.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}
                  >
                    <input
                      type="radio"
                      name="patient"
                      value={p.id}
                      checked={selectedId === p.id}
                      onChange={() => setSelectedId(p.id)}
                      className="sr-only"
                    />
                    <div className="font-mono text-sm">{p.patient_number}</div>
                    <div className="text-xs text-gray-500">
                      {p.age_range || 'Age N/A'} &middot; {p.sex} &middot; {p.language.toUpperCase()}
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={handleStart}
            disabled={!selectedId || loading}
            className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Starting...' : 'Start Voice Session'}
          </button>
        </div>
      </main>
    </div>
  )
}
