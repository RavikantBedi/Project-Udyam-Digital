import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { LogIn, UserPlus, Mail, Phone, Lock, Building, CheckCircle2, AlertCircle, ArrowRight } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Auth() {
  const { i18n } = useTranslation()
  const navigate = useNavigate()
  const isHi = i18n.language === 'hi'

  const [isSignup, setIsSignup] = useState(false)
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [businessName, setBusinessName] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    const endpoint = isSignup ? '/api/auth/signup' : '/api/auth/signin'
    const payload = isSignup
      ? { email, phone, business_name: businessName, password }
      : { email, password }

    try {
      const res = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      setLoading(false)

      if (!res.ok) {
        setError(data.detail || 'Authentication failed')
        return
      }

      // Store token & user profile
      localStorage.setItem('auth_token', data.token)
      localStorage.setItem('auth_user', JSON.stringify(data.user))

      setSuccess(
        isSignup
          ? (isHi
              ? 'खाता सफलतापूर्वक बन गया! ईमेल, SMS और WhatsApp पर पुष्टि भेजी गई है।'
              : 'Account created! Welcome alerts dispatched to your Email, SMS & WhatsApp.')
          : (isHi
              ? 'लॉगिन सफल! सुरक्षा अलर्ट आपके ईमेल और SMS पर भेजा गया है।'
              : 'Signed in successfully! Real-time alerts sent to your Email & SMS.')
      )

      setTimeout(() => {
        navigate('/advisor')
      }, 1500)
    } catch {
      setLoading(false)
      setError(isHi ? 'सर्वर से कनेक्ट नहीं हो सका।' : 'Could not reach authentication server')
    }
  }

  return (
    <div className="px-4 py-8 max-w-md mx-auto pb-20">
      <div className="text-center mb-6">
        <div className="w-12 h-12 bg-[#E40000] text-white rounded-2xl flex items-center justify-center font-black text-xl mx-auto shadow-md mb-3">
          AB
        </div>
        <h2 className="text-2xl font-black text-gray-900 tracking-tight">
          {isSignup
            ? (isHi ? 'व्यापार खाता बनाएं (Sign Up)' : 'Register Your Business')
            : (isHi ? 'खाते में प्रवेश करें (Sign In)' : 'Sign In to Udyam Digital')}
        </h2>
        <p className="text-xs text-gray-500 mt-1">
          {isHi
            ? 'साइन इन करते ही ईमेल, SMS और WhatsApp पर रीयल-टाइम अपडेट प्राप्त करें'
            : 'Instant live Email & SMS security alerts, plus real-time WhatsApp order tracking'}
        </p>
      </div>

      <div className="bg-white border border-gray-200 rounded-2xl p-5 shadow-sm space-y-4">
        {/* Toggle between Signin and Signup */}
        <div className="flex border border-gray-200 bg-gray-100 rounded-xl p-1 text-xs font-bold">
          <button
            type="button"
            onClick={() => {
              setIsSignup(false)
              setError('')
              setSuccess('')
            }}
            className={`flex-1 py-2 rounded-lg transition-all ${
              !isSignup ? 'bg-white text-gray-900 shadow-xs' : 'text-gray-500'
            }`}
          >
            {isHi ? 'साइन इन (Sign In)' : 'Sign In'}
          </button>
          <button
            type="button"
            onClick={() => {
              setIsSignup(true)
              setError('')
              setSuccess('')
            }}
            className={`flex-1 py-2 rounded-lg transition-all ${
              isSignup ? 'bg-white text-gray-900 shadow-xs' : 'text-gray-500'
            }`}
          >
            {isHi ? 'नया खाता बनाएं (Sign Up)' : 'Sign Up'}
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-xs p-3 rounded-xl flex items-start gap-2">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className="bg-green-50 border border-green-200 text-green-800 text-xs p-3 rounded-xl flex items-start gap-2">
            <CheckCircle2 size={16} className="shrink-0 mt-0.5 text-green-600" />
            <span>{success}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3.5">
          {isSignup && (
            <>
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">
                  {isHi ? 'व्यवसाय का नाम' : 'Business Name'}
                </label>
                <div className="relative">
                  <Building size={16} className="absolute left-3 top-3 text-gray-400" />
                  <input
                    required
                    type="text"
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                    placeholder="e.g. Sharma Clinic & Diagnostic"
                    className="w-full border border-gray-300 rounded-xl pl-9 pr-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#E40000]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">
                  {isHi ? 'मोबाइल नंबर (SMS और WhatsApp हेतु)' : 'Mobile Phone (for SMS & WhatsApp alerts)'}
                </label>
                <div className="relative">
                  <Phone size={16} className="absolute left-3 top-3 text-gray-400" />
                  <input
                    required
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="9876543210"
                    className="w-full border border-gray-300 rounded-xl pl-9 pr-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#E40000]"
                  />
                </div>
              </div>
            </>
          )}

          <div>
            <label className="block text-xs font-bold text-gray-700 mb-1">
              {isHi ? 'ईमेल पता (अलर्ट और कोटेशन हेतु)' : 'Email Address (for security & billing alerts)'}
            </label>
            <div className="relative">
              <Mail size={16} className="absolute left-3 top-3 text-gray-400" />
              <input
                required
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="owner@mybusiness.com"
                className="w-full border border-gray-300 rounded-xl pl-9 pr-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#E40000]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-700 mb-1">
              {isHi ? 'पासवर्ड' : 'Password'}
            </label>
            <div className="relative">
              <Lock size={16} className="absolute left-3 top-3 text-gray-400" />
              <input
                required
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full border border-gray-300 rounded-xl pl-9 pr-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#E40000]"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#E40000] hover:bg-red-700 disabled:opacity-50 text-white font-bold py-3 px-4 rounded-xl text-sm flex items-center justify-center gap-2 shadow-md transition-colors mt-2"
          >
            {loading ? (
              <span>{isHi ? 'प्रसंस्करण हो रहा है...' : 'Processing...'}</span>
            ) : (
              <>
                <span>{isSignup ? (isHi ? 'खाता बनाएं' : 'Create Account') : (isHi ? 'साइन इन करें' : 'Sign In')}</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>

        {/* Live Notification Indicator Badge */}
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-3 text-[11px] text-gray-600 space-y-1">
          <div className="font-bold text-gray-800 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span>{isHi ? 'रीयल-टाइम मल्टी-चैनल कनेक्टेड:' : 'Real-Time Omnichannel Integration Active:'}</span>
          </div>
          <div>✉️ <strong>Email:</strong> {isHi ? 'सुरक्षा और कोटेशन मेल' : 'Security alerts & official quotes'}</div>
          <div>📱 <strong>SMS:</strong> {isHi ? 'त्वरित OTP और स्थिति संदेश' : 'Instant OTP & milestone updates'}</div>
          <div>💬 <strong>WhatsApp:</strong> {isHi ? 'लाइव एक्टिवेशन और सपोर्ट' : 'Real-time timeline & activation cards'}</div>
        </div>
      </div>
    </div>
  )
}
