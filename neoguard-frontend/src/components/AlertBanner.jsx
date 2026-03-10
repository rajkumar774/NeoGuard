import { useState } from 'react'
import { AlertTriangle, X, Bell } from 'lucide-react'

export default function AlertBanner({ alerts }) {
    const [dismissed, setDismissed] = useState(false)

    if (dismissed || !alerts || alerts.length === 0) return null

    const criticalAlerts = alerts.filter(a => a.severity === 'CRITICAL')
    const highAlerts = alerts.filter(a => a.severity === 'HIGH')
    const hasCritical = criticalAlerts.length > 0
    const topAlert = criticalAlerts[0] || highAlerts[0] || alerts[0]

    return (
        <div
            className={`relative overflow-hidden rounded-xl border px-5 py-4 animate-slide-down ${hasCritical
                    ? 'bg-red-950/60 border-critical/40'
                    : 'bg-orange-950/60 border-high/40'
                }`}
        >
            {/* Animated background pulse for critical */}
            {hasCritical && (
                <div className="absolute inset-0 bg-gradient-to-r from-critical/10 via-transparent to-critical/10 animate-pulse" />
            )}

            <div className="relative flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                    <div
                        className={`p-2 rounded-lg ${hasCritical ? 'bg-critical/20' : 'bg-high/20'
                            }`}
                    >
                        {hasCritical ? (
                            <AlertTriangle className="w-5 h-5 text-critical-light animate-pulse" />
                        ) : (
                            <Bell className="w-5 h-5 text-high-light" />
                        )}
                    </div>

                    <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                            <span
                                className={hasCritical ? 'badge-critical' : 'badge-high'}
                            >
                                {hasCritical ? 'CRITICAL' : 'HIGH'}
                            </span>
                            <span className="text-sm font-semibold text-white">
                                {alerts.length} Active Alert{alerts.length > 1 ? 's' : ''}
                            </span>
                        </div>

                        <p className="text-sm text-gray-300">
                            <span className="font-medium text-white">{topAlert.name || topAlert.rule_id || topAlert.label}:</span>{' '}
                            {topAlert.action || topAlert.description || 'Immediate attention required'}
                        </p>

                        {topAlert.patient_name && (
                            <p className="text-xs text-gray-400 mt-1">
                                Patient: {topAlert.patient_name} {topAlert.bed ? `• Bed ${topAlert.bed}` : ''}
                            </p>
                        )}
                    </div>
                </div>

                <button
                    onClick={() => setDismissed(true)}
                    className="p-1.5 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white flex-shrink-0"
                >
                    <X className="w-4 h-4" />
                </button>
            </div>
        </div>
    )
}
