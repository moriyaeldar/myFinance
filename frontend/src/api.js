import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// ── Analysis ─────────────────────────────────────────────────────────────────
export const fetchAnalysis = (params = {}) => api.get('/analysis', { params }).then(r => r.data)
export const fetchAdvice   = () => api.get('/analysis/advice').then(r => r.data)
export const fetchBillingMonths = () => api.get('/billing-months').then(r => r.data)

// ── Accounts ──────────────────────────────────────────────────────────────────
export const fetchAccounts   = () => api.get('/accounts').then(r => r.data)
export const deleteAccount   = (id) => api.delete(`/accounts/${id}`).then(r => r.data)

// ── Transactions ──────────────────────────────────────────────────────────────
export const fetchTransactions = (params = {}) =>
  api.get('/transactions', { params }).then(r => r.data)

export const recategorize = (id, group, category) =>
  api.patch(`/transactions/${id}/category`, null, { params: { category_group: group, category } })
    .then(r => r.data)

// ── Category settings ─────────────────────────────────────────────────────────
export const fetchCategorySettings = () =>
  api.get('/categories/settings').then(r => r.data)

export const updateCategoryStatus = (group, status) =>
  api.patch(`/categories/${encodeURIComponent(group)}/settings`, { status }).then(r => r.data)

export const updateCategoryBudget = (group, monthly_budget) =>
  api.patch(`/categories/${encodeURIComponent(group)}/settings`, { monthly_budget }).then(r => r.data)

// ── Plaid ─────────────────────────────────────────────────────────────────────
export const fetchLinkToken = () => api.get('/plaid/link-token').then(r => r.data)
export const exchangePlaidToken = (public_token, institution_name) =>
  api.post('/plaid/exchange', { public_token, institution_name }).then(r => r.data)

// ── CSV ───────────────────────────────────────────────────────────────────────
export const importCSV = (file, account_name) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/import/csv', form, {
    params: account_name ? { account_name } : {},
  }).then(r => r.data)
}

