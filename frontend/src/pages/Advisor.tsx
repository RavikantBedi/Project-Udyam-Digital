import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Mic, MicOff, Send, CheckCircle2, AlertCircle, ArrowRight, Sparkles, User, Bot, HelpCircle } from 'lucide-react'

const API_URL = window.location.protocol + '//' + window.location.hostname + ':8000'

interface Message {
  role: 'bot' | 'user'
  text: string
  action?: string
}

export default function Advisor() {
  const { i18n } = useTranslation()
  const navigate = useNavigate()
  const isHi = i18n.language === 'hi'

  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'bot',
      text: isHi
        ? 'नमस्ते! मैं आपका डिजिटल व्यापार सलाहकार हूँ। आपका व्यवसाय किस प्रकार का है? (जैसे: दुकान/रिटेल, क्लिनिक/ऑफिस, कारखाना/मैन्युफैक्चरिंग, रेस्टोरेंट)'
        : 'Welcome! I am your Accel Business Advisor. What type of business do you run? (e.g. Retail Shop, Clinic/Office, Factory, Restaurant)',
    },
  ])
  const [input, setInput] = useState('')
  const [profile, setProfile] = useState<Record<string, any>>({ lang: i18n.language })
  const [quickReplies, setQuickReplies] = useState<string[]>([
    'Retail Shop / Dukaan',
    'Clinic / Office',
    'Restaurant / Food',
    'Factory / Production',
  ])
  const [recommendation, setRecommendation] = useState<any>(null)
  const [pricing, setPricing] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [mode, setMode] = useState<'ai' | 'offline'>('offline')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (textToSend: string) => {
    if (!textToSend.trim() || loading) return
    const userMsg = textToSend.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', text: userMsg }])
    setLoading(true)

    try {
      const res = await fetch(`${API_URL}/api/advisor/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg,
          profile: { ...profile, lang: i18n.language },
        }),
      })
      const data = await res.json()
      setLoading(false)

      if (data.reply) {
        setMessages((prev) => [...prev, { role: 'bot', text: data.reply, action: data.action }])
      }
      if (data.profile) setProfile(data.profile)
      if (data.quick_replies && data.quick_replies.length > 0) {
        setQuickReplies(data.quick_replies)
      } else {
        setQuickReplies([])
      }
      if (data.recommendation) setRecommendation(data.recommendation)
      if (data.pricing) setPricing(data.pricing)
      if (data.mode) setMode(data.mode)
    } catch (err) {
      setLoading(false)
      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          text: isHi
            ? 'सर्वर से जुड़ने में समस्या हुई। कृपया पुनः प्रयास करें।'
            : 'Could not connect to advisor service. Falling back to offline engine.',
        },
      ])
    }
  }

  // Voice input via browser Web Speech API
  const toggleListening = () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      alert(isHi ? 'आपके ब्राउज़र में आवाज़ इनपुट समर्थित नहीं है।' : 'Speech recognition is not supported in this browser.')
      return
    }

    if (isListening) {
      setIsListening(false)
      return
    }

    try {
      const recognition = new SpeechRecognition()
      recognition.lang = isHi ? 'hi-IN' : 'en-IN'
      recognition.interimResults = false
      recognition.maxAlternatives = 1

      recognition.onstart = () => setIsListening(true)
      recognition.onend = () => setIsListening(false)
      recognition.onerror = () => setIsListening(false)

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript
        if (transcript) {
          setInput(transcript)
          sendMessage(transcript)
        }
      }

      recognition.start()
    } catch {
      setIsListening(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-105px)] max-w-lg mx-auto bg-gray-50 border-x border-gray-200">
      {/* Subheader */}
      <div className="px-4 py-2.5 bg-white border-b border-gray-200 flex items-center justify-between shadow-xs">
        <div>
          <h2 className="font-bold text-gray-900 text-sm flex items-center gap-1.5">
            <Sparkles size={16} className="text-[#E40000]" />
            {isHi ? 'डिजिटल व्यापार सलाहकार' : 'AI Business Advisor'}
          </h2>
          <p className="text-[11px] text-gray-500">
            {isHi ? 'अनुकूली प्रश्न · शून्य तकनीकी भाषा' : '≤ 6 Adaptive Questions · Deterministic Core'}
          </p>
        </div>
        <span
          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
            mode === 'ai'
              ? 'bg-purple-50 text-purple-700 border-purple-200'
              : 'bg-green-50 text-green-700 border-green-200'
          }`}
        >
          {mode === 'ai' ? 'Claude 4.6' : 'Offline Rules Engine'}
        </span>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`flex items-start gap-2.5 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {m.role === 'bot' && (
              <div className="w-7 h-7 rounded-full bg-[#E40000] text-white flex items-center justify-center shrink-0 text-xs font-bold shadow-xs">
                <Bot size={14} />
              </div>
            )}
            <div
              className={`max-w-[82%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap shadow-xs ${
                m.role === 'user'
                  ? 'bg-[#E40000] text-white rounded-br-xs'
                  : 'bg-white border border-gray-200 text-gray-900 rounded-bl-xs'
              }`}
            >
              {m.text}
            </div>
            {m.role === 'user' && (
              <div className="w-7 h-7 rounded-full bg-gray-700 text-white flex items-center justify-center shrink-0 text-xs font-bold shadow-xs">
                <User size={14} />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2 text-xs text-gray-500 italic pl-10">
            <span className="w-2 h-2 rounded-full bg-red-400 animate-ping" />
            {isHi ? 'सलाहकार विचार कर रहा है...' : 'Advisor analyzing options...'}
          </div>
        )}

        {/* Live Recommendation Card */}
        {recommendation && pricing && (
          <div className="bg-white border-2 border-[#E40000] rounded-2xl p-4 shadow-md space-y-3 mt-4">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#E40000] bg-red-50 px-2 py-0.5 rounded-md">
                  {recommendation.segment}
                </span>
                <h3 className="font-extrabold text-gray-900 text-lg mt-1">
                  {recommendation.bundle_name}
                </h3>
              </div>
              <div className="text-right">
                <div className="text-2xl font-black text-gray-900 tracking-tight">
                  ₹{pricing.monthly_total?.toLocaleString('en-IN')}
                </div>
                <div className="text-[11px] text-gray-500">+ 18% GST (₹{pricing.gst?.toLocaleString('en-IN')})</div>
              </div>
            </div>

            {/* Why this fits */}
            {recommendation.why && recommendation.why.length > 0 && (
              <div className="bg-gray-50 rounded-xl p-3 space-y-1 text-xs text-gray-700">
                <div className="font-bold text-gray-900 flex items-center gap-1 mb-1">
                  <CheckCircle2 size={13} className="text-green-600" />
                  {isHi ? 'यह बंडल आपके लिए क्यों सही है:' : 'Why this fits your business:'}
                </div>
                {recommendation.why.map((reason: string, i: number) => (
                  <div key={i} className="flex items-start gap-1.5 text-gray-600">
                    <span className="text-[#E40000] font-bold">•</span>
                    <span>{reason}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Inclusions */}
            <div className="text-xs">
              <span className="font-semibold text-gray-700">{isHi ? 'शामिल उत्पाद:' : 'Included products:'}</span>{' '}
              <span className="text-gray-600">
                {pricing.items?.map((it: any) => it.name).join(' + ')}
              </span>
            </div>

            {/* Excluded items callout if any */}
            {recommendation.excluded && recommendation.excluded.length > 0 && (
              <div className="border border-amber-200 bg-amber-50 rounded-lg p-2 text-xs text-amber-800 flex items-start gap-1.5">
                <AlertCircle size={14} className="shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold">{isHi ? 'अनुपलब्ध विकल्प:' : 'Ineligible products:'} </span>
                  {recommendation.excluded[0].reason}
                </div>
              </div>
            )}

            {/* CTAs */}
            <div className="flex gap-2 pt-1">
              <button
                onClick={() =>
                  navigate('/quote', {
                    state: { bundle: recommendation.bundle, bundle_name: recommendation.bundle_name },
                  })
                }
                className="flex-1 bg-[#E40000] hover:bg-red-700 text-white font-bold py-2.5 px-4 rounded-xl text-sm flex items-center justify-center gap-1.5 shadow-sm transition-colors"
              >
                <span>{isHi ? 'कोटेशन देखें' : 'See Quote'}</span>
                <ArrowRight size={16} />
              </button>
              <button
                onClick={() => sendMessage(isHi ? 'मुझे कुछ बदलना है' : 'I want to change something')}
                className="border border-gray-300 hover:border-gray-400 bg-white text-gray-700 font-medium py-2.5 px-3 rounded-xl text-xs transition-colors"
              >
                {isHi ? 'कुछ बदलें' : 'Change'}
              </button>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Reply Chips */}
      {quickReplies.length > 0 && (
        <div className="px-4 py-2 bg-white border-t border-gray-100 flex gap-2 overflow-x-auto no-scrollbar">
          {quickReplies.map((chip, idx) => (
            <button
              key={idx}
              onClick={() => sendMessage(chip)}
              className="whitespace-nowrap text-xs font-medium px-3 py-1.5 bg-gray-100 hover:bg-red-50 hover:text-[#E40000] hover:border-red-200 border border-gray-200 rounded-full transition-colors shrink-0"
            >
              {chip}
            </button>
          ))}
        </div>
      )}

      {/* Input Bar */}
      <div className="p-3 bg-white border-t border-gray-200 flex items-center gap-2">
        <button
          onClick={toggleListening}
          aria-label="Voice Input"
          className={`p-2.5 rounded-xl border transition-colors ${
            isListening
              ? 'bg-red-600 text-white border-red-600 animate-pulse'
              : 'border-gray-300 text-gray-600 hover:bg-gray-100'
          }`}
        >
          {isListening ? <MicOff size={18} /> : <Mic size={18} />}
        </button>

        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage(input)}
          placeholder={isHi ? 'यहाँ अपना उत्तर लिखें या बोलें...' : 'Type your answer or use microphone...'}
          className="flex-1 border border-gray-300 rounded-xl px-3.5 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#E40000]"
        />

        <button
          onClick={() => sendMessage(input)}
          disabled={!input.trim() || loading}
          aria-label="Send Message"
          className="p-2.5 bg-[#E40000] hover:bg-red-700 disabled:opacity-40 text-white rounded-xl transition-colors shadow-xs"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  )
}
