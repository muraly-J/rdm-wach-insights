import axios from 'axios'

// In production (Vercel), VITE_API_BASE is set to your Cloudflare tunnel URL.
// In development (npm run dev), it's empty so Vite proxy handles /api.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
  timeout: 60000,   // 60s — LLM + InfluxDB can be slow
  headers: {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',  // helps backend distinguish browser requests
  },
})

export default api