import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { MessageSquare, FileText, ShieldCheck, Activity, ArrowRight, Zap, Award, UserCheck } from 'lucide-react'

export default function Home() {
  const { i18n } = useTranslation()
  const isHi = i18n.language === 'hi'

  return (
    <div className="px-4 py-8 max-w-lg mx-auto pb-16">
      <div className="inline-flex items-center gap-1.5 bg-red-50 text-[#E40000] border border-red-200 rounded-full px-3 py-1 text-xs font-semibold mb-4">
        <Zap size={14} />
        {isHi ? 'डिजिटल भारत · उद्योग डिजिटल' : 'Track A · Accel YTL Hackathon 2026'}
      </div>

      <div className="mb-6">
        <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight leading-tight mb-2">
          {isHi ? 'एक ही बैठक में अपने व्यवसाय को डिजिटल बनाएं' : 'Make your small business go digital in one sitting'}
        </h1>
        <p className="text-gray-600 text-sm leading-relaxed">
          {isHi
            ? 'अपनी भाषा में सही टेलीकॉम और IT बंडल खोजें, पारदर्शी मूल्य देखें और 15 मिनट में KYC पूरी करें।'
            : 'Find the right telecom and IT bundle in your language, see transparent all-in-one pricing, and complete KYC in minutes.'}
        </p>
      </div>

      <div className="bg-gradient-to-r from-red-50 to-orange-50 border border-red-200 rounded-xl p-3.5 mb-6 text-xs text-gray-700">
        <div className="font-bold text-[#E40000] flex items-center gap-1.5 mb-1 text-sm">
          <Award size={16} />
          {isHi ? 'डेटा अंतर्दृष्टि (smb_leads.csv)' : 'Data Finding (5,000 leads analysis)'}
        </div>
        <div className="flex justify-between items-center text-gray-700 font-medium">
          <span>{isHi ? 'पारंपरिक एक्टिवेशन समय:' : 'Current baseline time:'} <strong className="text-gray-900">17.6 days</strong></span>
          <span>→</span>
          <span>{isHi ? 'उद्यम डिजिटल लक्ष्य:' : 'Target with Udyam:'} <strong className="text-green-700">≤ 5 days</strong></span>
        </div>
        <div className="text-[11px] text-gray-500 mt-1">
          {isHi
            ? '44% ग्राहक क्वोटेशन के बाद ड्रॉप होते हैं — पारदर्शी मूल्य और त्वरित सलाहकार इसे हल करता है।'
            : 'Biggest funnel drop is 44% at quote acceptance — transparent self-serve pricing removes the friction.'}
        </div>
      </div>

      <div className="space-y-3 mb-8">
        <Link
          to="/auth"
          className="group flex items-center gap-3.5 p-4 border border-gray-200 hover:border-[#E40000] rounded-xl bg-white shadow-sm hover:shadow transition-all"
        >
          <div className="w-11 h-11 rounded-lg bg-gray-100 text-gray-800 flex items-center justify-center font-bold">
            <UserCheck size={22} />
          </div>
          <div className="flex-1">
            <div className="font-bold text-gray-900 flex items-center justify-between">
              <span>{isHi ? 'खाता बनाएं / साइन इन करें' : 'Sign Up / Sign In'}</span>
              <ArrowRight size={16} className="text-[#E40000] group-hover:translate-x-1 transition-transform" />
            </div>
            <div className="text-xs text-gray-600 mt-0.5">
              {isHi ? 'ईमेल, SMS और WhatsApp पर रीयल-टाइम अलर्ट प्राप्त करें' : 'Get instant real-time alerts via Email, SMS & WhatsApp'}
            </div>
          </div>
        </Link>

        <Link
          to="/advisor"
          className="group flex items-center gap-3.5 p-4 border-2 border-red-100 hover:border-[#E40000] rounded-xl bg-white shadow-sm hover:shadow transition-all"
        >
          <div className="w-11 h-11 rounded-lg bg-red-100 text-[#E40000] flex items-center justify-center font-bold">
            <MessageSquare size={22} />
          </div>
          <div className="flex-1">
            <div className="font-bold text-gray-900 flex items-center justify-between">
              <span>{isHi ? '1. AI सलाहकार से बात करें' : '1. AI Advisor Chat'}</span>
              <ArrowRight size={16} className="text-[#E40000] group-hover:translate-x-1 transition-transform" />
            </div>
            <div className="text-xs text-gray-600 mt-0.5">
              {isHi ? 'अधिकतम 6 सवालों में सही बंडल खोजें (आवाज़ या टाइप)' : 'Find your bundle in ≤ 6 adaptive questions'}
            </div>
          </div>
        </Link>

        <Link
          to="/quote"
          className="group flex items-center gap-3.5 p-4 border border-gray-200 hover:border-[#E40000] rounded-xl bg-white shadow-sm hover:shadow transition-all"
        >
          <div className="w-11 h-11 rounded-lg bg-gray-100 text-gray-800 flex items-center justify-center font-bold">
            <FileText size={22} />
          </div>
          <div className="flex-1">
            <div className="font-bold text-gray-900 flex items-center justify-between">
              <span>{isHi ? '2. पारदर्शी कोटेशन और चेकआउट' : '2. Quote & Transparent Pricing'}</span>
              <ArrowRight size={16} className="text-gray-400 group-hover:translate-x-1 transition-transform" />
            </div>
            <div className="text-xs text-gray-600 mt-0.5">
              {isHi ? 'कोई छिपा शुल्क नहीं — GST और मासिक बचत साफ़ देखें' : 'One monthly bill with GST, no hidden fees'}
            </div>
          </div>
        </Link>

        <Link
          to="/kyc"
          className="group flex items-center gap-3.5 p-4 border border-gray-200 hover:border-[#E40000] rounded-xl bg-white shadow-sm hover:shadow transition-all"
        >
          <div className="w-11 h-11 rounded-lg bg-gray-100 text-gray-800 flex items-center justify-center font-bold">
            <ShieldCheck size={22} />
          </div>
          <div className="flex-1">
            <div className="font-bold text-gray-900 flex items-center justify-between">
              <span>{isHi ? '3. स्मार्ट डिजिटल KYC' : '3. Smart Lookup KYC'}</span>
              <ArrowRight size={16} className="text-gray-400 group-hover:translate-x-1 transition-transform" />
            </div>
            <div className="text-xs text-gray-600 mt-0.5">
              {isHi ? 'DPDP सहमति, GSTIN ऑटो-फ़ेच, दस्तावेज़ जांच और ई-साइन' : 'DPDP Consent, GSTIN autofill, validation checklist'}
            </div>
          </div>
        </Link>

        <Link
          to="/track"
          className="group flex items-center gap-3.5 p-4 border border-gray-200 hover:border-[#E40000] rounded-xl bg-white shadow-sm hover:shadow transition-all"
        >
          <div className="w-11 h-11 rounded-lg bg-gray-100 text-gray-800 flex items-center justify-center font-bold">
            <Activity size={22} />
          </div>
          <div className="flex-1">
            <div className="font-bold text-gray-900 flex items-center justify-between">
              <span>{isHi ? '4. लाइव एक्टिवेशन ट्रैकर' : '4. Order Tracker'}</span>
              <ArrowRight size={16} className="text-gray-400 group-hover:translate-x-1 transition-transform" />
            </div>
            <div className="text-xs text-gray-600 mt-0.5">
              {isHi ? 'WhatsApp नोटिफिकेशन और वास्तविक समय स्थिति' : 'Real-time milestones, ETAs, WhatsApp feed'}
            </div>
          </div>
        </Link>
      </div>

      <Link
        to="/advisor"
        className="w-full bg-[#E40000] hover:bg-red-700 text-white font-bold py-3.5 px-6 rounded-xl flex items-center justify-center gap-2 shadow-md transition-colors"
      >
        <span>{isHi ? 'अभी शुरू करें — 1 मिनट में' : 'Start Discovery Now'}</span>
        <ArrowRight size={18} />
      </Link>
    </div>
  )
}
