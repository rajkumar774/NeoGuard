import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth'
import Navbar from '../components/Navbar'
import PatientCard from '../components/PatientCard'
import PatientForm from '../components/PatientForm'
import AlertBanner from '../components/AlertBanner'
import client from '../api/client'
import { Users, AlertTriangle, AlertCircle, Bed, Plus, Loader2, Activity } from 'lucide-react'

export default function DashboardPage() {
    const { user } = useAuth()
    const [patients, setPatients] = useState([])
    const [activeAlerts, setActiveAlerts] = useState([])
    const [loading, setLoading] = useState(true)
    const [showForm, setShowForm] = useState(false)

    const fetchPatients = async () => {
        try {
            const res = await client.get('/patients')
            setPatients(res.data)
        } catch (err) {
            console.error('Failed to fetch patients:', err)
        }
    }

    const fetchAlerts = async () => {
        try {
            const res = await client.get('/alerts/active')
            setActiveAlerts(res.data)
        } catch (err) {
            console.error('Failed to fetch alerts:', err)
        }
    }

    useEffect(() => {
        const loadData = async () => {
            setLoading(true)
            await Promise.all([fetchPatients(), fetchAlerts()])
            setLoading(false)
        }
        loadData()

        // Auto-refresh alerts every 10 seconds
        const alertInterval = setInterval(fetchAlerts, 10000)
        return () => clearInterval(alertInterval)
    }, [])

    const criticalAlerts = activeAlerts.filter(a => a.severity === 'CRITICAL')
    const highAlerts = activeAlerts.filter(a => a.severity === 'HIGH')

    const stats = [
        {
            label: 'Total Patients',
            value: patients.length,
            icon: Users,
            color: 'text-medical-blue-light',
            bg: 'bg-medical-blue/10',
        },
        {
            label: 'Critical Alerts',
            value: criticalAlerts.length,
            icon: AlertTriangle,
            color: 'text-critical-light',
            bg: 'bg-critical/10',
        },
        {
            label: 'High Alerts',
            value: highAlerts.length,
            icon: AlertCircle,
            color: 'text-high-light',
            bg: 'bg-high/10',
        },
        {
            label: 'Total Beds',
            value: patients.length,
            icon: Bed,
            color: 'text-purple-400',
            bg: 'bg-purple-500/10',
        },
    ]

    return (
        <div className="min-h-screen bg-bg-dark">
            <Navbar />

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                {/* Critical Alert Banner */}
                {criticalAlerts.length > 0 && (
                    <div className="mb-6">
                        <AlertBanner alerts={criticalAlerts} />
                    </div>
                )}

                {/* Stats Row */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                    {stats.map(({ label, value, icon: Icon, color, bg }) => (
                        <div
                            key={label}
                            className="glass-card p-4 flex items-center gap-4 hover:border-border-light transition-all"
                        >
                            <div className={`p-3 rounded-xl ${bg}`}>
                                <Icon className={`w-6 h-6 ${color}`} />
                            </div>
                            <div>
                                <p className="text-2xl font-bold text-white">{value}</p>
                                <p className="text-xs text-gray-400">{label}</p>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Header + Add Button */}
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <Activity className="w-5 h-5 text-medical-blue-light" />
                        <h2 className="text-lg font-semibold text-white">Patient Monitoring</h2>
                        <span className="text-sm text-gray-500">
                            ({patients.length} patient{patients.length !== 1 ? 's' : ''})
                        </span>
                    </div>
                    {user?.role === 'doctor' && (
                        <button
                            onClick={() => setShowForm(true)}
                            className="btn-primary flex items-center gap-2 text-sm"
                        >
                            <Plus className="w-4 h-4" />
                            Add Patient
                        </button>
                    )}
                </div>

                {/* Patient Grid */}
                {loading ? (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 className="w-8 h-8 text-medical-blue-light animate-spin" />
                    </div>
                ) : patients.length === 0 ? (
                    <div className="text-center py-20">
                        <Users className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                        <p className="text-gray-400">No patients found</p>
                        {user?.role === 'doctor' && (
                            <button
                                onClick={() => setShowForm(true)}
                                className="btn-primary mt-4 text-sm"
                            >
                                Add First Patient
                            </button>
                        )}
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5 animate-fade-in">
                        {patients.map(patient => (
                            <PatientCard key={patient.id} patient={patient} />
                        ))}
                    </div>
                )}
            </main>

            {/* Patient Form Modal */}
            {showForm && (
                <PatientForm
                    onClose={() => setShowForm(false)}
                    onPatientAdded={fetchPatients}
                />
            )}
        </div>
    )
}
