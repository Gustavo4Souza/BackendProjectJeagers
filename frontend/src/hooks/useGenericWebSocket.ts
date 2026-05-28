import { useEffect, useRef, useCallback } from 'react'

const WS_BASE = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000'
const MAX_RECONNECT_MS = Number(import.meta.env.VITE_WS_RECONNECT_MAX_MS) || 30_000

export function useGenericWebSocket<T>(path: string, onMessage: (data: T) => void) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectDelay = useRef(1_000)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isMounted = useRef(true)
  const onMessageRef = useRef(onMessage)
  const connectRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    onMessageRef.current = onMessage
  })

  const connect = useCallback(() => {
    if (!isMounted.current) return

    const ws = new WebSocket(`${WS_BASE}${path}`)
    wsRef.current = ws

    ws.onopen = () => {
      reconnectDelay.current = 1_000
    }

    ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string) as T
        onMessageRef.current(data)
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
  }, [path])

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
