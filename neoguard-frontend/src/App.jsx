import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import PatientDetailPage from './pages/PatientDetailPage'
import PatientReportPage from './pages/PatientReportPage'
import AlertsPage from './pages/AlertsPage'

function ProtectedRoute({ children }) {
    const token = localStorage.getItem('neoguard_token')
    if (!token) return <Navigate to="/" replace />
    return children
}

function PublicRoute({ children }) {
    const token = localStorage.getItem('neoguard_token')
    if (token) return <Navigate to="/dashboard" replace />
    return children
}

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route
                    path="/"
                    element={
                        <PublicRoute>
                            <LoginPage />
                        </PublicRoute>
                    }
                />
                <Route
                    path="/dashboard"
                    element={
                        <ProtectedRoute>
                            <DashboardPage />
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/patient/:id"
                    element={
                        <ProtectedRoute>
                            <PatientDetailPage />
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/patient/:id/report"
                    element={
                        <ProtectedRoute>
                            <PatientReportPage />
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/alerts"
                    element={
                        <ProtectedRoute>
                            <AlertsPage />
                        </ProtectedRoute>
                    }
                />
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </BrowserRouter>
    )
}
