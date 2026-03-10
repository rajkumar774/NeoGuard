import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useWebSocket } from '../hooks/useWebSocket'
import Navbar from '../components/Navbar'
import VitalCard from '../components/VitalCard'
import VitalsChart from '../components/VitalsChart'
import AlertBanner from '../components/AlertBanner'
import client from '../api/client'
import {
    ArrowLeft, FileText, Wifi, WifiOff, Bed, Baby, Calendar,
    Clock, Activity, Cpu, Loader2, AlertTriangle, Check
} from 'lucide-react'

const NORMAL_RANGES = {
    extremely_preterm: { HR: [120, 180], SpO2: [88, 95], RR: [30, 60], Temp: [36.5, 37.5], MAP: [25, 40] },
    very_preterm: { HR: [120, 175], SpO2: [90, 96], RR: [28, 55], Temp: [36.5, 37.5], MAP: [28, 42] },
    moderate_preterm: { HR: [115, 170], SpO2: [91, 97], RR: [25, 50], Temp: [36.5, 37.5], MAP: [30, 45] },
    late_preterm: { HR: [110, 165], SpO2: [92, 98], RR: [22, 50], Temp: [36.5, 37.5], MAP: [32, 48] },
    term: { HR: [100, 160], SpO2: [94, 100], RR: [20, 45], Temp: [36.5, 37.5], MAP: [35, 55] },
}

const PHASE_LABELS = {
    acute: { label: 'Acute', class: 'phase-acute', icon: '🔴' },
    extended: { label: 'Extended', class: 'phase-extended', icon: '🟠' },
    step_down: { label: 'Step Down', class: 'phase-step_down', icon: '🟡' },
    discharge_ready: { label: 'Discharge Ready', class: 'phase-discharge_ready', icon: '🟢' },
}

