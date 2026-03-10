import { useNavigate } from 'react-router-dom'
import { useWebSocket } from '../hooks/useWebSocket'
import { Heart, Wind, Thermometer, Droplets, Bed, ChevronRight, Wifi, WifiOff } from 'lucide-react'

const PHASE_BADGE = {
    acute: 'phase-acute',
    extended: 'phase-extended',
    step_down: 'phase-step_down',
    discharge_ready: 'phase-discharge_ready',
}

export default function PatientCard({ patient }) {
    const navigate = useNavigate()
    const { vitals, alerts, connected } = useWebSocket(patient.id)

    const hasCritical = alerts?.some(a => a.severity === 'CRITICAL')
    const hasHigh = alerts?.some(a => a.severity === 'HIGH')
    const currentVitals = vitals || {}
    const phase = patient.phase || 'acute'

    return (
        <div
            className={`glass-card p-5 cursor-pointer group transition-all duration-300 hover:bg-bg-card-hover hover:border-border-light hover:scale-[1.01] hover:shadow-xl hover:shadow-black/20 relative overflow-hidden ${hasCritical ? 'border-critical/40' : hasHigh ? 'border-high/30' : ''
                }`}
            onClick={() => navigate(`/patient/${patient.id}`)}
        >
            {/* Critical pulse indicator */}
            {hasCritical && (
                <div className="absolute top-3 right-3 flex items-center gap-1.5">
                    <span className="relative flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-critical opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-critical"></span>
                    </span>
                </div>
            )}

            {/* Header */}
            <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                    <h3 className="text-white font-semibold text-base group-hover:text-medical-blue-light transition-colors">
                        {patient.name}
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                        <div className="flex items-center gap-1 text-xs text-gray-400">
                            <Bed className="w-3.5 h-3.5" />
                            <span>Bed {patient.bed}</span>
                        </div>
                        <span className="text-gray-600">•</span>
                        <span className="text-xs text-gray-400">
                            CGA: {patient.corrected_ga?.toFixed(1) || '--'}w
                        </span>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <span className={PHASE_BADGE[phase] || 'phase-acute'}>
                        {phase.replace('_', ' ')}
                    </span>
                    {connected ? (
                        <Wifi className="w-3.5 h-3.5 text-normal-light" />
                    ) : (
                        <WifiOff className="w-3.5 h-3.5 text-gray-600" />
                    )}
                </div>
            </div>

            {/* Mini vitals */}
            <div className="grid grid-cols-4 gap-3 mb-4">
                <div className="text-center">
                    <Heart className="w-3.5 h-3.5 text-red-400 mx-auto mb-1" />
                    <p className="text-sm font-bold text-white">
                        {currentVitals.HR != null ? Math.round(currentVitals.HR) : '--'}
                    </p>
                    <p className="text-[10px] text-gray-500">bpm</p>
                </div>
                <div className="text-center">
                    <Droplets className="w-3.5 h-3.5 text-blue-400 mx-auto mb-1" />
                    <p className="text-sm font-bold text-white">
                        {currentVitals.SpO2 != null ? currentVitals.SpO2.toFixed(1) : '--'}
                    </p>
                    <p className="text-[10px] text-gray-500">SpO₂%</p>
                </div>
                <div className="text-center">
                    <Wind className="w-3.5 h-3.5 text-green-400 mx-auto mb-1" />
                    <p className="text-sm font-bold text-white">
                        {currentVitals.RR != null ? Math.round(currentVitals.RR) : '--'}
                    </p>
                    <p className="text-[10px] text-gray-500">/min</p>
                </div>
                <div className="text-center">
                    <Thermometer className="w-3.5 h-3.5 text-orange-400 mx-auto mb-1" />
                    <p className="text-sm font-bold text-white">
                        {currentVitals.Temp != null ? currentVitals.Temp.toFixed(1) : '--'}
                    </p>
                    <p className="text-[10px] text-gray-500">°C</p>
                </div>
            </div>

            {/* Alert count + View button */}
            <div className="flex items-center justify-between pt-3 border-t border-border-dark/50">
                <div className="flex items-center gap-2">
                    {patient.pending_alerts > 0 ? (
                        <span className={patient.pending_alerts > 2 ? 'badge-critical' : 'badge-high'}>
                            {patient.pending_alerts} alert{patient.pending_alerts > 1 ? 's' : ''}
                        </span>
                    ) : (
                        <span className="badge-normal">Stable</span>
                    )}
                    {patient.diagnosis && (
                        <span className="text-xs text-gray-500 truncate max-w-[120px]">
                            {patient.diagnosis}
                        </span>
                    )}
                </div>
                <ChevronRight className="w-4 h-4 text-gray-500 group-hover:text-medical-blue-light group-hover:translate-x-0.5 transition-all" />
            </div>
        </div>
    )
}
