import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useState, useEffect } from 'react'
import Home from './pages/Home'
import Advisor from './pages/Advisor'
import Quote from './pages/Quote'
import KYC from './pages/KYC'
import Tracker from './pages/Tracker'
import Office from './pages/Office'
import Auth from './pages/Auth'

const STEP_MAP: Record<string, number> = {
  '/advisor': 1,
  '/quote': 2,
  '/kyc': 3,
  '/track': 4,
}

function ProgressStepper() {
  const location = useLocation()
  const step = STEP_MAP[location.pathname] ?? 0
  const steps = [
    { num: 1, label: 'Advise', path: '/advisor' },
    { num: 2, label: 'Quote', path: '/quote' },
    { num: 3, label: 'KYC', path: '/kyc' },
    { num: 4, label: 'Track', path: '/track' },
  ]
  if (step === 0) return null
  return (
    <div className="flex items-center justify-center gap-2 px-4 py-2 bg-gray-50 border-b border-gray-200">
      {steps.map((s, i) => (
        <div key={s.num} className="flex items-center gap-2">
          <Link
            to={s.path}
            className={`text-xs font-semibold px-2.5 py-0.5 rounded-full transition-colors ${
              s.num === step
                ? 'bg-[#E40000] text-white shadow-xs'
                : s.num < step
                ? 'bg-green-600 text-white'
                : 'bg-gray-200 text-gray-500'
            }`}
          >
            {s.num}. {s.label}
          </Link>
          {i < steps.length - 1 && (
            <div className={`h-0.5 w-3 sm:w-6 ${s.num < step ? 'bg-green-600' : 'bg-gray-300'}`} />
          )}
        </div>
      ))}
    </div>
  )
}

export default function App() {
  const { i18n } = useTranslation()
  const isHi = i18n.language === 'hi'
  const [currentUser, setCurrentUser] = useState<any>(null)

  useEffect(() => {
    const raw = localStorage.getItem('auth_user')
    if (raw) {
      try {
        setCurrentUser(JSON.parse(raw))
      } catch (e) {
        console.error(e)
      }
    }
  }, [])

  const logout = () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    setCurrentUser(null)
  }

  return (
    <div className="min-h-screen bg-white text-gray-900 flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-gray-200 px-4 py-3 flex items-center justify-between sticky top-0 bg-white z-20">
        <Link to="/" className="flex items-center gap-2.5 hover:opacity-90">
          <div className="w-8 h-8 bg-[#E40000] rounded-lg flex items-center justify-center text-white font-black text-sm shadow-sm">
            AB
          </div>
          <div>
            <div className="font-bold text-gray-900 tracking-tight leading-none text-base">Accel Business</div>
            <div className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">Udyam Digital</div>
          </div>
        </Link>

        <div className="flex items-center gap-2">
          {currentUser ? (
            <div className="flex items-center gap-1.5 text-xs">
              <span className="font-bold text-gray-800 bg-gray-100 px-2 py-1 rounded-md max-w-[120px] truncate">
                {currentUser.business_name || currentUser.email}
              </span>
              <button
                onClick={logout}
                className="text-gray-400 hover:text-red-600 px-1 font-semibold"
                title="Logout"
              >
                Logout
              </button>
            </div>
          ) : (
            <Link
              to="/auth"
              className="text-xs font-bold text-[#E40000] hover:bg-red-50 border border-red-200 px-2.5 py-1 rounded-lg transition-colors"
            >
              {isHi ? 'साइन इन / खाता' : 'Sign In'}
            </Link>
          )}

          <Link
            to="/office"
            className="text-xs font-semibold text-gray-700 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 px-2.5 py-1 rounded-lg transition-colors border border-gray-200"
          >
            Office
          </Link>

          <select
            value={i18n.language}
            onChange={(e) => i18n.changeLanguage(e.target.value)}
            aria-label="Language Selector"
            className="border border-gray-300 rounded-lg px-2 py-1 text-sm bg-white font-medium focus:outline-none focus:ring-2 focus:ring-[#E40000]"
          >
            <option value="hi">हिंदी</option>
            <option value="en">English</option>
          </select>
        </div>
      </header>

      {/* Progress stepper */}
      <ProgressStepper />

      {/* Page Content */}
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/auth" element={<Auth />} />
          <Route path="/advisor" element={<Advisor />} />
          <Route path="/quote" element={<Quote />} />
          <Route path="/kyc" element={<KYC />} />
          <Route path="/track" element={<Tracker />} />
          <Route path="/office" element={<Office />} />
        </Routes>
      </main>

      {/* Dev footer */}
      <footer className="bg-gray-50 border-t border-gray-200 px-4 py-2 text-xs text-gray-500 text-center flex flex-wrap items-center justify-center gap-3">
        <span className="inline-flex items-center gap-1.5 font-medium text-green-700">
          <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
          Real-Time Omnichannel (Email, SMS & WhatsApp) Active
        </span>
        <span className="text-gray-300">•</span>
        <span>Mock Registries (3,534 GSTIN / 2,723 Udyam)</span>
        <span className="text-gray-300">•</span>
        <span className="font-mono text-gray-600">DEMO_TODAY = 2026-07-15</span>
      </footer>
    </div>
  )
}
