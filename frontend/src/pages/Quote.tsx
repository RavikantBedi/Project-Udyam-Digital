import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Check, ShieldCheck, ArrowRight, Zap, Info, Plus, Trash2 } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Quote() {
  const { i18n } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const isHi = i18n.language === 'hi'

  // Default to Clinic/Office Pro bundle if not passed
  const initialBundle = location.state?.bundle || ['P02', 'P16', 'P07', 'P20', 'P17']
  const bundleName = location.state?.bundle_name || 'Clinic/Office Pro'

  const [selectedBundle, setSelectedBundle] = useState<string[]>(initialBundle)
  const [contractMonths, setContractMonths] = useState<number>(24)
  const [quoteData, setQuoteData] = useState<any>(null)
  const [loading, setLoading] = useState<boolean>(true)

  const fetchQuote = async (bundle: string[], months: number) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/quote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bundle, contract_months: months }),
      })
      const data = await res.json()
      setQuoteData(data)
    } catch (e) {
      console.error('Quote fetch failed:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchQuote(selectedBundle, contractMonths)
  }, [selectedBundle, contractMonths])

  const toggleProduct = (pid: string) => {
    if (selectedBundle.includes(pid)) {
      if (selectedBundle.length <= 1) return // Keep at least one
      setSelectedBundle(selectedBundle.filter((x) => x !== pid))
    } else {
      setSelectedBundle([...selectedBundle, pid])
    }
  }

  return (
    <div className="px-4 py-6 max-w-lg mx-auto pb-20">
      {/* Title */}
      <div className="mb-5">
        <h2 className="text-2xl font-black text-gray-900 tracking-tight">
          {isHi ? 'पारदर्शी कोटेशन और चेकआउट' : 'Quote & Checkout'}
        </h2>
        <p className="text-xs text-gray-500 mt-0.5">
          {isHi ? 'एक बिल · कोई छिपा शुल्क नहीं · नियत अनुबंध दर' : 'One monthly bill · Zero hidden fees · Deterministic pricing'}
        </p>
      </div>

      {/* Bundle Header Card */}
      <div className="bg-gradient-to-r from-red-600 to-red-700 text-white rounded-2xl p-4.5 mb-5 shadow-sm">
        <div className="flex justify-between items-start">
          <div>
            <div className="text-xs uppercase tracking-wider text-red-200 font-bold">
              {isHi ? 'अनुशंसित बंडल' : 'Selected Bundle'}
            </div>
            <h3 className="text-xl font-black mt-0.5">{bundleName}</h3>
          </div>
          <div className="text-right">
            <div className="text-2xl font-black tracking-tight">
              ₹{quoteData?.monthly_total?.toLocaleString('en-IN') || '---'}
            </div>
            <div className="text-xs text-red-100">{isHi ? 'प्रति माह + GST' : '/month + GST'}</div>
          </div>
        </div>
      </div>

      {/* Contract Duration Selector */}
      <div className="bg-white border border-gray-200 rounded-xl p-4 mb-4 shadow-xs">
        <label className="block text-xs font-bold text-gray-900 uppercase tracking-wider mb-2">
          {isHi ? 'अनुबंध अवधि (महीने)' : 'Contract Duration'}
        </label>
        <div className="grid grid-cols-3 gap-2">
          {[
            { m: 12, label: '12 mos', tag: 'Standard' },
            { m: 24, label: '24 mos', tag: 'Best value' },
            { m: 36, label: '36 mos', tag: 'Lowest rate' },
          ].map((item) => (
            <button
              key={item.m}
              onClick={() => setContractMonths(item.m)}
              className={`py-2 px-3 rounded-xl border text-center transition-all ${
                contractMonths === item.m
                  ? 'border-[#E40000] bg-red-50 text-[#E40000] font-bold shadow-xs'
                  : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50'
              }`}
            >
              <div className="text-sm font-extrabold">{item.label}</div>
              <div className="text-[10px] text-gray-500 mt-0.5">{item.tag}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Line Items */}
      <div className="bg-white border border-gray-200 rounded-xl p-4 mb-4 shadow-xs space-y-3">
        <div className="text-xs font-bold text-gray-900 uppercase tracking-wider">
          {isHi ? 'बंडल में शामिल सेवाएँ' : 'Line Items'}
        </div>
        <div className="divide-y divide-gray-100">
          {quoteData?.items?.map((item: any) => (
            <div key={item.product_id} className="py-2.5 flex items-center justify-between text-sm">
              <div>
                <div className="font-semibold text-gray-900 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#E40000]" />
                  {item.name}
                </div>
                <div className="text-[11px] text-gray-500">
                  {item.category} · {item.install_days}d install SLA
                </div>
              </div>
              <div className="text-right">
                <div className="font-bold text-gray-900">₹{item.monthly?.toLocaleString('en-IN')}/mo</div>
                {item.setup > 0 && (
                  <div className="text-[10px] text-gray-500">Setup: ₹{item.setup}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Bill Breakdown */}
      {quoteData && (
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 mb-6 space-y-2.5 text-sm">
          <div className="flex justify-between text-gray-600">
            <span>{isHi ? 'मासिक शुल्क (बिना कर)' : 'Monthly Recurring Charge'}</span>
            <span className="font-semibold text-gray-900">₹{quoteData.monthly_total?.toLocaleString('en-IN')}</span>
          </div>
          <div className="flex justify-between text-gray-600">
            <span>{isHi ? 'GST (18%)' : 'GST (18%)'}</span>
            <span className="font-semibold text-gray-900">₹{quoteData.gst?.toLocaleString('en-IN')}</span>
          </div>
          <div className="flex justify-between text-gray-600">
            <span>{isHi ? 'एकमुश्त सेटअप शुल्क' : 'One-time Setup Fee'}</span>
            <span className="font-semibold text-gray-900">₹{quoteData.one_time_total?.toLocaleString('en-IN')}</span>
          </div>

          <div className="border-t border-gray-300 pt-2 flex justify-between font-bold text-base text-gray-900">
            <span>{isHi ? 'पहले बिल का अनुमान' : 'First Bill Estimate'}</span>
            <span className="text-[#E40000]">₹{quoteData.first_bill_estimate?.toLocaleString('en-IN')}</span>
          </div>

          {quoteData.bundle_saving > 0 && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-2 text-xs font-semibold text-green-800 flex items-center gap-1.5 mt-2">
              <Check size={14} className="text-green-600 shrink-0" />
              <span>
                {isHi
                  ? `बंडल बचत: अलग-अलग लेने की तुलना में ₹${quoteData.bundle_saving?.toLocaleString('en-IN')} प्रति माह की बचत`
                  : `Bundle saving: ₹${quoteData.bundle_saving?.toLocaleString('en-IN')}/month vs individual products`}
              </span>
            </div>
          )}
        </div>
      )}

      {/* CTA Button */}
      <button
        onClick={() =>
          navigate('/kyc', {
            state: {
              bundle: selectedBundle,
              monthly_total: quoteData?.monthly_total,
              one_time_total: quoteData?.one_time_total,
            },
          })
        }
        className="w-full bg-[#E40000] hover:bg-red-700 text-white font-bold py-3.5 px-6 rounded-xl flex items-center justify-center gap-2 shadow-md transition-colors"
      >
        <span>{isHi ? 'KYC सत्यापन के लिए आगे बढ़ें' : 'Proceed to Smart KYC'}</span>
        <ArrowRight size={18} />
      </button>
    </div>
  )
}
