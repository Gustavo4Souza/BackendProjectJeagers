import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import HistoricoPage from './pages/HistoricoPage'
import AlertasPage from './pages/AlertasPage'
import ConfigPage from './pages/ConfigPage'
import BatchesPage from './pages/BatchesPage'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/historico"
            element={
              <ProtectedRoute>
                <HistoricoPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/alertas"
            element={
              <ProtectedRoute>
                <AlertasPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/lotes"
            element={
              <ProtectedRoute>
                <BatchesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/config"
            element={
              <ProtectedRoute>
                <ConfigPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
