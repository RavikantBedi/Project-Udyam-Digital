import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  CheckCircle2,
  Clock,
  MessageSquare,
  FastForward,
  Mail,
  Smartphone,
  Send,
  ShieldCheck,
  Bell,
  RefreshCw
} from 'lucide-react'

const API_URL = window.location.protocol + '//' + window.location.hostname + ':8000'

export default function Tracker() {
  const { i18n } = useTranslation()
  const location = useLocation()
  const isHi = i18n.language === 'hi'

  const orderId = location.state?.order_id || 'ORD-DEMO0001'
  const [trackData, setTrackData] = useState<any>(null)
  const [liveLogs, setLiveLogs] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState<'whatsapp' | 'sms' | 'email'>('whatsapp')
  const [loading, setLoading] = useState(true)

  const fetchTrack = async () => {
    try {
      const res = await fetch(`${API_URL}/api/orders/${orderId}/track`)
      const data = await res.json()
      setTrackData(data)
    } catch (e) {
      console.error(e)
    }
  }

  const fetchLiveNotifications = async () => {
    try {
      const res = await fetch(`${API_URL}/api/notifications/live?limit=20`)
      const data = await res.json()
      if (Array.isArray(data)) {
        setLiveLogs(data)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTrack()
    fetchLiveNotifications()
    const timer = setInterval(() => {
      fetchTrack()
      fetchLiveNotifications()
    }, 4000)
    return () => clearInterval(timer)
  }, [orderId])

  const advanceTime = async () => {
    try {
      await fetch(`${API_URL}/api/demo/advance-time`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_id: orderId }),
      })
      fetchTrack()
      fetchLiveNotifications()
    } catch (e) {
      console.error(e)
    }
  }

  const filteredLogs = liveLogs.filter((l) => l.channel === activeTab)

  return (
    <div className="px-4 py-6 max-w-lg mx-auto pb-24 space-y-5">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-2xl font-black text-gray-900 tracking-tight">
            {isHi ? 'ऑर्डर और एक्टिवेशन ट्रैकर' : 'Activation Tracker'}
          </h2>
          <div className="text-xs text-gray-500 font-mono mt-0.5">Order ID: {orderId}</div>
        </div>
        <span className="text-[10px] font-bold px-2.5 py-1 bg-green-50 text-green-700 border border-green-200 rounded-full">
          {trackData?.order?.status || 'Active'}
        </span>
      </div>

      {/* SLA Metric Card */}
      <div className="bg-gradient-to-r from-red-50 to-orange-50 border border-red-200 rounded-2xl p-4 shadow-xs">
        <div className="flex justify-between items-center text-xs">
          <div>
            <div className="font-bold text-[#E40000] uppercase tracking-wider text-[10px]">
              {isHi ? 'एक्टिवेशन समय बचत' : 'Time-to-Activate SLA'}
            </div>
            <div className="font-extrabold text-gray-900 text-sm mt-0.5">
              {isHi ? 'अनुमानित: ≤ 5 दिन' : 'Estimated: ≤ 5 days'}
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] text-gray-500">{isHi ? 'पारंपरिक उद्योग औसत:' : 'Baseline industry average:'}</div>
            <div className="font-extrabold text-gray-500 line-through text-sm">17.6 days</div>
          </div>
        </div>
      </div>

      {/* Milestones Stepper */}
      <div className="bg-white border border-gray-200 rounded-2xl p-4.5 shadow-sm">
        <div className="text-xs font-bold text-gray-900 uppercase tracking-wider mb-4">
          {isHi ? 'सक्रियण चरण' : 'Activation Milestones'}
        </div>
        <div className="space-y-4 relative before:absolute before:left-3.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-gray-200">
          {trackData?.timeline?.map((step: any, idx: number) => (
            <div key={idx} className="flex items-start gap-3 relative z-10">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs shrink-0 ${
                  step.done
                    ? 'bg-green-600 text-white shadow-xs'
                    : 'bg-white border-2 border-gray-300 text-gray-400'
                }`}
              >
                {step.done ? <CheckCircle2 size={16} /> : idx + 1}
              </div>
              <div className="flex-1">
                <div className="flex justify-between items-baseline">
                  <div className={`text-sm font-bold ${step.done ? 'text-gray-900' : 'text-gray-500'}`}>
                    {step.status}
                  </div>
                  <div
                    className={`text-[11px] font-semibold ${
                      step.done ? 'text-green-700' : 'text-gray-400'
                    }`}
                  >
                    {step.eta}
                  </div>
                </div>
                <div className="text-xs text-gray-500 mt-0.5">{step.message}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Real-time Omnichannel Live Feed: WhatsApp, SMS, Email */}
      <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-bold text-gray-900 uppercase tracking-wider">
            <Bell size={16} className="text-[#E40000]" />
            <span>{isHi ? 'रीयल-टाइम अपडेट स्ट्रीम' : 'Live Notification Feed'}</span>
          </div>
          <span className="flex items-center gap-1 text-[10px] text-green-700 font-bold bg-green-50 px-2 py-0.5 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            Live Auto-Sync
          </span>
        </div>

        {/* Tab switcher: WhatsApp / SMS / Email */}
        <div className="flex border border-gray-200 bg-gray-100 rounded-xl p-1 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('whatsapp')}
            className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
              activeTab === 'whatsapp' ? 'bg-white text-green-700 font-bold shadow-xs' : 'text-gray-500'
            }`}
          >
            <MessageSquare size={13} />
            <span>WhatsApp</span>
          </button>
          <button
            onClick={() => setActiveTab('sms')}
            className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
              activeTab === 'sms' ? 'bg-white text-blue-700 font-bold shadow-xs' : 'text-gray-500'
            }`}
          >
            <Smartphone size={13} />
            <span>SMS</span>
          </button>
          <button
            onClick={() => setActiveTab('email')}
            className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
              activeTab === 'email' ? 'bg-white text-purple-700 font-bold shadow-xs' : 'text-gray-500'
            }`}
          >
            <Mail size={13} />
            <span>Email</span>
          </button>
        </div>

        {/* Feed List */}
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {filteredLogs.length > 0 ? (
            filteredLogs.map((log: any) => (
              <div
                key={log.id}
                className={`p-3 rounded-xl border text-xs leading-relaxed space-y-1 ${
                  activeTab === 'whatsapp'
                    ? 'bg-emerald-50/70 border-emerald-200 text-emerald-950'
                    : activeTab === 'sms'
                    ? 'bg-blue-50/70 border-blue-200 text-blue-950'
                    : 'bg-purple-50/70 border-purple-200 text-purple-950'
                }`}
              >
                {log.subject && (
                  <div className="font-bold text-gray-900 border-b border-gray-200/50 pb-1 mb-1">
                    {log.subject}
                  </div>
                )}
                <div
                  className="whitespace-pre-line"
                  dangerouslySetInnerHTML={{
                    __html: log.message.replace(/\n/g, '<br/>'),
                  }}
                />
                <div className="flex justify-between items-center text-[10px] text-gray-500 pt-1 border-t border-gray-200/40">
                  <span>To: {log.recipient}</span>
                  <span>{new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-6 text-xs text-gray-400 italic">
              {isHi
                ? 'अभी इस चैनल पर कोई संदेश नहीं है। नीचे "Advance State" दबाएं।'
                : 'No messages on this channel yet. Advance state below to trigger notifications.'}
            </div>
          )}
        </div>
      </div>

      {/* Demo State Control */}
      <div className="border border-gray-200 bg-gray-50 rounded-xl p-3.5 text-xs flex items-center justify-between shadow-xs">
        <div>
          <div className="font-bold text-gray-900">
            {isHi ? 'डेमो समय और लाइफसाइकिल नियंत्रण:' : 'Simulate Order Lifecycle:'}
          </div>
          <div className="text-[11px] text-gray-500">
            {isHi ? 'अगले चरण पर जाएँ और रीयल-टाइम अपडेट देखें' : 'Advance to next milestone & dispatch alerts'}
          </div>
        </div>
        <button
          onClick={advanceTime}
          className="inline-flex items-center gap-1.5 bg-[#E40000] hover:bg-red-700 text-white font-bold py-2 px-3.5 rounded-xl text-xs transition-colors shadow-xs"
        >
          <FastForward size={14} />
          <span>Advance State</span>
        </button>
      </div>
    </div>
  )
}
