import { useQuery } from '@tanstack/react-query'
import { fetchAdvice } from '../api'
import {
  TrendingUp, TrendingDown, Lightbulb,
  AlertCircle, CheckCircle2, Clock, ArrowRight, RefreshCw,
} from 'lucide-react'
import clsx from 'clsx'
import { useLang } from '../LangContext'

const PRIORITY_CONFIG = {
  high:   { color: 'border-red-300 bg-red-50',    badge: 'bg-red-100 text-red-600',    dot: 'bg-red-500'   },
  medium: { color: 'border-amber-300 bg-amber-50', badge: 'bg-amber-100 text-amber-600', dot: 'bg-amber-500' },
  low:    { color: 'border-blue-200 bg-blue-50',  badge: 'bg-blue-100 text-blue-600',  dot: 'bg-blue-400'  },
}

function fmt(n) {
  return '₪' + new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(Math.abs(n))
}

function ScoreRing({ score, label }) {
  const radius = 42
  const circ = 2 * Math.PI * radius
  const filled = (score / 100) * circ
  const color = score >= 80 ? '#22c55e' : score >= 60 ? '#f59e0b' : '#ef4444'

  return (
    <div className="flex flex-col items-center">
      <svg width="110" height="110" className="-rotate-90">
        <circle cx="55" cy="55" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="10" />
        <circle cx="55" cy="55" r={radius} fill="none" stroke={color} strokeWidth="10"
          strokeDasharray={`${filled} ${circ}`} strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.8s ease' }}
        />
      </svg>
      <div className="-mt-[70px] text-center mb-[20px]">
        <p className="text-3xl font-bold text-slate-800">{score}</p>
        <p className="text-xs text-slate-400">/100</p>
      </div>
      <p className="text-sm font-semibold" style={{ color }}>{label}</p>
    </div>
  )
}

function RecommendationCard({ rec }) {
  const cfg = PRIORITY_CONFIG[rec.priority] || PRIORITY_CONFIG.low
  const { t } = useLang()
  return (
    <div className={clsx('border rounded-xl p-5 fade-in', cfg.color)}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-start gap-3">
          <div className={clsx('w-2 h-2 rounded-full mt-2 shrink-0', cfg.dot)} />
          <div>
            <h3 className="font-semibold text-slate-800">{rec.title}</h3>
            <span className="text-xs text-slate-400">{rec.category}</span>
          </div>
        </div>
        <div className="shrink-0 text-end">
          <p className="text-lg font-bold text-emerald-600">{fmt(rec.estimated_monthly_savings)}</p>
          <p className="text-xs text-slate-400">{t('savings_mo')}</p>
        </div>
      </div>

      <p className="text-sm text-slate-600 mb-3 leading-relaxed">{rec.description}</p>

      <div className="bg-white bg-opacity-60 rounded-lg p-3 flex items-start gap-2">
        <ArrowRight size={14} className="text-slate-500 mt-0.5 shrink-0" />
        <p className="text-xs text-slate-600 font-medium">{rec.action}</p>
      </div>

      <div className="flex items-center justify-between mt-3">
        <span className={clsx('text-xs px-2 py-0.5 rounded-full font-semibold', cfg.badge)}>
          {rec.priority.toUpperCase()} {t('priority_suffix')}
        </span>
        <span className="text-xs text-slate-400">{fmt(rec.estimated_monthly_savings * 12)}{t('per_year_abbr')}</span>
      </div>
    </div>
  )
}

export default function Recommendations() {
  const { t } = useLang()
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['advice'],
    queryFn: fetchAdvice,
    staleTime: 5 * 60_000,
  })

  if (isLoading) return <Loading />

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex gap-3">
          <AlertCircle className="text-red-500 shrink-0 mt-0.5" size={18} />
          <div>
            <p className="text-red-700 font-medium">{t('could_not_generate')}</p>
            <p className="text-red-500 text-sm">{error?.message}</p>
          </div>
        </div>
      </div>
    )
  }

  const recs = data?.recommendations || []
  const highPriority = recs.filter(r => r.priority === 'high')
  const medLow = recs.filter(r => r.priority !== 'high')

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">{t('advice_title')}</h1>
          <p className="text-sm text-slate-400 mt-1">{t('advice_sub')}</p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center gap-2 px-3 py-2 text-sm text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50 transition disabled:opacity-50"
        >
          <RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} />
          {t('btn_refresh')}
        </button>
      </div>

      <div className="bg-white border border-slate-100 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-8">
          <ScoreRing score={data?.health_score || 0} label={data?.health_label || ''} />
          <div className="flex-1">
            <h2 className="font-semibold text-slate-700 mb-2 flex items-center gap-2">
              <Lightbulb size={18} className="text-amber-400" />
              {t('health_summary_title')}
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed">{data?.summary}</p>
            <div className="grid grid-cols-2 gap-4 mt-4">
              <div className="bg-emerald-50 rounded-lg p-3 border border-emerald-100">
                <p className="text-xs text-emerald-600 font-medium">{t('monthly_savings_potential')}</p>
                <p className="text-xl font-bold text-emerald-700 mt-0.5">{fmt(data?.savings_potential_monthly || 0)}</p>
              </div>
              <div className="bg-sky-50 rounded-lg p-3 border border-sky-100">
                <p className="text-xs text-sky-600 font-medium">{t('annual_savings_potential')}</p>
                <p className="text-xl font-bold text-sky-700 mt-0.5">{fmt(data?.savings_potential_annual || 0)}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {highPriority.length > 0 && (
        <div>
          <h2 className="font-semibold text-slate-700 mb-3 flex items-center gap-2">
            <AlertCircle size={16} className="text-red-500" />
            {t('high_priority')}
          </h2>
          <div className="space-y-3">
            {highPriority.map((rec, i) => <RecommendationCard key={i} rec={rec} />)}
          </div>
        </div>
      )}

      {medLow.length > 0 && (
        <div>
          <h2 className="font-semibold text-slate-700 mb-3 flex items-center gap-2">
            <Clock size={16} className="text-amber-500" />
            {t('other_recs')}
          </h2>
          <div className="space-y-3">
            {medLow.map((rec, i) => <RecommendationCard key={i} rec={rec} />)}
          </div>
        </div>
      )}

      {recs.length === 0 && (
        <div className="bg-white border border-slate-100 rounded-xl p-12 text-center text-slate-400 shadow-sm">
          <Lightbulb size={40} className="mx-auto mb-3 opacity-30" />
          <p>{t('no_recs')}</p>
        </div>
      )}
    </div>
  )
}

function Loading() {
  return (
    <div className="p-8 flex flex-col items-center justify-center min-h-64 gap-4">
      <div className="animate-spin rounded-full h-8 w-8 border-2 border-sky-500 border-t-transparent" />
    </div>
  )
}
