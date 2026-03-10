import {
    LineChart, Line, XAxis, YAxis, Tooltip, Legend,
    ResponsiveContainer, CartesianGrid
} from 'recharts'

const VITAL_CONFIG = [
    { key: 'HR', name: 'Heart Rate', color: '#E74C3C', unit: 'bpm' },
    { key: 'SpO2', name: 'SpO₂', color: '#3498DB', unit: '%' },
    { key: 'RR', name: 'Resp Rate', color: '#2ECC71', unit: '/min' },
    { key: 'Temp', name: 'Temperature', color: '#E67E22', unit: '°C' },
    { key: 'MAP', name: 'MAP', color: '#9B59B6', unit: 'mmHg' },
]

function formatTime(timestamp) {
    if (!timestamp) return ''
    try {
        return new Date(timestamp).toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        })
    } catch {
        return ''
    }
}

function CustomTooltip({ active, payload, label }) {
    if (!active || !payload?.length) return null

    return (
        <div className="bg-bg-card/95 backdrop-blur-sm border border-border-dark rounded-lg p-3 shadow-xl">
            <p className="text-xs text-gray-400 mb-2 font-mono">{label}</p>
            {payload.map((entry, i) => (
                <div key={i} className="flex items-center gap-2 text-xs py-0.5">
                    <span
                        className="w-2.5 h-2.5 rounded-full"
                        style={{ backgroundColor: entry.color }}
                    />
                    <span className="text-gray-300">{entry.name}:</span>
                    <span className="font-semibold text-white">
                        {typeof entry.value === 'number' ? entry.value.toFixed(1) : entry.value}
                    </span>
                </div>
            ))}
        </div>
    )
}

export default function VitalsChart({ history }) {
    const data = (history || []).map((v, i) => ({
        ...v,
        time: v.timestamp ? formatTime(v.timestamp) : `${i}s`,
    }))

    return (
        <div className="glass-card p-5">
            <h3 className="text-sm font-semibold text-gray-300 mb-4 uppercase tracking-wider">
                Real-Time Vitals — Last 60 readings
            </h3>
            <ResponsiveContainer width="100%" height={320}>
                <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e2533" />
                    <XAxis
                        dataKey="time"
                        tick={{ fill: '#6B7280', fontSize: 10 }}
                        tickLine={{ stroke: '#30363D' }}
                        axisLine={{ stroke: '#30363D' }}
                        interval="preserveStartEnd"
                    />
                    <YAxis
                        tick={{ fill: '#6B7280', fontSize: 10 }}
                        tickLine={{ stroke: '#30363D' }}
                        axisLine={{ stroke: '#30363D' }}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                        wrapperStyle={{ paddingTop: '10px' }}
                        formatter={(value) => (
                            <span style={{ color: '#9CA3AF', fontSize: '12px' }}>{value}</span>
                        )}
                    />
                    {VITAL_CONFIG.map(({ key, name, color }) => (
                        <Line
                            key={key}
                            type="monotone"
                            dataKey={key}
                            name={name}
                            stroke={color}
                            strokeWidth={2}
                            dot={false}
                            activeDot={{ r: 4, strokeWidth: 2, fill: '#0D1117' }}
                            animationDuration={300}
                        />
                    ))}
                </LineChart>
            </ResponsiveContainer>
        </div>
    )
}
