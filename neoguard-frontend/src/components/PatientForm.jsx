import { useState } from 'react'
import { X, UserPlus, Loader2 } from 'lucide-react'
import client from '../api/client'

export default function PatientForm({ onClose, onPatientAdded }) {
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [form, setForm] = useState({
        name: '',
        ga_at_birth: 28,
        days_in_nicu: 0,
        diagnosis: '',
        bed: '',
    })

    const handleChange = (e) => {
        const { name, value, type } = e.target
        setForm(prev => ({
            ...prev,
            [name]: type === 'number' ? Number(value) : value,
        }))
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)
        setError('')
        try {
            await client.post('/patients', form)
            onPatientAdded?.()
            onClose?.()
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to add patient')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Overlay */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="relative glass-card w-full max-w-lg p-6 animate-slide-down">
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-medical-blue/20 rounded-lg">
                            <UserPlus className="w-5 h-5 text-medical-blue-light" />
                        </div>
                        <h2 className="text-lg font-semibold text-white">Add New Patient</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {error && (
                    <div className="mb-4 p-3 bg-critical/10 border border-critical/30 rounded-lg text-sm text-critical-light">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-1.5">
                            Patient Name
                        </label>
                        <input
                            type="text"
                            name="name"
                            value={form.name}
                            onChange={handleChange}
                            placeholder="Enter patient name"
                            required
                            className="input-field"
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-1.5">
                                GA at Birth (weeks)
                            </label>
                            <input
                                type="number"
                                name="ga_at_birth"
                                value={form.ga_at_birth}
                                onChange={handleChange}
                                min={22}
                                max={42}
                                required
                                className="input-field"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-1.5">
                                Days in NICU
                            </label>
                            <input
                                type="number"
                                name="days_in_nicu"
                                value={form.days_in_nicu}
                                onChange={handleChange}
                                min={0}
                                max={365}
                                required
                                className="input-field"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-1.5">
                            Bed Number
                        </label>
                        <input
                            type="text"
                            name="bed"
                            value={form.bed}
                            onChange={handleChange}
                            placeholder="e.g. NICU-A3"
                            required
                            className="input-field"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-1.5">
                            Diagnosis
                        </label>
                        <input
                            type="text"
                            name="diagnosis"
                            value={form.diagnosis}
                            onChange={handleChange}
                            placeholder="e.g. Respiratory Distress Syndrome"
                            className="input-field"
                        />
                    </div>

                    <div className="flex gap-3 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 py-2.5 px-5 rounded-lg border border-border-dark text-gray-300 hover:bg-bg-dark hover:text-white transition-all font-medium"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading}
                            className="flex-1 btn-primary flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Adding...
                                </>
                            ) : (
                                <>
                                    <UserPlus className="w-4 h-4" />
                                    Add Patient
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}