export default function PatientDetailPage() {
    const { id } = useParams()
    const navigate = useNavigate()
    const { vitals, alerts, connected, history, cga, phase, gaCat } = useWebSocket(id)
    const [patient, setPatient] = useState(null)
    const [loading, setLoading] = useState(true)
    const [sessionAlerts, setSessionAlerts] = useState([])

    useEffect(() => {
        const fetchPatient = async () => {
            try {
                const res = await client.get(`/patients/${id}`)
                setPatient(res.data)

                // Seed session alerts with currently active alerts on load
                if (res.data.active_alerts && res.data.active_alerts.length > 0) {
                    setSessionAlerts(res.data.active_alerts.map(a => ({
                        ...a,
                        receivedAt: new Date().toISOString()
                    })))
                }
            } catch (err) {
                console.error('Failed to fetch patient:', err)
            } finally {
                setLoading(false)
            }
        }
        fetchPatient()
    }, [id])

    // Accumulate and update session alerts based on active socket payload
    useEffect(() => {
        if (!alerts) return
        setSessionAlerts(prev => {
            let updated = [...prev]
            alerts.forEach(newAlert => {
                const existingIdx = updated.findIndex(a => a.alert_id === newAlert.alert_id)
                if (existingIdx >= 0) {
                    updated[existingIdx] = { ...updated[existingIdx], ...newAlert }
                } else {
                    updated.unshift({ ...newAlert, receivedAt: new Date().toISOString() })
                }
            })
            return updated.slice(0, 50)
        })
    }, [alerts])

    const handleAcknowledge = async (e, alertId) => {
        e.stopPropagation()
        try {
            const res = await client.post(`/alerts/${id}/${alertId}/acknowledge`)
            setSessionAlerts(prev => prev.map(a =>
                a.alert_id === alertId ? { ...a, acknowledged: true, acknowledged_by: res.data.acknowledged_by } : a
            ))
        } catch (err) {
            console.error('Failed to acknowledge:', err)
        }
    }

    const currentGaCat = gaCat || patient?.ga_category || 'term'
    const currentPhase = phase || patient?.phase || 'acute'
    const ranges = NORMAL_RANGES[currentGaCat] || NORMAL_RANGES.term
    const phaseInfo = PHASE_LABELS[currentPhase] || PHASE_LABELS.acute

    const vitalCards = [
        { label: 'Heart Rate', key: 'HR', unit: 'bpm' },
        { label: 'SpO₂', key: 'SpO2', unit: '%' },
        { label: 'Resp Rate', key: 'RR', unit: '/min' },
        { label: 'Temperature', key: 'Temp', unit: '°C' },
        { label: 'MAP', key: 'MAP', unit: 'mmHg' },
    ]

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

    return (
        <div className="min-h-screen bg-bg-dark">
            <Navbar />

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                {/* Critical Alert Banner */}
                {alerts?.some(a => a.severity === 'CRITICAL') && (
                    <div className="mb-6">
                        <AlertBanner alerts={alerts} />
                    </div>
                )}

                {/* Top Bar */}
                <div className="flex items-center justify-between mb-6">
                    <button
                        onClick={() => navigate('/dashboard')}
                        className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors text-sm"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Back to Dashboard
                    </button>

                    <div className="flex items-center gap-3">
                        {/* Source badge */}
                        {vitals?.source && (
                            <span className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${vitals.source === 'ESP32'
                                ? 'bg-blue-900/60 text-blue-200 border border-blue-700/40'
                                : 'bg-purple-900/60 text-purple-200 border border-purple-700/40'
                                }`}>
                                <Cpu className="w-3 h-3" />
                                {vitals.source}
                            </span>
                        )}

                        {/* Connection status */}
                        <span className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${connected
                            ? 'bg-normal/20 text-normal-light'
                            : 'bg-gray-700/50 text-gray-400'
                            }`}>
                            {connected ? (
                                <><Wifi className="w-3 h-3" /> Live</>
                            ) : (
                                <><WifiOff className="w-3 h-3" /> Offline</>
                            )}
                        </span>

                        <button
                            onClick={() => navigate(`/patient/${id}/report`)}
                            className="btn-primary flex items-center gap-2 text-sm"
                        >
                            <FileText className="w-4 h-4" />
                            Full Report
                        </button>
                    </div>
                </div>

                {/* Patient Info Header */}
                <div className="glass-card p-6 mb-6">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                        <div>
                            <h1 className="text-2xl font-bold text-white mb-2">{patient?.name}</h1>
                            <div className="flex flex-wrap items-center gap-3 text-sm text-gray-400">
                                <span className="flex items-center gap-1.5">
                                    <Bed className="w-4 h-4" />
                                    Bed {patient?.bed}
                                </span>
                                <span className="text-gray-600">•</span>
                                <span className="flex items-center gap-1.5">
                                    <Baby className="w-4 h-4" />
                                    GA: {patient?.ga_at_birth}w
                                </span>
                                <span className="text-gray-600">•</span>
                                <span className="flex items-center gap-1.5">
                                    <Calendar className="w-4 h-4" />
                                    CGA: {(cga || patient?.corrected_ga)?.toFixed(1)}w
                                </span>
                                <span className="text-gray-600">•</span>
                                <span className="flex items-center gap-1.5">
                                    <Clock className="w-4 h-4" />
                                    {patient?.days_in_nicu} days in NICU
                                </span>
                            </div>
                            {patient?.diagnosis && (
                                <p className="text-sm text-gray-400 mt-2">
                                    <span className="text-gray-500">Diagnosis:</span>{' '}
                                    <span className="text-gray-300">{patient.diagnosis}</span>
                                </p>
                            )}
                        </div>

                        <div className="flex items-center gap-3">
                            <span className={phaseInfo.class}>
                                {phaseInfo.icon} {phaseInfo.label}
                            </span>
                            <span className="px-3 py-1 rounded-full text-xs font-medium bg-bg-dark border border-border-dark text-gray-300">
                                {currentGaCat?.replace(/_/g, ' ')}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Vital Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-6 animate-fade-in">
                    {vitalCards.map(({ label, key, unit }) => (
                        <VitalCard
                            key={key}
                            label={label}
                            value={vitals?.[key]}
                            unit={unit}
                            normalMin={ranges[key]?.[0]}
                            normalMax={ranges[key]?.[1]}
                        />
                    ))}
                </div>

                {/* Chart + Alert Panel */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2">
                        <VitalsChart history={history} />
                    </div>

                    {/* Alert Panel */}
                    <div className="glass-card p-5 max-h-[420px] overflow-y-auto">
                        <h3 className="text-sm font-semibold text-gray-300 mb-4 uppercase tracking-wider flex items-center gap-2">
                            <AlertTriangle className="w-4 h-4 text-high-light" />
                            Session Alerts ({sessionAlerts.length})
                        </h3>

                        {sessionAlerts.length === 0 ? (
                            <div className="text-center py-10">
                                <Activity className="w-8 h-8 text-gray-600 mx-auto mb-2" />
                                <p className="text-sm text-gray-500">No alerts in this session</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {sessionAlerts.map((alert, i) => (
                                    <div
                                        key={i}
                                        className={`p-3 rounded-lg border ${alert.acknowledged
                                            ? 'opacity-50 grayscale border-gray-600/30 bg-gray-600/10'
                                            : alert.severity === 'CRITICAL'
                                                ? 'bg-critical/5 border-critical/20'
                                                : 'bg-high/5 border-high/20'
                                            }`}
                                    >
                                        <div className="flex items-center justify-between mb-1.5">
                                            <span
                                                className={
                                                    alert.severity === 'CRITICAL' ? 'badge-critical' : 'badge-high'
                                                }
                                            >
                                                {alert.severity}
                                            </span>
                                            <span className="text-[10px] text-gray-500 font-mono">
                                                {alert.timestamp
                                                    ? new Date(alert.timestamp).toLocaleTimeString()
                                                    : alert.receivedAt
                                                        ? new Date(alert.receivedAt).toLocaleTimeString()
                                                        : ''}
                                            </span>
                                        </div>
                                        <div className="flex items-start justify-between">
                                            <div>
                                                <p className="text-sm font-medium text-white mb-1">
                                                    {alert.name || alert.rule_id}
                                                </p>
                                                {alert.duration && (
                                                    <p className="text-xs text-gray-400">
                                                        Duration: {alert.duration}s
                                                    </p>
                                                )}
                                                {alert.action && (
                                                    <p className="text-xs text-normal-light mt-1">
                                                        💊 {alert.action}
                                                    </p>
                                                )}
                                            </div>
                                            <div className="mt-1">
                                                {alert.acknowledged ? (
                                                    <span className="text-xs text-green-400 flex items-center gap-1" title={alert.acknowledged_by ? `By ${alert.acknowledged_by}` : ''}>
                                                        <Check className="w-3.5 h-3.5" /> Done
                                                    </span>
                                                ) : (
                                                    <button
                                                        onClick={(e) => handleAcknowledge(e, alert.alert_id)}
                                                        className="px-2 py-1 text-xs bg-medical-blue/20 text-medical-blue-light hover:bg-medical-blue/30 rounded border border-medical-blue/30 transition-colors flex items-center gap-1"
                                                    >
                                                        <Check className="w-3 h-3" /> Ack
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </main>
        </div>
    )
}
