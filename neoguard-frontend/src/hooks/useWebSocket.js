import { useState, useEffect, useRef } from 'react'

export function useWebSocket(patientId) {
  const [vitals, setVitals] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [connected, setConnected] = useState(false)
  const [history, setHistory] = useState([])
  const [cga, setCga] = useState(null)
  const [phase, setPhase] = useState(null)
  const [gaCat, setGaCat] = useState(null)

  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)

  useEffect(() => {
    if (!patientId) return

    const WS_URL = `ws://localhost:8000/ws/${patientId}`

    const connect = () => {
      try {
        const ws = new WebSocket(WS_URL)

        ws.onopen = () => {
          setConnected(true)
          console.log(`WebSocket connected for patient ${patientId}`)
        }

        ws.onmessage = (event) => {
          const data = JSON.parse(event.data)

          if (data.type === 'vitals') {
            setVitals(data.vitals)
            setAlerts(data.alerts || [])
            setCga(data.cga)
            setPhase(data.phase)
            setGaCat(data.ga_cat)

            // Keep last 60 vitals
            setHistory(prev => {
              const updated = [...prev, data.vitals]
              return updated.slice(-60)
            })

            // Play alert sound if CRITICAL
            if (data.alerts?.some(a => a.severity === 'CRITICAL')) {
              playAlertSound()
            }
          } else if (data.type === 'alert_acknowledged') {
            setAlerts(prev => prev.map(a =>
              a.alert_id === data.alert_id
                ? { ...a, acknowledged: true, acknowledged_by: data.acknowledged_by, acknowledged_at: data.acknowledged_at }
                : a
            ))
          }
        }

        ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          setConnected(false)
        }

        ws.onclose = () => {
          setConnected(false)
          console.log('WebSocket closed, reconnecting...')
          reconnectTimeoutRef.current = setTimeout(connect, 3000)
        }

        wsRef.current = ws
      } catch (error) {
        console.error('WebSocket connection failed:', error)
        reconnectTimeoutRef.current = setTimeout(connect, 3000)
      }
    }

    connect()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [patientId])

  const playAlertSound = () => {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)()
      const oscillator = audioContext.createOscillator()
      const gainNode = audioContext.createGain()

      oscillator.connect(gainNode)
      gainNode.connect(audioContext.destination)

      oscillator.frequency.value = 800
      oscillator.type = 'sine'

      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1)

      oscillator.start(audioContext.currentTime)
      oscillator.stop(audioContext.currentTime + 0.1)
    } catch (error) {
      console.error('Alert sound failed:', error)
    }
  }

  return { vitals, alerts, connected, history, cga, phase, gaCat }
}
