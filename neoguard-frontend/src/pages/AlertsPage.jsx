import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import client from '../api/client'
import {
    AlertTriangle, RefreshCw, Filter, Loader2, ExternalLink, Clock, Check
} from 'lucide-react'

export default function AlertsPage() {
    const navigate = useNavigate()
    const [alerts, setAlerts] = useState([])
    const [loading, setLoading] = useState(true)
    const [filter, setFilter] = useState('all')
    const [lastRefresh, setLastRefresh] = useState(new Date())

    const fetchAlerts = async () => {
        try {
            const res = await client.get('/alerts/active')
            setAlerts(res.data)
            setLastRefresh(new Date())
        } catch (err) {
            console.error('Failed to fetch alerts:', err)
        } finally {
            setLoading(false)
        }
    }

    const handleAcknowledge = async (e, patientId, alertId) => {
        e.stopPropagation()
        try {
            const res = await client.post(`/alerts/${patientId}/${alertId}/acknowledge`)
            setAlerts(prev => prev.map(a =>
                (a.alert_id === alertId && a.patient_id === patientId)
                    ? { ...a, acknowledged: true, acknowledged_by: res.data.acknowledged_by }
                    : a
            ))
        } catch (err) {
            console.error('Failed to acknowledge:', err)
        }
    }

    useEffect(() => {
        fetchAlerts()
        const interval = setInterval(fetchAlerts, 10000) // Auto-refresh every 10s
        return () => clearInterval(interval)
    }, [])

    const filteredAlerts =
        filter === 'all'
            ? alerts
            : alerts.filter(a => a.severity === filter)

    const criticalCount = alerts.filter(a => a.severity === 'CRITICAL').length
    const highCount = alerts.filter(a => a.severity === 'HIGH').length

    return (
        <div className="min-h-screen bg-bg-dark">
            <Navbar />

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-high/20 rounded-lg">
                            <AlertTriangle className="w-6 h-6 text-high-light" />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold text-white">Active Alerts</h1>
                            <p className="text-xs text-gray-400 flex items-center gap-1.5">
                                <Clock className="w-3 h-3" />
                                Last refreshed: {lastRefresh.toLocaleTimeString()} • Auto-refresh: 10s
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        {/* Filter */}
                        <div className="flex items-center gap-1 bg-bg-card rounded-lg border border-border-dark p-1">
                            <button
                                onClick={() => setFilter('all')}
                                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${filter === 'all'
                                    ? 'bg-medical-blue/20 text-medical-blue-light'
                                    : 'text-gray-400 hover:text-white'
                                    }`}
                            >
                                All ({alerts.length})
                            </button>
                            <button
                                onClick={() => setFilter('CRITICAL')}
                                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${filter === 'CRITICAL'
                                    ? 'bg-critical/20 text-critical-light'
                                    : 'text-gray-400 hover:text-white'
                                    }`}
                            >
                                Critical ({criticalCount})
                            </button>
                            <button
                                onClick={() => setFilter('HIGH')}
                                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${filter === 'HIGH'
                                    ? 'bg-high/20 text-high-light'
                                    : 'text-gray-400 hover:text-white'
                                    }`}
                            >
                                High ({highCount})
                            </button>
                        </div>

                        <button
                            onClick={fetchAlerts}
                            className="p-2 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white border border-border-dark"
                            title="Refresh"
                        >
                            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        </button>
                    </div>
                </div>

                {/* Stats Summary */}
                <div className="grid grid-cols-3 gap-4 mb-6">
                    <div className="glass-card p-4 flex items-center gap-3">
                        <div className="p-2 bg-medical-blue/10 rounded-lg">
                            <AlertTriangle className="w-5 h-5 text-medical-blue-light" />
                        </div>
                        <div>
                            <p className="text-xl font-bold text-white">{alerts.length}</p>
                            <p className="text-xs text-gray-400">Total Active</p>
                        </div>
                    </div>
                    <div className="glass-card p-4 flex items-center gap-3">
                        <div className="p-2 bg-critical/10 rounded-lg">
                            <AlertTriangle className="w-5 h-5 text-critical-light" />
                        </div>
                        <div>
                            <p className="text-xl font-bold text-critical-light">{criticalCount}</p>
                            <p className="text-xs text-gray-400">Critical</p>
                        </div>
                    </div>
                    <div className="glass-card p-4 flex items-center gap-3">
                        <div className="p-2 bg-high/10 rounded-lg">
                            <AlertTriangle className="w-5 h-5 text-high-light" />
                        </div>
                        <div>
                            <p className="text-xl font-bold text-high-light">{highCount}</p>
                            <p className="text-xs text-gray-400">High</p>
                        </div>
                    </div>
                </div>

                {/* Alerts Table */}
                <div className="glass-card overflow-hidden">
                    {loading ? (
                        <div className="flex items-center justify-center py-20">
                            <Loader2 className="w-8 h-8 text-medical-blue-light animate-spin" />
                        </div>
                    ) : filteredAlerts.length === 0 ? (
                        <div className="text-center py-20">
                            <AlertTriangle className="w-10 h-10 text-gray-600 mx-auto mb-3" />
                            <p className="text-gray-400">
                                {filter === 'all'
                                    ? 'No active alerts — all patients stable'
                                    : `No ${filter.toLowerCase()} alerts active`}
                            </p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b border-border-dark bg-bg-dark/50 text-xs text-gray-500 uppercase tracking-wider">
                                        <th className="text-left py-3 px-4">Time</th>
                                        <th className="text-left py-3 px-4">Patient</th>
                                        <th className="text-left py-3 px-4">Bed</th>
                                        <th className="text-left py-3 px-4">Alert Type</th>
                                        <th className="text-left py-3 px-4">Severity</th>
                                        <th className="text-left py-3 px-4">Duration</th>
                                        <th className="text-left py-3 px-4">Action</th>
                                        <th className="text-left py-3 px-4"></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredAlerts.map((alert, i) => (
                                        <tr
                                            key={i}
                                            className={`border-b border-border-dark/30 cursor-pointer transition-colors hover:bg-bg-card-hover ${alert.acknowledged
                                                ? 'opacity-50 grayscale'
                                                : alert.severity === 'CRITICAL'
                                                    ? 'bg-red-950/20'
                                                    : 'bg-orange-950/10'
                                                }`}
                                            onClick={() => {
                                                if (alert.patient_id) navigate(`/patient/${alert.patient_id}`)
                                            }}
                                        >
                                            <td className="py-3 px-4 font-mono text-xs text-gray-400">
                                                {alert.timestamp
                                                    ? new Date(alert.timestamp).toLocaleTimeString()
                                                    : '--'}
                                            </td>
                                            <td className="py-3 px-4 text-white font-medium">
                                                {alert.patient_name || alert.patient_id || '--'}
                                            </td>
                                            <td className="py-3 px-4 text-gray-400">
                                                {alert.bed || '--'}
                                            </td>
                                            <td className="py-3 px-4 text-white">
                                                {alert.name || alert.rule_id || alert.type || '--'}
                                            </td>
                                            <td className="py-3 px-4">
                                                <span
                                                    className={
                                                        alert.severity === 'CRITICAL'
                                                            ? 'badge-critical'
                                                            : 'badge-high'
                                                    }
                                                >
                                                    {alert.severity}
                                                </span>
                                            </td>
                                            <td className="py-3 px-4 text-gray-400">
                                                {alert.duration ? `${alert.duration}s` : '--'}
                                            </td>
                                            <td className="py-3 px-4 text-gray-300 max-w-xs truncate">
                                                {alert.action || '--'}
                                            </td>
                                            <td className="py-3 px-4">
                                                <div className="flex items-center gap-3 justify-end">
                                                    {alert.acknowledged ? (
                                                        <span className="text-xs text-green-400 flex items-center gap-1" title={alert.acknowledged_by ? `By ${alert.acknowledged_by}` : ''}>
                                                            <Check className="w-3.5 h-3.5" /> Done
                                                        </span>
                                                    ) : (
                                                        <button
                                                            onClick={(e) => handleAcknowledge(e, alert.patient_id, alert.alert_id)}
                                                            className="px-2 py-1.5 text-xs bg-medical-blue/20 text-medical-blue-light hover:bg-medical-blue/30 rounded transition-colors flex items-center gap-1"
                                                        >
                                                            <Check className="w-3 h-3" /> Ack
                                                        </button>
                                                    )}
                                                    {alert.patient_id && (
                                                        <ExternalLink className="w-3.5 h-3.5 text-gray-500 hover:text-white transition-colors" />
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </main>
        </div>
    )
}
