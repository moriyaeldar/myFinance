import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchTransactions, fetchAnalysis, fetchBillingMonths } from '../api'
import { Search, TrendingUp, TrendingDown } from 'lucide-react'
import clsx from 'clsx'
import { useLang } from '../LangContext'
import { translateCategory } from '../i18n'

const CATEGORY_ICONS = {
  'Income': '💵', 'Housing': '🏠', 'Food & Dining': '🛒',
  'Restaurants & Cafes': '🍽️', 'Communication': '📱', 'Bills & Utilities': '⚡',
  'Insurance': '🛡️', 'Transportation': '🚗', 'Health & Fitness': '🏥',
  'Children & Family': '👶', 'Clothing & Fashion': '👗', 'Home & Garden': '🪴',
  'Shopping': '🛍️', 'Entertainment': '🎬', 'Personal Care': '💆',
  'Pets': '🐾', 'Gifts & Donations': '🎁', 'Education': '📚',
  'Travel': '✈️', 'Loans & Credit': '🏦', 'ATM & Cash': '💴',
  'Savings & Investments': '💰', 'Other': '📦',
}

function fmt(n) {
  return '₪' + new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Math.abs(n))
}

function fmtBillingLabel(bm, lang) {
  const s = new Date(bm.start + 'T00:00:00')
  const e = new Date(bm.end + 'T00:00:00')
  if (lang === 'he') {
    return `${s.getDate()}.${s.getMonth() + 1} – ${e.getDate()}.${e.getMonth() + 1}.${e.getFullYear()}`
  }
  return (
    s.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) +
    ' – ' +
    e.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  )
}

export default function TransactionList() {
  const { t, lang } = useLang()
  const [search, setSearch] = useState('')
  const [groupFilter, setGroupFilter] = useState('')
  const [limit, setLimit] = useState(100)
  const [billingMonth, setBillingMonth] = useState('')

  const fmtDate = (d) => new Date(d).toLocaleDateString(lang === 'he' ? 'he-IL' : 'en-US', { month: 'short', day: 'numeric', year: 'numeric' })

  const { data: billingMonths = [] } = useQuery({ queryKey: ['billing-months'], queryFn: fetchBillingMonths })
  const selectedBM = billingMonths.find(bm => bm.label === billingMonth)

  const { data: analysis } = useQuery({ queryKey: ['analysis'], queryFn: fetchAnalysis })
  const groups = analysis?.categories?.map(c => c.category_group) || []

  const txnParams = {
    category_group: groupFilter || undefined,
    limit,
    ...(selectedBM ? { start_date: selectedBM.start, end_date: selectedBM.end } : {}),
  }

  const { data: transactions = [], isLoading } = useQuery({
    queryKey: ['transactions', groupFilter, limit, billingMonth],
    queryFn: () => fetchTransactions(txnParams),
  })

  const filtered = transactions.filter(t =>
    !search ||
    t.description?.toLowerCase().includes(search.toLowerCase()) ||
    t.merchant_name?.toLowerCase().includes(search.toLowerCase())
  )

  const totalExpenses = filtered.filter(t => t.amount > 0).reduce((s, t) => s + t.amount, 0)
  const totalIncome   = filtered.filter(t => t.amount < 0).reduce((s, t) => s + Math.abs(t.amount), 0)

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-4 fade-in">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">{t('txn_title')}</h1>
        <p className="text-sm text-slate-400 mt-1">
          {filtered.length.toLocaleString()} {t('txn_shown')}
        </p>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        {billingMonths.length > 0 && (
          <select
            value={billingMonth}
            onChange={e => setBillingMonth(e.target.value)}
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-300 bg-white"
          >
            <option value="">{lang === 'he' ? 'כל הזמן' : 'All time'}</option>
            {billingMonths.map(bm => (
              <option key={bm.label} value={bm.label}>{fmtBillingLabel(bm, lang)}</option>
            ))}
          </select>
        )}
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute start-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder={t('search_placeholder')}
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full ps-8 pe-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-300"
          />
        </div>
        <select
          value={groupFilter}
          onChange={e => setGroupFilter(e.target.value)}
          className="border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-300 bg-white"
        >
          <option value="">{t('all_categories')}</option>
          {groups.map(g => (
            <option key={g} value={g}>{CATEGORY_ICONS[g] || '📦'} {translateCategory(g, lang)}</option>
          ))}
        </select>
        <select
          value={limit}
          onChange={e => setLimit(Number(e.target.value))}
          className="border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-300 bg-white"
        >
          {[50, 100, 200, 500].map(n => <option key={n} value={n}>{n}</option>)}
        </select>
      </div>

      {/* Summary */}
      {filtered.length > 0 && (
        <div className="flex gap-4 text-sm">
          <div className="flex items-center gap-1.5 text-red-500">
            <TrendingDown size={14} />
            <span>{t('expenses_label')} <strong>{fmt(totalExpenses)}</strong></span>
          </div>
          <div className="flex items-center gap-1.5 text-emerald-600">
            <TrendingUp size={14} />
            <span>{t('income_label')} <strong>{fmt(totalIncome)}</strong></span>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white border border-slate-100 rounded-xl shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 flex justify-center">
            <div className="animate-spin rounded-full h-6 w-6 border-2 border-sky-500 border-t-transparent" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-slate-400">{t('no_transactions')}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider text-start">{t('col_date')}</th>
                  <th className="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider text-start">{t('col_description')}</th>
                  <th className="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider text-start">{t('col_category')}</th>
                  <th className="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider text-end">{t('col_amount')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {filtered.map((txn) => (
                  <tr key={txn.id} className="hover:bg-slate-50 transition">
                    <td className="px-4 py-3 text-slate-400 whitespace-nowrap">{fmtDate(txn.date)}</td>
                    <td className="px-4 py-3">
                      <p className="text-slate-800 font-medium truncate max-w-xs">{txn.merchant_name || txn.description}</p>
                      {txn.merchant_name && txn.merchant_name !== txn.description && (
                        <p className="text-xs text-slate-400 truncate max-w-xs">{txn.description}</p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1 text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded-lg">
                        {CATEGORY_ICONS[txn.category_group] || '📦'}
                        {translateCategory(txn.category_group, lang)}
                      </span>
                    </td>
                    <td className={clsx('px-4 py-3 font-semibold text-end whitespace-nowrap', txn.amount < 0 ? 'text-emerald-600' : 'text-slate-800')}>
                      {txn.amount < 0 ? '+' : ''}{fmt(txn.amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
