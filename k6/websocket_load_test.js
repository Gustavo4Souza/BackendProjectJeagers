/**
 * k6 Load Test — EH Brewing WebSocket
 *
 * Validates that 8 simultaneous WebSocket connections (one per tank) remain
 * stable under load while a continuous stream of readings is published.
 *
 * Run:
 *   k6 run k6/websocket_load_test.js
 *
 * Override API URL:
 *   k6 run -e API_URL=http://my-server:8000 k6/websocket_load_test.js
 */

import ws from 'k6/ws'
import http from 'k6/http'
import { check, sleep } from 'k6'
import { Counter, Rate, Trend } from 'k6/metrics'

// ── Config ────────────────────────────────────────────────────────────────────

const API_URL = __ENV.API_URL || 'http://localhost:8000'
const WS_URL  = __ENV.WS_URL  || 'ws://localhost:8000'

// One VU per tank — exactly 8 simultaneous connections
export const options = {
  scenarios: {
    websocket_connections: {
      executor: 'constant-vus',
      vus: 8,
      duration: '30s',
    },
  },
  thresholds: {
    // All connections must stay up
    ws_connecting: ['p(95)<500'],
    // At least 95% of messages must arrive within 2s
    ws_msg_receive_time: ['p(95)<2000'],
    // Zero connection errors allowed
    ws_errors: ['count==0'],
    // HTTP readings must succeed
    http_req_failed: ['rate<0.01'],
  },
}

// ── Custom metrics ─────────────────────────────────────────────────────────────

const wsErrors        = new Counter('ws_errors')
const messagesReceived = new Counter('ws_messages_received')
const msgReceiveTime  = new Trend('ws_msg_receive_time')
const connectionRate  = new Rate('ws_connection_success')

// ── Credentials ───────────────────────────────────────────────────────────────

function getToken() {
  const loginResp = http.post(
    `${API_URL}/auth/login`,
    JSON.stringify({ username: 'admin', password: 'admin123' }),
    { headers: { 'Content-Type': 'application/json' } },
  )

  const ok = check(loginResp, {
    'login status 200': (r) => r.status === 200,
    'login has access_token': (r) => JSON.parse(r.body).access_token !== undefined,
  })

  if (!ok) return null
  return JSON.parse(loginResp.body).access_token
}

// ── Main VU function ──────────────────────────────────────────────────────────

export default function () {
  // Each VU maps to one tank (tank IDs 1–8)
  const tankId = (__VU % 8) + 1

  const token = getToken()
  if (!token) {
    wsErrors.add(1)
    return
  }

  const authHeaders = { Authorization: `Bearer ${token}` }
  const wsEndpoint  = `${WS_URL}/ws/tanks/${tankId}`

  const sendTestReading = () => {
    const temperature = 10 + Math.random() * 15
    http.post(
      `${API_URL}/api/v1/readings`,
      JSON.stringify({ tank_id: tankId, temperature: parseFloat(temperature.toFixed(2)) }),
      { headers: { 'Content-Type': 'application/json', ...authHeaders } },
    )
  }

  const connectionStart = Date.now()

  const result = ws.connect(wsEndpoint, { headers: authHeaders }, function (socket) {
    connectionRate.add(1)

    socket.on('open', () => {
      check(socket, { 'WebSocket connected': () => true })

      // Send a reading every 2 seconds to produce messages on this socket
      socket.setInterval(() => {
        sendTestReading()
      }, 2000)

      // Close after 25s (test duration is 30s)
      socket.setTimeout(() => {
        socket.close()
      }, 25000)
    })

    socket.on('message', (data) => {
      messagesReceived.add(1)
      const latency = Date.now() - connectionStart
      msgReceiveTime.add(latency)

      const payload = JSON.parse(data)
      check(payload, {
        'message has tank_id':     (p) => p.tank_id !== undefined,
        'message has temperature': (p) => p.temperature !== undefined,
        'message has recorded_at': (p) => p.recorded_at !== undefined,
      })
    })

    socket.on('error', (err) => {
      wsErrors.add(1)
      check(err, { 'no WS error': () => false })
    })

    socket.on('close', () => {
      check(null, { 'WebSocket closed cleanly': () => true })
    })
  })

  check(result, { 'ws connect returned status 101': (r) => r && r.status === 101 })

  sleep(1)
}

// ── Setup: seed tanks if needed ───────────────────────────────────────────────

export function setup() {
  const loginResp = http.post(
    `${API_URL}/auth/login`,
    JSON.stringify({ username: 'admin', password: 'admin123' }),
    { headers: { 'Content-Type': 'application/json' } },
  )

  if (loginResp.status !== 200) {
    console.warn('Could not log in during setup — make sure the API is running and admin user exists.')
    console.warn('Run: docker compose exec backend python api/scripts/seed_tanks.py --admin-password admin123')
    return
  }

  const token = JSON.parse(loginResp.body).access_token
  const authHeaders = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  const tanksResp = http.get(`${API_URL}/api/v1/tanks`, { headers: authHeaders })
  const tanks = JSON.parse(tanksResp.body)
  console.log(`Setup: found ${tanks.length} tanks registered.`)

  if (tanks.length < 8) {
    console.warn('Warning: fewer than 8 tanks found. Run seed_tanks.py to seed the database.')
  }
}
