import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchAnalysis, fetchBillingMonths, updateCategoryStatus, updateCategoryBudget } from '../api'
import {
  ChevronDown, ChevronUp, Scissors, Shield, HelpCircle,
  CheckCircle2, TrendingDown, PiggyBank, GripVertical,
  Target, Zap, ArrowUp, ArrowDown, Minus,
} from 'lucide-react'
import clsx from 'clsx'
import { useLang } from '../LangContext'
import { translateCategory } from '../i18n'

const CATEGORY_ICONS = {
  'Housing': '🏠', 'Food & Dining': '🍽️', 'Transportation': '🚗',
  'Health & Fitness': '🏋️', 'Bills & Utilities': '⚡', 'Shopping': '🛒',
  'Entertainment': '🎬', 'Personal Care': '💆', 'Education': '📚',
  'Travel': '✈️', 'Savings & Investments': '💰', 'Income': '💵', 'Other': '📦',
}

const STATUS_CONFIG = {
  essential: { label: 'Essential', icon: Shield,      color: 'bg-emerald-500', badge: 'bg-emerald-100 text-emerald-700', desc: 'Must-have expense' },
  optional:  { label: 'Optional',  icon: HelpCircle,  color: 'bg-amber-500',   badge: 'bg-amber-100 text-amber-700',     desc: 'Could reduce if needed' },
  cut:       { label: 'Cut',       icon: Scissors,    color: 'bg-red-500',     badge: 'bg-red-100 text-red-600',         desc: 'Eliminate this expense' },
}

const GOAL_RULES = [
  { id: '502030', label: '50/30/20', needs: 50, wants: 30, savings: 20 },
  { id: '602020', label: '60/20/20', needs: 60, wants: 20, savings: 20 },
  { id: '702010', label: '70/20/10', needs: 70, wants: 20, savings: 10 },
]

function fmt(n) {
  return '₪' + new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(Math.abs(n))
}

// ─── Goals Panel ─────────────────────────────────────────────────────────────

