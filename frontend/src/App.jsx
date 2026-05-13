import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './components/Dashboard'
import ConnectBank from './components/ConnectBank'
import ExpenseGroups from './components/ExpenseGroups'
import Recommendations from './components/Recommendations'
import TransactionList from './components/TransactionList'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard"      element={<Dashboard />} />
        <Route path="connect"        element={<ConnectBank />} />
        <Route path="expenses"       element={<ExpenseGroups />} />
        <Route path="recommendations" element={<Recommendations />} />
        <Route path="transactions"   element={<TransactionList />} />
      </Route>
    </Routes>
  )
}
