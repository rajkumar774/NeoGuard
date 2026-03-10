import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Heart, Eye, EyeOff, Loader2, Stethoscope, Shield } from 'lucide-react'

export default function LoginPage() {
    const navigate = useNavigate()
    const { login } = useAuth()
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [role, setRole] = useState('doctor')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)
        setError('')

        const result = await login(username, password)
        if (result.success) {
            navigate('/dashboard')
        } else {
            setError(result.error)
        }
        setLoading(false)
    }

    return (
        <div className="min-h-screen bg-bg-dark flex items-center justify-center p-4 relative overflow-hidden">
            {/* Background decoration */}
            <div className="absolute inset-0 overflow-hidden">
                <div className="absolute -top-40 -right-40 w-80 h-80 bg-medical-blue/5 rounded-full blur-3xl" />
                <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-medical-blue/5 rounded-full blur-3xl" />
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-medical-blue/3 rounded-full blur-3xl" />
            </div>

            {/* Grid pattern overlay */}
            <div
                className="absolute inset-0 opacity-[0.02]"
                style={{
                    backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
                    backgroundSize: '50px 50px',
                }}
            />

            <div className="relative w-full max-w-md animate-fade-in">
                {/* Logo & Header */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center p-4 bg-medical-blue/10 rounded-2xl mb-4 animate-glow">
                        <Heart className="w-12 h-12 text-medical-blue-light" />
                    </div>
                    <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">
                        Neo<span className="text-medical-blue-light">Guard</span>
                    </h1>
                    <p className="text-gray-400 text-sm">
                        AI-Powered Neonatal Monitoring
                    </p>
                </div>

                {/* Login Card */}
                <div className="glass-card p-8">
                    {/* Role Selection */}
                    <div className="flex gap-3 mb-6">
                        <button
                            type="button"
                            onClick={() => setRole('doctor')}
                            className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-lg border text-sm font-medium transition-all ${role === 'doctor'
                                    ? 'bg-medical-blue/20 border-medical-blue text-medical-blue-light'
                                    : 'border-border-dark text-gray-400 hover:border-border-light hover:text-gray-300'
                                }`}
                        >
                            <Stethoscope className="w-4 h-4" />
                            Doctor
                        </button>
                        <button
                            type="button"
                            onClick={() => setRole('nurse')}
                            className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-lg border text-sm font-medium transition-all ${role === 'nurse'
                                    ? 'bg-normal/20 border-normal text-normal-light'
                                    : 'border-border-dark text-gray-400 hover:border-border-light hover:text-gray-300'
                                }`}
                        >
                            <Shield className="w-4 h-4" />
                            Nurse
                        </button>
                    </div>

                    {error && (
                        <div className="mb-4 p-3 bg-critical/10 border border-critical/30 rounded-lg text-sm text-critical-light animate-slide-down">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-1.5">
                                Username
                            </label>
                            <input
                                type="text"
                                value={username}
                                onChange={e => setUsername(e.target.value)}
                                placeholder="Enter username"
                                required
                                className="input-field"
                                autoFocus
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-1.5">
                                Password
                            </label>
                            <div className="relative">
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    placeholder="Enter password"
                                    required
                                    className="input-field pr-11"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                                >
                                    {showPassword ? (
                                        <EyeOff className="w-4 h-4" />
                                    ) : (
                                        <Eye className="w-4 h-4" />
                                    )}
                                </button>
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full btn-primary py-3 flex items-center justify-center gap-2 text-base disabled:opacity-50 mt-6"
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Signing in...
                                </>
                            ) : (
                                'Sign In'
                            )}
                        </button>
                    </form>

                    {/* Demo Credentials */}
                    <div className="mt-6 pt-5 border-t border-border-dark">
                        <p className="text-xs text-gray-500 text-center mb-3 uppercase tracking-wider font-medium">
                            Demo Credentials
                        </p>
                        <div className="grid grid-cols-2 gap-3">
                            <button
                                onClick={() => {
                                    setUsername('dr.smith')
                                    setPassword('doctor123')
                                    setRole('doctor')
                                }}
                                className="p-2.5 rounded-lg bg-bg-dark/50 border border-border-dark hover:border-medical-blue/50 transition-all text-left group cursor-pointer"
                            >
                                <p className="text-xs text-gray-400 group-hover:text-medical-blue-light transition-colors">
                                    <Stethoscope className="w-3 h-3 inline mr-1" />
                                    Doctor
                                </p>
                                <p className="text-xs text-gray-500 font-mono mt-0.5">dr.smith</p>
                            </button>
                            <button
                                onClick={() => {
                                    setUsername('nurse.raj')
                                    setPassword('nurse123')
                                    setRole('nurse')
                                }}
                                className="p-2.5 rounded-lg bg-bg-dark/50 border border-border-dark hover:border-normal/50 transition-all text-left group cursor-pointer"
                            >
                                <p className="text-xs text-gray-400 group-hover:text-normal-light transition-colors">
                                    <Shield className="w-3 h-3 inline mr-1" />
                                    Nurse
                                </p>
                                <p className="text-xs text-gray-500 font-mono mt-0.5">nurse.raj</p>
                            </button>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <p className="text-center mt-6 text-xs text-gray-600">
                    Secure medical monitoring platform • HIPAA Compliant
                </p>
            </div>
        </div>
    )
}
