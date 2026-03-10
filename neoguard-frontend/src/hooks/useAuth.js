import { useState, useCallback, useEffect } from 'react'
import client from '../api/client'

export function useAuth() {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    const storedToken = localStorage.getItem('neoguard_token')
    const storedUser = localStorage.getItem('neoguard_user')
    const storedRole = localStorage.getItem('neoguard_role')
    
    if (storedToken && storedUser) {
      setToken(storedToken)
      setUser({
        full_name: storedUser,
        role: storedRole,
      })
      setIsAuthenticated(true)
    }
  }, [])

  const login = useCallback(async (username, password) => {
    try {
      const response = await client.post('/auth/login', {
        username,
        password,
      })
      const { access_token, full_name, role } = response.data
      
      localStorage.setItem('neoguard_token', access_token)
      localStorage.setItem('neoguard_user', full_name)
      localStorage.setItem('neoguard_role', role)
      
      setToken(access_token)
      setUser({ full_name, role })
      setIsAuthenticated(true)
      
      return { success: true }
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Invalid credentials' 
      }
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('neoguard_token')
    localStorage.removeItem('neoguard_user')
    localStorage.removeItem('neoguard_role')
    setToken(null)
    setUser(null)
    setIsAuthenticated(false)
    window.location.href = '/'
  }, [])

  return { user, token, login, logout, isAuthenticated }
}
