import { useAuth } from '../hooks/useAuth'
import { LogOut, Heart, Bell, LayoutDashboard } from 'lucide-react'
import { useNavigate, useLocation } from 'react-router-dom'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const navLinks = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/alerts', label: 'Alerts', icon: Bell },
  ]

  return (
    <nav className="bg-bg-card/80 backdrop-blur-lg border-b border-border-dark sticky top-0 z-50 no-print">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div
            className="flex items-center gap-2.5 cursor-pointer group"
            onClick={() => navigate('/dashboard')}
          >
            <div className="p-1.5 bg-medical-blue/20 rounded-lg group-hover:bg-medical-blue/30 transition-colors">
              <Heart className="text-medical-blue-light w-6 h-6 group-hover:animate-heartbeat" />
            </div>
            <div>
              <span className="text-lg font-bold text-white tracking-tight">NeoGuard</span>
              <span className="text-[10px] text-medical-blue-light block -mt-1 font-medium">
                AI-Powered NICU
              </span>
            </div>
          </div>

          {/* Nav Links */}
          <div className="flex items-center gap-1">
            {navLinks.map(({ path, label, icon: Icon }) => (
              <button
                key={path}
                onClick={() => navigate(path)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all ${location.pathname === path
                    ? 'bg-medical-blue/20 text-medical-blue-light'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </div>

          {/* User section */}
          <div className="flex items-center gap-4">
            {user && (
              <>
                <div className="text-right hidden sm:block">
                  <p className="text-white font-medium text-sm">{user.full_name}</p>
                  <p className="text-xs">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${user.role === 'doctor'
                          ? 'bg-blue-900/80 text-blue-200'
                          : 'bg-green-900/80 text-green-200'
                        }`}
                    >
                      {user.role}
                    </span>
                  </p>
                </div>
                <button
                  onClick={logout}
                  className="p-2 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white"
                  title="Logout"
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
