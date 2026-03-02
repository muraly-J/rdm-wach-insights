import axios from 'axios'

// Use relative paths for localhost development
// Frontend (port 3000) communicates with backend (port 8081) via /api endpoints
const api = axios.create({
  baseURL: '/api',
  timeout: 60000,   // 60s — LLM + InfluxDB can be slow
  headers: {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',  // helps backend distinguish browser requests
  },
})

export default api