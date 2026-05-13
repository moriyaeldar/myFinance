import { useQuery } from '@tanstack/react-query'
import { fetchAnalysis } from '../api'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'
import {
  TrendingUp, TrendingDown, Wallet, CreditCard,
  Scissors, AlertCircle, CheckCircle2,
} from 'lucide-react'
import clsx from 'clsx'
import { Link } from 'react-router-dom'
import { useLang } from '../LangContext'
import { translateCategory } from '../i18n'

const COLORS = [
  '#0ea5e9','#8b5cf6','#f59e0b','#22c55e','#ef4444',
  '#f97316','#06b6d4','#ec4899','#84cc16','#64748b',
]

function StatCard({ label, value, sub, icon: Icon, color = 'sky' }) {
  const colorMap = {
    sky:   'bg-sky-50 text-sky-600 border-sky-100',
    green: 'bg-green-50 text-green-600 border-green-100',
    red:   'bg-red-50 text-red-600 border-red-100',
    amber: 'bg-amber-50 text-amber-600 border-amber-100',
  }
  return (
    <div className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">{label}</p>
          <p className="text-2xl font-bold text-slate-800">{value}</p>
          {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
        </div>
        <div className={clsx('p-2.5 rounded-lg border', colorMap[color])}>
          <Icon size={20} />
        </div>
      </div>
    </div>
  )
}

function fmt(n) {
  if (n == null) return '₪0'
  return '₪' + new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(Math.abs(n))
}

export default function Dashboard() {
  const { t, lang } = useLang()

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-lg text-sm">
        <p className="font-semibold text-slate-700 mb-1">{label}</p>
        {payload.map(p => (
          <p key={p.name} style={{ color: p.color }}>
            {p.name}: {fmt(p.value)}
          </p>
        ))}
      </div>
    )
  }

  const { data, isLoading, error } = useQuery({
    queryKey: ['analysis'],
    queryFn: fetchAnalysis,
  })

  if (isLoading) return <Loading />
  if (error) return <ErrorState error={error} t={t} />

  const { dashboard: d, categories, monthly_trends } = data
  const hasData = d.transactions_count > 0
  const acctLabel = d.accounts_connected === 1 ? t('accounts_connected') : t('accounts_connected_pl')

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">{t('dashboard_title')}</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            {d.accounts_connected} {acctLabel} · {d.transactions_count.toLocaleString()} {t('transactions_total')}
          </p>
        </div>
        {!hasData && (
          <Link to="/connect" className="px-4 py-2 bg-sky-500 text-white rounded-lg text-sm font-medium hover:bg-sky-600 transition">
            {t('btn_connect_bank')}
          </Link>
        )}
      </div>

      {!hasData ? (
        <EmptyState t={t} />
      ) : (
        <>
          <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
            <StatCard label={t('stat_income_mtd')}  value={fmt(d.total_income_mtd)}  icon={TrendingUp}   color="green" />
            <StatCard label={t('stat_expenses_mtd')} value={fmt(d.total_expenses_mtd)} icon={TrendingDown} color="red" />
            <StatCard
              label={t('stat_net')} value={fmt(d.net_mtd)} icon={Wallet}
              color={d.net_mtd >= 0 ? 'green' : 'red'}
              sub={d.net_mtd >= 0 ? t('positive_balance') : t('spending_over_income')}
            />
            <StatCard label={t('stat_savings')} value={fmt(d.savings_potential)} sub={t('from_cut_categories')} icon={Scissors} color="amber" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {monthly_trends.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
                <h2 className="font-semibold text-slate-700 mb-4">{t('chart_income_vs_expenses')}</h2>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={monthly_trends}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `₪${(v/1000).toFixed(0)}k`} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Bar dataKey="income"   name={t('stat_income_mtd').replace(' (MTD)','').replace(' (החודש)','')} fill="#22c55e" radius={[4,4,0,0]} />
                    <Bar dataKey="expenses" name={t('stat_expenses_mtd').replace(' (MTD)','').replace(' (החודש)','')} fill="#ef4444" radius={[4,4,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {categories.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
                <h2 className="font-semibold text-slate-700 mb-4">{t('chart_spending_by_cat')}</h2>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={categories.filter(c => c.total > 0).slice(0, 10).map(c => ({
                        ...c, name: translateCategory(c.category_group, lang),
                      }))}
                      dataKey="total"
                      nameKey="name"
                      cx="50%" cy="50%" outerRadius={80}
                      label={({ name, percentage_of_total }) =>
                        percentage_of_total > 5 ? `${name.split(' ')[0]} ${percentage_of_total.toFixed(0)}%` : ''
                      }
                      labelLine={false}
                    >
                      {categories.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip formatter={(v) => fmt(v)} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {monthly_trends.length > 1 && (
            <div className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
              <h2 className="font-semibold text-slate-700 mb-4">{t('chart_net_savings')}</h2>
              <ResponsiveContainer width="100%" height={160}>
                <AreaChart data={monthly_trends}>
                  <defs>
                    <linearGradient id="netGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `₪${(v/1000).toFixed(1)}k`} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="net" name={t('stat_net')} stroke="#0ea5e9" fill="url(#netGrad)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-slate-700">{t('table_top_categories')}</h2>
              <Link to="/expenses" className="text-sky-500 text-sm hover:underline">{t('manage_link')}</Link>
            </div>
            <div className="space-y-3">
              {categories.filter(c => c.total > 0).slice(0, 8).map((cat, i) => {
                const statusColor = {
                  essential: 'text-emerald-600 bg-emerald-50',
                  optional:  'text-amber-600 bg-amber-50',
                  cut:       'text-red-500 bg-red-50',
                }[cat.status] || 'text-slate-500 bg-slate-100'

                return (
                  <div key={cat.category_group} className="flex items-center gap-3">
                    <span className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0" style={{ background: COLORS[i % COLORS.length] }}>
                      {i + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-sm font-medium text-slate-700 truncate">
                          {translateCategory(cat.category_group, lang)}
                        </span>
                        <span className={clsx('text-xs px-1.5 py-0.5 rounded font-medium', statusColor)}>
                          {cat.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div className="h-full rounded-full" style={{ width: `${cat.percentage_of_total}%`, background: COLORS[i % COLORS.length] }} />
                        </div>
                        <span className="text-xs text-slate-400 w-10 text-right">{cat.percentage_of_total.toFixed(0)}%</span>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-sm font-semibold text-slate-800">{fmt(cat.monthly_avg)}<span className="text-slate-400 font-normal">/mo</span></p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function EmptyState({ t }) {
  return (
    <div className="bg-white rounded-xl border border-slate-100 p-12 text-center shadow-sm">
      <CreditCard className="mx-auto text-slate-300 mb-4" size={48} />
      <h2 className="text-lg font-semibold text-slate-600 mb-2">{t('no_data_title')}</h2>
      <p className="text-slate-400 text-sm mb-6">{t('no_data_sub')}</p>
      <Link to="/connect" className="px-4 py-2 bg-sky-500 text-white rounded-lg text-sm font-medium hover:bg-sky-600 transition">
        {t('btn_connect_bank')}
      </Link>
    </div>
  )
}

function Loading() {
  return (
    <div className="p-8 flex items-center justify-center min-h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-2 border-sky-500 border-t-transparent" />
    </div>
  )
}

function ErrorState({ error, t }) {
  return (
    <div className="p-6">
      <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex gap-3">
        <AlertCircle className="text-red-500 shrink-0 mt-0.5" size={18} />
        <div>
          <p className="text-red-700 font-medium">{t('failed_load')}</p>
          <p className="text-red-500 text-sm">{error?.message || 'Unknown error'}</p>
        </div>
      </div>
    </div>
  )
}
