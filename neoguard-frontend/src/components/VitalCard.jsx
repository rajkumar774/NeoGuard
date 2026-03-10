import { Heart, SprayCan, Wind, Thermometer, Gauge } from 'lucide-react'

const ICONS = {
    HR: Heart,
    SpO2: SprayCan,
    RR: Wind,
    Temp: Thermometer,
    MAP: Gauge,
}

const UNIT_MAP = {
    HR: 'bpm',
    SpO2: '%',
    RR: '/min',
    Temp: '°C',
    MAP: 'mmHg',
}

const LABELS = {
    HR: 'Heart Rate',
    SpO2: 'SpO₂',
    RR: 'Resp Rate',
    Temp: 'Temperature',
    MAP: 'MAP',
}

function getVitalStatus(label, value, normalMin, normalMax) {
    if (value == null || normalMin == null || normalMax == null) return 'normal'
    const range = normalMax - normalMin
    if (value >= normalMin && value <= normalMax) return 'normal'
    const deviation = value < normalMin
        ? (normalMin - value) / range
        : (value - normalMax) / range
    if (deviation <= 0.1) return 'warning'
    return 'critical'
}

const STATUS_STYLES = {
    normal: {
        border: 'border-normal/50',
        glow: 'vital-glow-green',
        icon: 'text-normal-light',
        value: 'text-normal-light',
        bg: 'bg-normal/5',
    },
    warning: {
        border: 'border-high/50',
        glow: 'vital-glow-yellow',
        icon: 'text-high-light',
        value: 'text-high-light',
        bg: 'bg-high/5',
    },
    critical: {
        border: 'border-critical/50',
        glow: 'vital-glow-red',
        icon: 'text-critical-light',
        value: 'text-critical-light',
        bg: 'bg-critical/5',
    },
}

export default function VitalCard({ label, value, unit, normalMin, normalMax, icon }) {
    const vitalKey = Object.keys(LABELS).find(k => LABELS[k] === label) || label
    const IconComponent = icon || ICONS[vitalKey] || Heart
    const displayUnit = unit || UNIT_MAP[vitalKey] || ''
    const displayLabel = LABELS[vitalKey] || label
    const status = getVitalStatus(vitalKey, value, normalMin, normalMax)
    const styles = STATUS_STYLES[status]

    return (
        <div
            className={`glass-card p-4 ${styles.border} ${styles.glow} ${styles.bg} transition-all duration-500 hover:scale-[1.02]`}
        >
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                    <IconComponent className={`w-5 h-5 ${styles.icon}`} />
                    <span className="text-sm font-medium text-gray-400">{displayLabel}</span>
                </div>
                <div
                    className={`w-2.5 h-2.5 rounded-full ${status === 'critical'
                            ? 'bg-critical animate-pulse-critical'
                            : status === 'warning'
                                ? 'bg-high animate-pulse'
                                : 'bg-normal'
                        }`}
                />
            </div>

            <div className="flex items-baseline gap-1.5 mb-2">
                <span className={`text-3xl font-bold tracking-tight ${styles.value}`}>
                    {value != null ? (typeof value === 'number' ? value.toFixed(vitalKey === 'Temp' || vitalKey === 'SpO2' ? 1 : 0) : value) : '--'}
                </span>
                <span className="text-sm text-gray-500">{displayUnit}</span>
            </div>

            {normalMin != null && normalMax != null && (
                <div className="text-xs text-gray-500 flex items-center gap-1">
                    <span>Normal:</span>
                    <span className="font-mono">
                        {normalMin}–{normalMax} {displayUnit}
                    </span>
                </div>
            )}
        </div>
    )
}