function GoalsPanel({ categories, avgIncome, onApplyBudgets }) {
  const { t } = useLang()
  const [ruleId, setRuleId] = useState('502030')

  const rule = GOAL_RULES.find(r => r.id === ruleId)

  const essential = useMemo(() => categories.filter(c => c.status === 'essential'), [categories])
  const optional  = useMemo(() => categories.filter(c => c.status === 'optional' && c.category_group !== 'Savings & Investments'), [categories])
  const savings   = useMemo(() => categories.filter(c => c.category_group === 'Savings & Investments'), [categories])

  const needsCurrent   = essential.reduce((s, c) => s + c.monthly_avg, 0)
  const wantsCurrent   = optional.reduce((s, c) => s + c.monthly_avg, 0)
  const savingsCurrent = savings.reduce((s, c) => s + c.monthly_avg, 0)

  const base = avgIncome > 0 ? avgIncome : (needsCurrent + wantsCurrent + savingsCurrent) || 1

  const buckets = [
    {
      label: t('goals_needs'), sub: t('goals_needs_sub'),
      current: needsCurrent, target: base * rule.needs / 100,
      pct: rule.needs, cats: essential,
      barColor: 'bg-emerald-400', overColor: 'bg-red-400', textColor: 'text-emerald-600',
      hint: t('goals_hint_needs'),
    },
    {
      label: t('goals_wants'), sub: t('goals_wants_sub'),
      current: wantsCurrent, target: base * rule.wants / 100,
      pct: rule.wants, cats: optional,
      barColor: 'bg-sky-400', overColor: 'bg-red-400', textColor: 'text-sky-600',
      hint: t('goals_hint_wants'),
    },
    {
      label: t('goals_savings'), sub: t('goals_savings_sub'),
      current: savingsCurrent, target: base * rule.savings / 100,
      pct: rule.savings, cats: savings,
      barColor: 'bg-violet-400', overColor: 'bg-orange-400', textColor: 'text-violet-600',
      hint: t('goals_hint_savings'),
    },
  ]

  return (
    <div className="bg-white border border-slate-100 rounded-xl p-5 shadow-sm space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="font-semibold text-slate-700 flex items-center gap-2">
            <Target size={15} className="text-sky-500" />
            {t('goals_title')}
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            {avgIncome > 0
              ? <>{t('goals_income_label')} <span className="font-medium text-slate-600">{fmt(avgIncome)}</span></>
              : t('goals_no_income')}
          </p>
        </div>
        <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
          {GOAL_RULES.map(r => (
            <button
              key={r.id}
              onClick={() => setRuleId(r.id)}
              className={clsx(
                'px-3 py-1 rounded-md text-xs font-medium transition',
                ruleId === r.id ? 'bg-white text-slate-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              )}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Bucket rows */}
      <div className="space-y-5">
        {buckets.map(({ label, sub, current, target, pct, cats, barColor, overColor, textColor, hint }) => {
          const fillPct = target > 0 ? Math.min((current / target) * 100, 120) : 0
          const diff = current - target
          const isOver = diff > 5
          const isUnder = diff < -5

          const catNames = cats.map(c => c.category_group)
          const catLabel = catNames.length === 0 ? null
            : catNames.length <= 2 ? catNames.join(', ')
            : catNames.slice(0, 2).join(', ') + ` +${catNames.length - 2}`

          return (
            <div key={label}>
              <div className="flex items-end justify-between mb-1.5 gap-2 flex-wrap">
                <div>
                  <span className="text-sm font-semibold text-slate-700">{label}</span>
                  <span className="text-xs text-slate-400 ml-1.5">{sub}</span>
                  {catLabel && (
                    <span className="text-xs text-slate-400 ml-2 italic">{catLabel}</span>
                  )}
                </div>
                <div className="text-right text-xs shrink-0">
                  <span className={clsx('font-bold text-sm', isOver ? 'text-red-500' : textColor)}>
                    {fmt(current)}
                  </span>
                  <span className="text-slate-400"> / {fmt(target)}</span>
                  <span className="text-slate-400 ml-1">({pct}%)</span>
                </div>
              </div>

              <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={clsx('h-full rounded-full transition-all duration-500', fillPct > 100 ? overColor : barColor)}
                  style={{ width: `${Math.min(fillPct, 100)}%` }}
                />
              </div>

              <div className="flex items-center justify-between mt-1">
                {cats.length === 0 ? (
                  <span className="text-xs text-slate-300 italic">{hint}</span>
                ) : (
                  <span className="text-xs text-slate-400">{Math.round(fillPct)}{t('goals_of_target')}</span>
                )}
                {cats.length > 0 && (
                  <span className={clsx('text-xs font-medium flex items-center gap-0.5',
                    isOver ? 'text-red-500' : isUnder ? 'text-emerald-600' : 'text-slate-400'
                  )}>
                    {isOver  && <><ArrowUp size={11} /> {fmt(diff)} {t('goals_over')}</>}
                    {isUnder && <><ArrowDown size={11} /> {fmt(Math.abs(diff))} {t('goals_under')}</>}
                    {!isOver && !isUnder && <><Minus size={11} /> {t('goals_on_target')}</>}
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Apply button */}
      <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-4">
        <p className="text-xs text-slate-400">
          {t('goals_apply_desc')}
        </p>
        <button
          onClick={() => onApplyBudgets(rule, { essential, optional, savings }, base)}
          className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 bg-sky-500 hover:bg-sky-600 text-white text-xs font-medium rounded-lg transition"
        >
          <Zap size={12} />
          {t('btn_apply_budgets')}
        </button>
      </div>
    </div>
  )
}

// ─── Status Toggle ────────────────────────────────────────────────────────────

function StatusToggle({ value, onChange }) {
  const { t } = useLang()
  const labels = { essential: t('status_essential'), optional: t('status_optional'), cut: t('status_cut') }
  return (
    <div className="flex items-center rounded-lg border border-slate-200 overflow-hidden text-xs font-medium">
      {['essential', 'optional', 'cut'].map(opt => {
        const cfg = STATUS_CONFIG[opt]
        const active = value === opt
        return (
          <button
            key={opt}
            onClick={() => onChange(opt)}
            className={clsx(
              'px-3 py-1.5 transition flex items-center gap-1',
              active ? `${cfg.color} text-white` : 'bg-white text-slate-500 hover:bg-slate-50'
            )}
          >
            <cfg.icon size={12} />
            {labels[opt]}
          </button>
        )
      })}
    </div>
  )
}

// ─── Category Card ────────────────────────────────────────────────────────────

function CategoryCard({
  cat, settings, onStatusChange, onBudgetChange,
  isDragging, isOver,
  onDragStart, onDragOver, onDrop, onDragEnd,
}) {
  const { t, lang } = useLang()
  const [open, setOpen] = useState(false)
  const [editBudget, setEditBudget] = useState(false)
  const [budgetVal, setBudgetVal] = useState(settings?.monthly_budget || '')

  const status = settings?.status || cat.status || 'optional'
  const cfg = STATUS_CONFIG[status]
  const overBudget = settings?.monthly_budget && cat.monthly_avg > settings.monthly_budget
  const emoji = CATEGORY_ICONS[cat.category_group] || '📦'

  const saveBudget = () => {
    const val = parseFloat(budgetVal)
    if (!isNaN(val) && val > 0) onBudgetChange(val)
    setEditBudget(false)
  }

  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragOver={onDragOver}
      onDrop={onDrop}
      onDragEnd={onDragEnd}
      className={clsx(
        'bg-white border rounded-xl shadow-sm transition-all select-none',
        isDragging && 'opacity-40 shadow-lg scale-[1.01]',
        isOver && !isDragging && 'border-sky-300 shadow-md',
        !isDragging && !isOver && (status === 'cut' ? 'border-red-200 opacity-80' : 'border-slate-100'),
        open && !isDragging && 'shadow-md',
      )}
    >
      {/* Header */}
      <div className="p-4 flex items-center gap-3">
        <GripVertical size={16} className="text-slate-300 cursor-grab shrink-0 active:cursor-grabbing" />
        <span className="text-2xl w-8 text-center shrink-0">{emoji}</span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h3 className={clsx('font-semibold text-slate-800', status === 'cut' && 'line-through text-slate-400')}>
              {translateCategory(cat.category_group, lang)}
            </h3>
            <span className={clsx('text-xs px-2 py-0.5 rounded-full font-medium', cfg.badge)}>
              <cfg.icon size={10} className="inline mr-1" />{cfg.label}
            </span>
            {overBudget && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-600 font-medium">
                {t('over_budget')}
              </span>
            )}
          </div>
          <div className="flex items-center gap-4 text-xs text-slate-400 flex-wrap">
            <span>{fmt(cat.monthly_avg)}{t('mo_avg')}</span>
            <span>{cat.transaction_count} {t('txn_count_unit')}</span>
            <span>{cat.percentage_of_total.toFixed(1)}{t('of_spending')}</span>
            {settings?.monthly_budget && (
              <span className={overBudget ? 'text-red-500' : 'text-emerald-500'}>
                {t('budget_label')} {fmt(settings.monthly_budget)}/mo
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <StatusToggle value={status} onChange={onStatusChange} />
          <button
            onClick={() => setOpen(o => !o)}
            className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 transition"
          >
            {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {/* Expanded details */}
      {open && (
        <div className="border-t border-slate-100 px-4 py-4 space-y-4 fade-in">
          {/* Progress bar */}
          <div>
            <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
              <span>Monthly spend</span>
              <span>{fmt(cat.monthly_avg)}</span>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={clsx('h-full rounded-full transition-all', overBudget ? 'bg-red-400' : 'bg-sky-400')}
                style={{
                  width: settings?.monthly_budget
                    ? `${Math.min((cat.monthly_avg / settings.monthly_budget) * 100, 100)}%`
                    : `${Math.min(cat.percentage_of_total, 100)}%`,
                }}
              />
            </div>
          </div>

          {/* Budget setter */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500 font-medium">{t('monthly_budget_label')}</span>
            {editBudget ? (
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">₪</span>
                <input
                  type="number"
                  value={budgetVal}
                  onChange={e => setBudgetVal(e.target.value)}
                  className="w-24 border border-slate-200 rounded px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-sky-300"
                  placeholder="0"
                  autoFocus
                  onKeyDown={e => e.key === 'Enter' && saveBudget()}
                />
                <button onClick={saveBudget} className="text-sky-500 text-xs hover:underline">{t('save')}</button>
                <button onClick={() => setEditBudget(false)} className="text-slate-400 text-xs hover:underline">{t('cancel')}</button>
              </div>
            ) : (
              <button onClick={() => setEditBudget(true)} className="text-xs text-sky-500 hover:underline">
                {settings?.monthly_budget ? fmt(settings.monthly_budget) + '/mo' : t('set_budget')}
              </button>
            )}
          </div>

          {/* Top merchants */}
          {cat.top_merchants?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-slate-500 mb-2">{t('top_merchants')}</p>
              <div className="flex flex-wrap gap-2">
                {cat.top_merchants.map(m => (
                  <span key={m} className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded-lg">{m}</span>
                ))}
              </div>
            </div>
          )}

          {/* Cut hint */}
          {status === 'cut' && (
            <div className="bg-red-50 border border-red-100 rounded-lg p-3 flex items-start gap-2">
              <TrendingDown size={14} className="text-red-500 mt-0.5 shrink-0" />
              <p className="text-xs text-red-600">
                {t('cutting_saves')}{' '}
                <strong>{fmt(cat.monthly_avg)}{t('per_month')}</strong> ({fmt(cat.monthly_avg * 12)}{t('per_year_abbr')}).
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

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

export default function ExpenseGroups() {
  const { t, lang } = useLang()
  const qc = useQueryClient()
  const [billingMonth, setBillingMonth] = useState('')

  const { data: billingMonths = [] } = useQuery({ queryKey: ['billing-months'], queryFn: fetchBillingMonths })
  const selectedBM = billingMonths.find(bm => bm.label === billingMonth)

  const analysisParams = selectedBM ? { start_date: selectedBM.start, end_date: selectedBM.end } : {}

  const { data, isLoading } = useQuery({
    queryKey: ['analysis', billingMonth || 'all'],
    queryFn: () => fetchAnalysis(analysisParams),
  })

  const statusMut = useMutation({
    mutationFn: ({ group, status }) => updateCategoryStatus(group, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['analysis'] }),
  })

  const budgetMut = useMutation({
    mutationFn: ({ group, budget }) => updateCategoryBudget(group, budget),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['analysis'] }),
  })

  // ── Drag state ──────────────────────────────────────────────────────────────
  const [dragIdx, setDragIdx] = useState(null)
  const [overIdx, setOverIdx] = useState(null)

  // ── Persisted order ────────────────────────────────────────────────────────
  const [savedOrder, setSavedOrder] = useState(() => {
    try { return JSON.parse(localStorage.getItem('eg_order')) || null }
    catch { return null }
  })

  // ── All memos before any early return ─────────────────────────────────────
  const categories = useMemo(() => {
    const raw = (data?.categories || []).filter(c => c.category_group !== 'Income')
    if (!savedOrder) return raw
    const idx = new Map(savedOrder.map((k, i) => [k, i]))
    return [...raw].sort((a, b) =>
      (idx.has(a.category_group) ? idx.get(a.category_group) : 999) -
      (idx.has(b.category_group) ? idx.get(b.category_group) : 999)
    )
  }, [data?.categories, savedOrder])

  const avgIncome = useMemo(() => {
    const months = (data?.monthly_trends || []).filter(m => m.income > 0)
    if (!months.length) return 0
    return months.reduce((s, m) => s + m.income, 0) / months.length
  }, [data?.monthly_trends])

  if (isLoading) return <Loading />

  const settingsMap = Object.fromEntries(
    categories.map(c => [c.category_group, { status: c.status, monthly_budget: c.monthly_budget }])
  )

  const cutCategories = categories.filter(c => c.status === 'cut')
  const savingsMo = cutCategories.reduce((s, c) => s + c.monthly_avg, 0)
  const essentials = categories.filter(c => c.status === 'essential')
  const optionals  = categories.filter(c => c.status === 'optional')

  // ── Drag handlers ──────────────────────────────────────────────────────────
  const handleDragStart = (i) => {
    setDragIdx(i)
  }

  const handleDragOver = (e, i) => {
    e.preventDefault()
    if (dragIdx !== null && dragIdx !== i) setOverIdx(i)
  }

  const handleDrop = (toIdx) => {
    if (dragIdx === null || dragIdx === toIdx) {
      setDragIdx(null); setOverIdx(null); return
    }
    const reordered = [...categories]
    const [moved] = reordered.splice(dragIdx, 1)
    reordered.splice(toIdx, 0, moved)
    const newOrder = reordered.map(c => c.category_group)
    setSavedOrder(newOrder)
    localStorage.setItem('eg_order', JSON.stringify(newOrder))
    setDragIdx(null); setOverIdx(null)
  }

  const handleDragEnd = () => {
    setDragIdx(null); setOverIdx(null)
  }

  // ── Apply Goals budgets ────────────────────────────────────────────────────
  const handleApplyBudgets = (rule, buckets, base) => {
    const distribute = (cats, target) => {
      const total = cats.reduce((s, c) => s + c.monthly_avg, 0) || 1
      cats.forEach(cat => {
        const budget = Math.round((cat.monthly_avg / total) * target)
        if (budget > 0) budgetMut.mutate({ group: cat.category_group, budget })
      })
    }
    distribute(buckets.essential, base * rule.needs / 100)
    distribute(buckets.optional,  base * rule.wants / 100)
    distribute(buckets.savings,   base * rule.savings / 100)
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 fade-in">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">{t('expenses_title')}</h1>
          <p className="text-sm text-slate-400 mt-1">{t('expenses_sub')}</p>
        </div>
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
      </div>

      {/* Goals panel */}
      {categories.length > 0 && (
        <GoalsPanel
          categories={categories}
          avgIncome={avgIncome}
          onApplyBudgets={handleApplyBudgets}
        />
      )}

      {/* Savings potential */}
      {savingsMo > 0 && (
        <div className="bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-xl p-5 flex items-center justify-between shadow-md">
          <div className="flex items-center gap-3">
            <PiggyBank size={28} />
            <div>
              <p className="text-sm opacity-90">{t('savings_potential_sub')}</p>
              <p className="text-2xl font-bold">{fmt(savingsMo)}<span className="text-base font-normal opacity-80">{t('per_month')}</span></p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm opacity-80">{t('per_year')}</p>
            <p className="text-xl font-bold">{fmt(savingsMo * 12)}</p>
          </div>
        </div>
      )}

      {/* Stats row */}
      <div className="flex items-center gap-4 text-sm">
        <div className="flex items-center gap-1.5 text-emerald-600">
          <CheckCircle2 size={15} />
          <span>{essentials.length} {t('n_essential')}</span>
        </div>
        <div className="flex items-center gap-1.5 text-amber-500">
          <HelpCircle size={15} />
          <span>{optionals.length} {t('n_optional')}</span>
        </div>
        <div className="flex items-center gap-1.5 text-red-500">
          <Scissors size={15} />
          <span>{cutCategories.length} {t('n_to_cut')}</span>
        </div>
        <div className="ml-auto text-xs text-slate-400">
          <GripVertical size={13} className="inline mr-1" />{t('drag_hint')}
        </div>
      </div>

      {/* Category list */}
      {categories.length === 0 ? (
        <div className="bg-white border border-slate-100 rounded-xl p-12 text-center text-slate-400">
          {t('no_expense_data')}
        </div>
      ) : (
        <div className="space-y-3">
          {categories.map((cat, i) => (
            <CategoryCard
              key={cat.category_group}
              cat={cat}
              settings={settingsMap[cat.category_group]}
              isDragging={dragIdx === i}
              isOver={overIdx === i && dragIdx !== i}
              onDragStart={() => handleDragStart(i)}
              onDragOver={(e) => handleDragOver(e, i)}
              onDrop={() => handleDrop(i)}
              onDragEnd={handleDragEnd}
              onStatusChange={(status) => statusMut.mutate({ group: cat.category_group, status })}
              onBudgetChange={(budget) => budgetMut.mutate({ group: cat.category_group, budget })}
            />
          ))}
        </div>
      )}
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
