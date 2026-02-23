import axios from 'axios'

// In production (Vercel), use relative paths since frontend and backend are on same domain
// In development, use VITE_API_BASE if set (for Cloudflare tunnel), otherwise default to localhost
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 60000,   // 60s — LLM + InfluxDB can be slow
  headers: {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',  // helps backend distinguish browser requests
  },
})

export default api