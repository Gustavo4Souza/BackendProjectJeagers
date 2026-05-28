import { useEffect, useRef, useCallback } from 'react'
import type { Reading } from '../types'

const WS_BASE = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000'
const MAX_RECONNECT_MS = Number(import.meta.env.VITE_WS_RECONNECT_MAX_MS) || 30_000

export function useWebSocket(tankId: number, onReading: (reading: Reading) => void) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectDelay = useRef(1_000)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isMounted = useRef(true)
  const onReadingRef = useRef(onReading)
  const connectRef = useRef<(() => void) | null>(null)

  // Keep callback fresh without re-triggering the effect
  useEffect(() => {
    onReadingRef.current = onReading
  })

  const connect = useCallback(() => {
    if (!isMounted.current) return

    const ws = new WebSocket(`${WS_BASE}/ws/tanks/${tankId}`)
    wsRef.current = ws

    ws.onopen = () => {
      reconnectDelay.current = 1_000
    }

    ws.onmessage = (event: MessageEvent) => {
      try {
        const reading = JSON.parse(event.data as string) as Reading
        onReadingRef.current(reading)
      } catch {
        // ignore malformed frames
      }
    }

    ws.onclose = () => {
      if (!isMounted.current) return
      reconnectTimer.current = setTimeout(() => {
        reconnectDelay.current = Math.min(reconnectDelay.current * 2, MAX_RECONNECT_MS)
        connectRef.current?.()
      }, reconnectDelay.current)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [tankId])

  useEffect(() => {
    connectRef.current = connect
  }, [connect])

  useEffect(() => {
    isMounted.current = true
    connect()

    return () => {
      isMounted.current = false
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])
}
