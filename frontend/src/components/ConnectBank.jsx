import { useState, useCallback, useRef } from 'react'
import { usePlaidLink } from 'react-plaid-link'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchLinkToken, exchangePlaidToken,
  fetchAccounts, deleteAccount, importCSV,
} from '../api'
import {
  Building2, Upload, Trash2, CheckCircle2,
  AlertCircle, Loader2, CreditCard, Landmark, BookOpen, CloudUpload,
} from 'lucide-react'
import clsx from 'clsx'
import { useLang } from '../LangContext'

export default function ConnectBank() {
  const { t } = useLang()
  const qc = useQueryClient()
  const [csvFile, setCsvFile] = useState(null)
  const [csvName, setCsvName] = useState('')
  const [csvTab, setCsvTab] = useState('instructions')
  const [dragging, setDragging] = useState(false)
  const fileInputRef = useRef(null)
  const [msg, setMsg] = useState(null)

  const { data: accounts = [] } = useQuery({ queryKey: ['accounts'], queryFn: fetchAccounts })

  const showMsg = (type, text) => { setMsg({ type, text }); setTimeout(() => setMsg(null), 5000) }
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['accounts'] })
    qc.invalidateQueries({ queryKey: ['analysis'] })
  }

  const { data: linkData } = useQuery({
    queryKey: ['plaid-link-token'], queryFn: fetchLinkToken, retry: false, staleTime: Infinity,
  })
  const plaidExchangeMut = useMutation({
    mutationFn: ({ public_token, metadata }) => exchangePlaidToken(public_token, metadata?.institution?.name),
    onSuccess: (data) => { showMsg('success', `Connected! ${data.transactions_added} transactions imported.`); invalidate() },
    onError: (e) => showMsg('error', e?.response?.data?.detail || 'Plaid connection failed.'),
  })
  const onPlaidSuccess = useCallback((public_token, metadata) => plaidExchangeMut.mutate({ public_token, metadata }), [])
  const { open: openPlaid, ready: plaidReady } = usePlaidLink({ token: linkData?.link_token || null, onSuccess: onPlaidSuccess })

  const csvMut = useMutation({
    mutationFn: () => importCSV(csvFile, csvName || undefined),
    onSuccess: (data) => { showMsg('success', `Imported ${data.transactions_added} transactions.`); setCsvFile(null); setCsvName(''); invalidate() },
    onError: (e) => showMsg('error', e?.response?.data?.detail || 'CSV import failed.'),
  })
  const deleteMut = useMutation({
    mutationFn: deleteAccount,
    onSuccess: () => { showMsg('success', 'Account removed.'); invalidate() },
  })

  const BANKS = [
    { name: 'Bank Hapoalim',    steps: 'עו"ש ← ייצוא נתונים ← Excel / CSV' },
    { name: 'Bank Leumi',       steps: 'תנועות חשבון ← ייצוא ← CSV' },
    { name: 'Discount Bank',    steps: 'תנועות ← הורדה ← Excel' },
    { name: 'Mizrahi-Tefahot',  steps: 'דפי חשבון ← ייצוא לאקסל' },
    { name: 'Max (Leumi Card)', steps: 'פירוט עסקאות ← ייצוא ← CSV / Excel' },
    { name: 'Visa Cal',         steps: 'פירוט עסקאות ← הורדה ← Excel' },
    { name: 'Isracard / Amex',  steps: 'פירוט חיובים ← ייצוא ← CSV' },
  ]

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6 fade-in">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">{t('connect_title')}</h1>
        <p className="text-sm text-slate-400 mt-1">{t('connect_sub')}</p>
      </div>

      {msg && (
        <div className={clsx(
          'flex items-start gap-3 p-4 rounded-xl border text-sm',
          msg.type === 'success' ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'
        )}>
          {msg.type === 'success' ? <CheckCircle2 size={18} className="shrink-0 mt-0.5" /> : <AlertCircle size={18} className="shrink-0 mt-0.5" />}
          {msg.text}
        </div>
      )}

      <div className="grid gap-4">
        {/* Plaid */}
        <Card icon={Building2} title={t('plaid_title')} color="sky">
          <p className="text-sm text-slate-500 mb-1">{t('plaid_sub')}</p>
          <p className="text-xs text-slate-400 mb-4">
            {t('plaid_requires')} <code className="bg-slate-100 px-1 rounded">PLAID_CLIENT_ID</code> and{' '}
            <code className="bg-slate-100 px-1 rounded">PLAID_SECRET</code> in your <code>.env</code> file.
          </p>
          <Btn onClick={() => openPlaid()} disabled={!plaidReady || !linkData} loading={plaidExchangeMut.isPending} color="sky">
            {t('btn_connect_bank_acct')}
          </Btn>
          {!linkData && <p className="text-xs text-amber-500 mt-2">{t('plaid_not_configured')}</p>}
        </Card>

        {/* Israeli Bank Import */}
        <Card icon={Upload} title={t('import_title')} color="violet">
          {/* Tabs */}
          <div className="flex gap-1 mb-5 bg-slate-100 rounded-lg p-1">
            {[
              { id: 'instructions', label: t('tab_how_to_export'), icon: BookOpen },
              { id: 'upload',       label: t('tab_upload_file'),   icon: CloudUpload },
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setCsvTab(id)}
                className={clsx(
                  'flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-xs font-medium transition',
                  csvTab === id ? 'bg-white text-violet-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'
                )}
              >
                <Icon size={13} />{label}
              </button>
            ))}
          </div>

          {csvTab === 'instructions' ? (
            <div className="space-y-4 text-sm">
              <p className="text-slate-500">{t('import_instructions_intro')}</p>
              <div className="space-y-3">
                {BANKS.map(({ name, steps }) => (
                  <div key={name} className="flex gap-3 items-start">
                    <span className="shrink-0 w-36 font-medium text-slate-700">{name}</span>
                    <span className="text-slate-500 leading-snug" dir="rtl">{steps}</span>
                  </div>
                ))}
              </div>
              <div className="bg-violet-50 border border-violet-100 rounded-lg px-4 py-3 text-xs text-violet-700 leading-relaxed">
                {t('import_accepted')} <strong>CSV</strong> and <strong>Excel (.xlsx / .xls)</strong>.{' '}
                {t('import_csv_preferred')}
              </div>
              <button onClick={() => setCsvTab('upload')} className="text-xs text-violet-600 hover:text-violet-800 font-medium underline underline-offset-2">
                {t('import_ready')}
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">{t('account_name_label')}</label>
                <input
                  type="text"
                  placeholder={t('account_name_placeholder')}
                  value={csvName}
                  onChange={e => setCsvName(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300"
                />
              </div>
              <div
                onDragOver={e => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={e => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files?.[0]; if (f) setCsvFile(f) }}
                onClick={() => fileInputRef.current?.click()}
                className={clsx(
                  'border-2 border-dashed rounded-xl px-4 py-8 text-center cursor-pointer transition',
                  dragging ? 'border-violet-400 bg-violet-50'
                    : csvFile ? 'border-green-300 bg-green-50'
                    : 'border-slate-200 hover:border-violet-300 hover:bg-violet-50/50'
                )}
              >
                {csvFile ? (
                  <div className="flex flex-col items-center gap-1">
                    <CheckCircle2 size={24} className="text-green-500" />
                    <p className="text-sm font-medium text-slate-700">{csvFile.name}</p>
                    <p className="text-xs text-slate-400">{(csvFile.size / 1024).toFixed(1)} KB</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-1">
                    <CloudUpload size={24} className="text-slate-300" />
                    <p className="text-sm text-slate-500">{t('drop_or_browse')} <span className="text-violet-600 font-medium">{t('drop_browse')}</span></p>
                    <p className="text-xs text-slate-400">{t('drop_formats')}</p>
                  </div>
                )}
                <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls" onChange={e => setCsvFile(e.target.files?.[0] || null)} className="hidden" />
              </div>
              <Btn onClick={() => csvMut.mutate()} disabled={!csvFile} loading={csvMut.isPending} color="violet">
                {t('btn_import')}
              </Btn>
            </div>
          )}
        </Card>
      </div>

      {/* Connected accounts */}
      {accounts.length > 0 && (
        <div>
          <h2 className="font-semibold text-slate-700 mb-3">{t('connected_accounts')}</h2>
          <div className="space-y-2">
            {accounts.map(acct => (
              <div key={acct.id} className="bg-white border border-slate-100 rounded-xl px-4 py-3 flex items-center gap-3 shadow-sm">
                {acct.type === 'credit'
                  ? <CreditCard size={20} className="text-violet-500 shrink-0" />
                  : <Landmark size={20} className="text-sky-500 shrink-0" />
                }
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">{acct.name}</p>
                  <p className="text-xs text-slate-400">
                    {acct.institution || acct.source} · {acct.type}
                    {acct.balance > 0 && ` · ₪${acct.balance.toLocaleString()}`}
                  </p>
                </div>
                <span className={clsx('text-xs px-2 py-0.5 rounded-full font-medium',
                  acct.source === 'plaid' ? 'bg-sky-100 text-sky-600' : 'bg-violet-100 text-violet-600'
                )}>{acct.source}</span>
                <button onClick={() => deleteMut.mutate(acct.id)} className="text-slate-300 hover:text-red-400 transition ms-2">
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function Card({ icon: Icon, title, color, children }) {
  const colorMap = { sky: 'text-sky-500 bg-sky-50', amber: 'text-amber-500 bg-amber-50', violet: 'text-violet-500 bg-violet-50' }
  return (
    <div className="bg-white border border-slate-100 rounded-xl p-5 shadow-sm">
      <div className="flex items-center gap-3 mb-4">
        <div className={clsx('p-2 rounded-lg', colorMap[color])}><Icon size={20} /></div>
        <h2 className="font-semibold text-slate-700">{title}</h2>
      </div>
      {children}
    </div>
  )
}

function Btn({ children, onClick, disabled, loading, color = 'sky', variant = 'solid' }) {
  const solidMap = { sky: 'bg-sky-500 hover:bg-sky-600 text-white', amber: 'bg-amber-500 hover:bg-amber-600 text-white', violet: 'bg-violet-500 hover:bg-violet-600 text-white' }
  const cls = variant === 'ghost' ? 'border border-slate-200 text-slate-600 hover:bg-slate-50' : solidMap[color]
  return (
    <button onClick={onClick} disabled={disabled || loading}
      className={clsx('inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-50 disabled:cursor-not-allowed', cls)}
    >
      {loading && <Loader2 size={14} className="animate-spin" />}
      {children}
    </button>
  )
}
