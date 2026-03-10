import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import client from '../api/client'
import VitalsChart from '../components/VitalsChart'
import {
    ArrowLeft, Printer, Loader2, Baby, Calendar, Bed, Clock,
    Heart, Droplets, Wind, Thermometer, Gauge, AlertTriangle, FileText, Check, Activity
} from 'lucide-react'

const SEVERITY_STYLES = {
    CRITICAL: 'bg-red-950/40 border-l-4 border-l-critical text-white',
    HIGH: 'bg-orange-950/40 border-l-4 border-l-high text-white',
}

export default function PatientReportPage() {
    const { id } = useParams()
    const navigate = useNavigate()
    const [report, setReport] = useState(null)
    const [patient, setPatient] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const loadReport = async () => {
            try {
                const [reportRes, patientRes] = await Promise.all([
                    client.get(`/patients/${id}/report`),
                    client.get(`/patients/${id}`),
                ])
                setReport(reportRes.data)
                setPatient(patientRes.data)
            } catch (err) {
                console.error('Failed to load report:', err)
            } finally {
                setLoading(false)
            }
        }
        loadReport()
    }, [id])

    const handlePrint = () => window.print()

    const handleAcknowledge = async (e, patientId, alertId) => {
        e.stopPropagation()
        try {
            const res = await client.post(`/alerts/${patientId}/${alertId}/acknowledge`)
            setReport(prev => {
                if (!prev) return prev
                const alertsList = prev.all_alerts || prev.alerts || []
                const updatedAlerts = alertsList.map(a =>
                    a.alert_id === alertId ? { ...a, acknowledged: true, acknowledged_by: res.data.acknowledged_by } : a
                )
                return { ...prev, all_alerts: updatedAlerts, alerts: updatedAlerts }
            })
        } catch (err) {
            console.error('Failed to acknowledge:', err)
        }
    }

    if (loading) {
        return (
            <div className="min-h-screen bg-bg-dark">
                <Navbar />
                <div className="flex items-center justify-center py-32">
                    <Loader2 className="w-8 h-8 text-medical-blue-light animate-spin" />
                </div>
            </div>
        )
    }

    // Extract data safely
    const vitalsAvg = report?.vitals_summary || report?.vitals_avg || {}
    const alertHistory = report?.all_alerts || report?.alerts || []
    const alertStats = report?.alerts_summary || report?.alert_stats || {}
    const gaAtBirth = patient?.ga_at_birth || report?.ga_at_birth || 28
    const currentCGA = patient?.corrected_ga || report?.corrected_ga || 30
    const cgaProgress = Math.min(((currentCGA - gaAtBirth) / (40 - gaAtBirth)) * 100, 100)
    const hasData = report?.has_data === true

    const vitalMetrics = [
        { label: 'Avg Heart Rate', value: vitalsAvg.HR?.avg ?? vitalsAvg.HR ?? vitalsAvg.avg_hr, unit: 'bpm', icon: Heart, color: 'text-red-400', range: '100–160' },
        { label: 'Avg SpO₂', value: vitalsAvg.SpO2?.avg ?? vitalsAvg.SpO2 ?? vitalsAvg.avg_spo2, unit: '%', icon: Droplets, color: 'text-blue-400', range: '90–100' },
        { label: 'Avg Resp Rate', value: vitalsAvg.RR?.avg ?? vitalsAvg.RR ?? vitalsAvg.avg_rr, unit: '/min', icon: Wind, color: 'text-green-400', range: '20–60' },
        { label: 'Avg Temperature', value: vitalsAvg.Temp?.avg ?? vitalsAvg.Temp ?? vitalsAvg.avg_temp, unit: '°C', icon: Thermometer, color: 'text-orange-400', range: '36.5–37.5' },
        { label: 'Avg MAP', value: vitalsAvg.MAP?.avg ?? vitalsAvg.MAP ?? vitalsAvg.avg_map, unit: 'mmHg', icon: Gauge, color: 'text-purple-400', range: '25–55' },
    ]

    return (
        <div className="min-h-screen bg-bg-dark">
            <Navbar />

            <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 print-container">
                {/* Top Bar (no-print) */}
                <div className="flex items-center justify-between mb-6 no-print">
                    <button
                        onClick={() => navigate(`/patient/${id}`)}
                        className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors text-sm"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Back to Patient
                    </button>
                    <button onClick={handlePrint} className="btn-primary flex items-center gap-2 text-sm">
                        <Printer className="w-4 h-4" />
                        Print Report
                    </button>
                </div>

                {/* Report Header */}
                <div className="glass-card p-6 mb-6">
                    <div className="flex items-center gap-3 mb-4">
                        <div className="p-2 bg-medical-blue/20 rounded-lg">
                            <FileText className="w-6 h-6 text-medical-blue-light" />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold text-white">Patient Report</h1>
                            <p className="text-xs text-gray-400">
                                Generated: {new Date().toLocaleString()}
                            </p>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4">
                        <div className="flex items-center gap-2">
                            <Baby className="w-4 h-4 text-gray-500" />
                            <div>
                                <p className="text-xs text-gray-500">Patient</p>
                                <p className="text-sm font-semibold text-white">{patient?.name}</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <Bed className="w-4 h-4 text-gray-500" />
                            <div>
                                <p className="text-xs text-gray-500">Bed</p>
                                <p className="text-sm font-semibold text-white">{patient?.bed}</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <Calendar className="w-4 h-4 text-gray-500" />
                            <div>
                                <p className="text-xs text-gray-500">GA at Birth</p>
                                <p className="text-sm font-semibold text-white">{gaAtBirth} weeks</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <Clock className="w-4 h-4 text-gray-500" />
                            <div>
                                <p className="text-xs text-gray-500">Days in NICU</p>
                                <p className="text-sm font-semibold text-white">{patient?.days_in_nicu}</p>
                            </div>
                        </div>
                    </div>

                    {patient?.diagnosis && (
                        <div className="mt-4 pt-4 border-t border-border-dark">
                            <span className="text-xs text-gray-500">Diagnosis: </span>
                            <span className="text-sm text-gray-300">{patient.diagnosis}</span>
                        </div>
                    )}
                </div>

                {!hasData ? (
                    <div className="glass-card p-12 mb-6 flex flex-col items-center justify-center text-center">
                        <Activity className="w-12 h-12 text-gray-600 mb-4" />
                        <h2 className="text-xl font-semibold text-white mb-2">No Monitoring Data Yet</h2>
                        <p className="text-gray-400 max-w-md">
                            The system is waiting for the ESP32 to transmit or start simulating vitals for {patient?.name}.
                        </p>
                    </div>
                ) : (
                    <>

                        {/* CGA Timeline */}
                        <div className="glass-card p-6 mb-6">
                            <h2 className="text-sm font-semibold text-gray-300 mb-4 uppercase tracking-wider">
                                Corrected Gestational Age Timeline
                            </h2>
                            <div className="relative">
                                <div className="flex justify-between text-xs text-gray-500 mb-2">
                                    <span>GA at Birth: {gaAtBirth}w</span>
                                    <span>Current CGA: {currentCGA?.toFixed(1)}w</span>
                                    <span>Term: 40w</span>
                                </div>
                                <div className="h-4 bg-bg-dark rounded-full overflow-hidden border border-border-dark">
                                    <div
                                        className="h-full rounded-full bg-gradient-to-r from-critical via-high to-normal transition-all duration-1000"
                                        style={{ width: `${cgaProgress}%` }}
                                    />
                                </div>
                                <div className="flex justify-between mt-2">
                                    <div className="flex items-center gap-1 text-[10px] text-gray-500">
                                        <div className="w-2 h-2 rounded-full bg-critical" />
                                        Extremely Preterm (&lt;28w)
                                    </div>
                                    <div className="flex items-center gap-1 text-[10px] text-gray-500">
                                        <div className="w-2 h-2 rounded-full bg-high" />
                                        Preterm (28-37w)
                                    </div>
                                    <div className="flex items-center gap-1 text-[10px] text-gray-500">
                                        <div className="w-2 h-2 rounded-full bg-normal" />
                                        Term (≥37w)
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Vitals Summary */}
                        <div className="glass-card p-6 mb-6">
                            <h2 className="text-sm font-semibold text-gray-300 mb-4 uppercase tracking-wider">
                                Vitals Summary
                            </h2>
                            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                                {vitalMetrics.map(({ label, value, unit, icon: Icon, color, range }) => (
                                    <div
                                        key={label}
                                        className="bg-bg-dark/50 rounded-lg p-4 border border-border-dark/50"
                                    >
                                        <div className="flex items-center gap-2 mb-2">
                                            <Icon className={`w-4 h-4 ${color}`} />
                                            <span className="text-xs text-gray-400">{label}</span>
                                        </div>
                                        <p className="text-2xl font-bold text-white mb-1">
                                            {value != null ? (typeof value === 'number' ? value.toFixed(1) : value) : '--'}
                                            <span className="text-sm text-gray-500 ml-1">{unit}</span>
                                        </p>
                                        <p className="text-[10px] text-gray-500">Ref: {range} {unit}</p>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Vitals Chart */}
                        {report?.vitals_history && report.vitals_history.length > 0 && (
                            <div className="mb-6">
                                <VitalsChart history={report.vitals_history} />
                            </div>
                        )}

                        {/* Alert History */}
                        <div className="glass-card p-6 mb-6">
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider flex items-center gap-2">
                                    <AlertTriangle className="w-4 h-4 text-high-light" />
                                    Alert History
                                </h2>
                                <div className="flex items-center gap-3 text-xs">
                                    <span className="text-gray-400">
                                        Total: <span className="text-white font-semibold">{alertStats.total || alertHistory.length}</span>
                                    </span>
                                    <span className="text-critical-light">
                                        Critical: <span className="font-semibold">{alertStats.critical || alertHistory.filter(a => a.severity === 'CRITICAL').length}</span>
                                    </span>
                                    <span className="text-high-light">
                                        High: <span className="font-semibold">{alertStats.high || alertHistory.filter(a => a.severity === 'HIGH').length}</span>
                                    </span>
                                </div>
                            </div>

                            {alertHistory.length === 0 ? (
                                <p className="text-sm text-gray-500 py-6 text-center">No alerts recorded</p>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="border-b border-border-dark text-xs text-gray-500 uppercase tracking-wider">
                                                <th className="text-left py-3 px-3">Time</th>
                                                <th className="text-left py-3 px-3">Rule</th>
                                                <th className="text-left py-3 px-3">Severity</th>
                                                <th className="text-left py-3 px-3">Duration</th>
                                                <th className="text-left py-3 px-3">Action</th>
                                                <th className="text-right py-3 px-3">Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {alertHistory.map((alert, i) => (
                                                <tr
                                                    key={i}
                                                    className={`border-b border-border-dark/30 ${SEVERITY_STYLES[alert.severity] || ''
                                                        }`}
                                                >
                                                    <td className="py-2.5 px-3 font-mono text-xs text-gray-400">
                                                        {alert.timestamp
                                                            ? new Date(alert.timestamp).toLocaleTimeString()
                                                            : '--'}
                                                    </td>
                                                    <td className="py-2.5 px-3 text-white font-medium">
                                                        {alert.name || alert.rule_id || alert.rule || '--'}
                                                    </td>
                                                    <td className="py-2.5 px-3">
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
                                                    <td className="py-2.5 px-3 text-gray-400">
                                                        {alert.duration ? `${alert.duration}s` : '--'}
                                                    </td>
                                                    <td className="py-2.5 px-3 text-gray-300 max-w-xs truncate">
                                                        {alert.action || '--'}
                                                    </td>
                                                    <td className="py-2.5 px-3">
                                                        <div className="flex items-center justify-end">
                                                            {alert.acknowledged ? (
                                                                <span className="text-xs text-green-400 flex items-center gap-1" title={alert.acknowledged_by ? `By ${alert.acknowledged_by}` : ''}>
                                                                    <Check className="w-3.5 h-3.5" /> Done
                                                                </span>
                                                            ) : (
                                                                <button
                                                                    onClick={(e) => handleAcknowledge(e, patient?.id || id, alert.alert_id)}
                                                                    className="px-2 py-1.5 text-xs bg-medical-blue/20 text-medical-blue-light hover:bg-medical-blue/30 rounded transition-colors flex items-center gap-1"
                                                                >
                                                                    <Check className="w-3 h-3" /> Ack
                                                                </button>
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
                    </>
                )}
            </main>
        </div>
    )
}
