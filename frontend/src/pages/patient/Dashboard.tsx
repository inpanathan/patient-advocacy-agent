import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import api from '../../lib/api'

interface Patient {
  id: string
  patient_number: string
  age_range: string | null
  sex: string
  language: string
}

export default function Dashboard() {
  const { user, logout } = useAuth()
  const [patients, setPatients] = useState<Patient[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (user?.facility_id) {
      api.get(`/patients/?facility_id=${user.facility_id}`)
        .then((res) => setPatients(res.data))
        .catch(() => {})
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [user])

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900">Patient Mode</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">{user?.name}</span>
            <button onClick={logout} className="text-sm text-red-600 hover:text-red-800">Logout</button>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <Link
            to="/patient/register"
            className="p-6 bg-white rounded-xl shadow-sm border-2 border-dashed border-blue-300 hover:border-blue-500 text-center"
          >
            <div className="text-4xl mb-2">+</div>
            <div className="text-lg font-medium text-blue-600">Register New Patient</div>
          </Link>
          <Link
            to="/patient/start"
            className="p-6 bg-blue-600 text-white rounded-xl shadow-sm hover:bg-blue-700 text-center"
          >
            <div className="text-4xl mb-2">&#127897;</div>
            <div className="text-lg font-medium">Start New Session</div>
          </Link>
        </div>

        <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Patients</h2>
        {loading ? (
          <p className="text-gray-500">Loading...</p>
        ) : patients.length === 0 ? (
          <p className="text-gray-500">No patients registered yet.</p>
        ) : (
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Patient #</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Age</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sex</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Language</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {patients.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-mono">{p.patient_number}</td>
                    <td className="px-6 py-4 text-sm">{p.age_range || '-'}</td>
                    <td className="px-6 py-4 text-sm capitalize">{p.sex}</td>
                    <td className="px-6 py-4 text-sm uppercase">{p.language}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
