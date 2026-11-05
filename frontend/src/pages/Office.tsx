import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Users,
  TrendingUp,
  Clock,
  DollarSign,
  PhoneCall,
  UserCheck,
  CheckCircle2,
  RefreshCw,
  Award,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Office() {
  const queryClient = useQueryClient()
  const [role, setRole] = useState<'sales' | 'partner'>('sales')
  const [assignedStatus, setAssignedStatus] = useState<Record<string, string>>({})

  // Fetch leads
  const { data: leads, isLoading: leadsLoading } = useQuery({
    queryKey: ['officeLeads'],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/api/office/leads`)
      return res.json()
    },
  })

  // Fetch metrics
  const { data: metrics } = useQuery({
    queryKey: ['officeMetrics'],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/api/office/metrics`)
      return res.json()
    },
  })

  // Retrain model mutation
  const retrainMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_URL}/api/office/model/retrain`, { method: 'POST' })
      return res.json()
    },
    onSuccess: (data) => {
      alert(`Model retrained successfully! AUC: ${data.auc} on ${data.samples} historical leads.`)
      queryClient.invalidateQueries({ queryKey: ['officeLeads'] })
    },
  })

  const assignLead = async (leadId: string, assignee: string, type: 'field' | 'partner') => {
    try {
      await fetch(`${API_URL}/api/office/leads/${leadId}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assignee, type }),
      })
      setAssignedStatus((prev) => ({
        ...prev,
        [leadId]: `Assigned to ${type === 'partner' ? 'Channel Partner' : 'Field Sales'} (${assignee}) · Commission Preserved`,
      }))
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div className="px-4 py-6 max-w-5xl mx-auto pb-20 space-y-6">
      {/* Top Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-black text-gray-900 tracking-tight flex items-center gap-2">
            <Users className="text-[#E40000]" size={26} />
            Back Office & Partner Portal
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Assisted-Digital Handoff · Gradient Boosted Propensity Scoring · DPDP Aligned
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Role switcher */}
          <div className="flex border border-gray-200 rounded-lg overflow-hidden bg-gray-100 p-0.5 text-xs font-semibold">
            <button
              onClick={() => setRole('sales')}
              className={`px-3 py-1 rounded-md transition-colors ${
                role === 'sales' ? 'bg-white text-gray-900 shadow-xs' : 'text-gray-500'
              }`}
            >
              Sales Exec
            </button>
            <button
              onClick={() => setRole('partner')}
              className={`px-3 py-1 rounded-md transition-colors ${
                role === 'partner' ? 'bg-white text-gray-900 shadow-xs' : 'text-gray-500'
              }`}
            >
              Channel Partner
            </button>
          </div>

          <button
            onClick={() => retrainMutation.mutate()}
            disabled={retrainMutation.isPending}
            className="inline-flex items-center gap-1.5 bg-gray-900 hover:bg-black text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-xs transition-colors"
          >
            <RefreshCw size={13} className={retrainMutation.isPending ? 'animate-spin' : ''} />
            <span>Retrain Model</span>
          </button>
        </div>
      </div>

      {/* 5 Key Metrics Cards (Baseline vs Target) */}
      {metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <div className="bg-white border border-gray-200 rounded-xl p-3.5 shadow-xs">
            <div className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">Lead → Activation</div>
            <div className="text-xl font-black text-gray-900 mt-1">
              {metrics.baseline.lead_to_activation}% <span className="text-green-600 text-sm font-bold">→ {metrics.target.lead_to_activation}%</span>
            </div>
            <div className="text-[10px] text-gray-400 mt-0.5">Target: 15%+ on digital</div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-3.5 shadow-xs">
            <div className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">Time to Activate</div>
            <div className="text-xl font-black text-gray-900 mt-1">
              {metrics.baseline.time_to_activate_days}d <span className="text-green-600 text-sm font-bold">→ ≤ {metrics.target.time_to_activate_days}d</span>
            </div>
            <div className="text-[10px] text-gray-400 mt-0.5">Digital steps: ≤ 15 min</div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-3.5 shadow-xs">
            <div className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">Acquisition Cost (CAC)</div>
            <div className="text-xl font-black text-gray-900 mt-1">
              ₹15k <span className="text-green-600 text-sm font-bold">→ ≤ ₹8k</span>
            </div>
            <div className="text-[10px] text-gray-400 mt-0.5">Referral CAC: ₹4.1k</div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-3.5 shadow-xs">
            <div className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">Status Chase Calls</div>
            <div className="text-xl font-black text-gray-900 mt-1">
              3 calls <span className="text-green-600 text-sm font-bold">→ ≤ 1 call</span>
            </div>
            <div className="text-[10px] text-gray-400 mt-0.5">Retains high customer NPS</div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-3.5 shadow-xs">
            <div className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">6-Month Churn</div>
            <div className="text-xl font-black text-gray-900 mt-1">
              15.0% <span className="text-green-600 text-sm font-bold">→ ≤ 12.0%</span>
            </div>
            <div className="text-[10px] text-gray-400 mt-0.5">Micro: 22.7% → ≤15%</div>
          </div>
        </div>
      )}

      {/* Funnel Overview */}
      {metrics?.funnel && (
        <div className="bg-white border border-gray-200 rounded-2xl p-4.5 shadow-xs">
          <div className="text-xs font-bold text-gray-900 uppercase tracking-wider mb-3">
            Synthetic Dataset Conversion Funnel (5,000 SMB Leads)
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 text-center text-xs">
            {metrics.funnel.map((stage: any, i: number) => (
              <div key={i} className="bg-gray-50 rounded-xl p-2.5 border border-gray-100">
                <div className="text-gray-500 font-semibold">{stage.stage}</div>
                <div className="text-base font-black text-gray-900 mt-0.5">
                  {stage.count.toLocaleString()}
                </div>
                {i > 0 && (
                  <div className="text-[10px] text-gray-400 mt-0.5">
                    {Math.round((stage.count / metrics.funnel[i - 1].count) * 100)}% conv
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Lead Queue */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-extrabold text-gray-900 text-lg">
              Needs a Human — Unclosed Lead Queue
            </h3>
            <p className="text-xs text-gray-500">
              Ranked by Gradient Boosting Propensity Score (language & state excluded per DPDP)
            </p>
          </div>
          <span className="text-xs font-bold text-[#E40000] bg-red-50 border border-red-200 px-2.5 py-1 rounded-full">
            Top 50 Qualified
          </span>
        </div>

        {leadsLoading && (
          <div className="text-xs text-gray-500 p-8 text-center italic">Loading ranked leads...</div>
        )}

        <div className="space-y-3">
          {leads?.map((lead: any) => (
            <div
              key={lead.lead_id}
              className="bg-white border border-gray-200 hover:border-gray-300 rounded-2xl p-4 shadow-xs transition-all space-y-3"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-gray-900 text-base">{lead.business_name}</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-gray-100 text-gray-700">
                      {lead.segment}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {lead.city} · Preferred Language: <strong className="text-gray-700">{lead.language}</strong> · Drop Stage: {lead.stage}
                  </div>
                </div>

                <div className="text-right">
                  <div className="inline-flex items-baseline gap-1">
                    <span className="text-2xl font-black text-[#E40000]">{lead.propensity_score}</span>
                    <span className="text-xs font-bold text-gray-400">/100</span>
                  </div>
                  <div className="text-[10px] font-semibold text-gray-500">Propensity Score</div>
                </div>
              </div>

              {/* Reasons */}
              <div className="bg-gray-50 rounded-xl p-2.5 text-xs space-y-1">
                <div className="font-bold text-gray-700">Top Propensity Factors:</div>
                <div className="flex flex-wrap gap-1.5">
                  {lead.reasons?.map((r: string, i: number) => (
                    <span key={i} className="bg-white border border-gray-200 text-gray-700 px-2 py-0.5 rounded-md text-[11px]">
                      ✓ {r}
                    </span>
                  ))}
                </div>
              </div>

              {/* Suggested Action Script */}
              <div className="text-xs text-gray-700 bg-amber-50/60 border border-amber-200/80 rounded-xl p-2.5 flex items-start gap-2">
                <PhoneCall size={14} className="text-amber-700 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-amber-900">Suggested Action ({lead.language}): </strong>
                  {lead.suggested_action}
                </div>
              </div>

              {/* Action Buttons */}
              {assignedStatus[lead.lead_id] ? (
                <div className="bg-green-50 text-green-800 border border-green-200 rounded-xl p-2 text-xs font-semibold flex items-center gap-2">
                  <CheckCircle2 size={16} />
                  <span>{assignedStatus[lead.lead_id]}</span>
                </div>
              ) : (
                <div className="flex gap-2 pt-1">
                  <button
                    onClick={() => assignLead(lead.lead_id, 'Rajesh Kumar (Field)', 'field')}
                    className="flex-1 bg-[#E40000] hover:bg-red-700 text-white font-bold py-2 px-3 rounded-xl text-xs transition-colors shadow-xs"
                  >
                    Assign to Field Sales
                  </button>
                  <button
                    onClick={() => assignLead(lead.lead_id, 'CityNet Solutions (Partner)', 'partner')}
                    className="flex-1 border border-gray-300 hover:bg-gray-50 text-gray-800 font-bold py-2 px-3 rounded-xl text-xs transition-colors"
                  >
                    Assign to Channel Partner
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
