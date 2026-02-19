import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import api from '../../lib/api'

const LANGUAGES = [
  { code: 'hi', name: 'Hindi' },
  { code: 'bn', name: 'Bengali' },
  { code: 'ta', name: 'Tamil' },
  { code: 'sw', name: 'Swahili' },
  { code: 'es', name: 'Spanish' },
  { code: 'en', name: 'English' },
]

export default function RegisterPatient() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [ageRange, setAgeRange] = useState('')
  const [sex, setSex] = useState('unknown')
  const [language, setLanguage] = useState('en')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!user?.facility_id) return
    setError('')
    setLoading(true)
    try {
      await api.post('/patients/', {
        facility_id: user.facility_id,
        age_range: ageRange || null,
        sex,
        language,
      })
      navigate('/patient/dashboard')
    } catch {
      setError('Failed to register patient')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
          <button onClick={() => navigate('/patient/dashboard')} className="text-gray-600 hover:text-gray-900">&larr; Back</button>
          <h1 className="text-xl font-bold text-gray-900">Register Patient</h1>
        </div>
      </nav>

      <main className="max-w-lg mx-auto px-4 py-8">
        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-xl shadow-sm space-y-6">
          {error && <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{error}</div>}

          <div>
            <label className="block text-sm font-medium text-gray-700">Age Range</label>
            <select value={ageRange} onChange={(e) => setAgeRange(e.target.value)} className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg">
              <option value="">Select...</option>
              <option value="0-10">0-10</option>
              <option value="10-20">10-20</option>
              <option value="20-30">20-30</option>
              <option value="30-40">30-40</option>
              <option value="40-50">40-50</option>
              <option value="50-60">50-60</option>
              <option value="60+">60+</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Sex</label>
            <select value={sex} onChange={(e) => setSex(e.target.value)} className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg">
              <option value="unknown">Prefer not to say</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Primary Language</label>
            <select value={language} onChange={(e) => setLanguage(e.target.value)} className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg">
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.name}</option>
              ))}
            </select>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Registering...' : 'Register Patient'}
          </button>
        </form>
      </main>
    </div>
  )
}
