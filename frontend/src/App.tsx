import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { CurrentEmployeeProvider } from './context/CurrentEmployee'
import DashboardPage from './pages/DashboardPage'
import ReportPage from './pages/ReportPage'
import ReviewPage from './pages/ReviewPage'
import SetupPage from './pages/SetupPage'

export default function App() {
  return (
    <CurrentEmployeeProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/report" element={<ReportPage />} />
            <Route path="/review" element={<ReviewPage />} />
            <Route path="/setup" element={<SetupPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </CurrentEmployeeProvider>
  )
}
