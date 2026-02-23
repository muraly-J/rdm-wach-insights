import { useState, useCallback } from 'react'
import api from './api.js'
import ChatView from './components/ChatView.jsx'
import ElectricalRiskView from './components/ElectricalRiskView.jsx'
import { MAPPED_COUNT } from './deviceMap.js'

const SESSION_ID = crypto.randomUUID()

export default function App() {
  const [showRiskCheck, setShowRiskCheck] = useState(false)
  const [messages, setMessages] = useState([
    {
      id: '0',
      role: 'assistant',
      text: 'Ask me about AHU energy performance in the WACH ward. Try one of the examples below, or type your own query.',
      result: null,
    }
  ])
  const [isLoading, setIsLoading] = useState(false)

  // Standard analytics query → LLM translator → InfluxDB
  const handleQuery = useCallback(async (query) => {
    if (!query.trim() || isLoading) return
    const userMsg    = { id: crypto.randomUUID(), role: 'user',      text: query, result: null }
    const assistantId = crypto.randomUUID()
    const pendingMsg = { id: assistantId,         role: 'assistant', text: null,  result: null }
    setMessages(prev => [...prev, userMsg, pendingMsg])
    setIsLoading(true)
    try {
      const response = await api.post('/api/query', { user_query: query, session_id: SESSION_ID })
      const data = response.data
      setMessages(prev => prev.map(m => m.id === assistantId ? {
        ...m,
        text: data.query_type === 'time_series'
          ? `${data.device_ids.join(', ')} · ${data.metric} · ${data.time_range.replace(/_/g, ' ')}`
          : `Top ${data.chart?.data?.length ?? '?'} devices · ${data.metric} · ${data.time_range.replace(/_/g, ' ')}`,
        result: data,
      } : m))
    } catch (err) {
      const msg = err.response?.data?.error || 'Something went wrong. Please try again.'
      const suggestion = err.response?.data?.suggestion
      setMessages(prev => prev.map(m => m.id === assistantId ? {
        ...m, role: 'error',
        text: suggestion ? `${msg}\n\n${suggestion}` : msg,
        result: null,
      } : m))
    } finally {
      setIsLoading(false)
    }
  }, [isLoading])

  // Forecast query → directly to /api/forecast/:device_id, bypasses LLM
  const handleForecast = useCallback(async (deviceId) => {
    if (isLoading) return
    const userMsg    = { id: crypto.randomUUID(), role: 'user',      text: `24-hour power forecast for ${deviceId}`, result: null }
    const assistantId = crypto.randomUUID()
    const pendingMsg = { id: assistantId,         role: 'assistant', text: null, result: null }
    setMessages(prev => [...prev, userMsg, pendingMsg])
    setIsLoading(true)
    try {
      const response = await api.get(`/api/forecast/${deviceId}`)
      const data = response.data
      setMessages(prev => prev.map(m => m.id === assistantId ? {
        ...m,
        text: `Forecast · ${deviceId} · next 24 hours`,
        result: data,
      } : m))
    } catch (err) {
      const msg = err.response?.data?.error || 'Forecast failed. Please try again.'
      const suggestion = err.response?.data?.suggestion
      setMessages(prev => prev.map(m => m.id === assistantId ? {
        ...m, role: 'error',
        text: suggestion ? `${msg}\n\n${suggestion}` : msg,
        result: null,
      } : m))
    } finally {
      setIsLoading(false)
    }
  }, [isLoading])

  const handleClear = useCallback(() => {
    setMessages([{
      id: crypto.randomUUID(),
      role: 'assistant',
      text: 'Ask me about AHU energy performance in the WACH ward. Try one of the examples below, or type your own query.',
      result: null,
    }])
  }, [])

  return (
    <div className="app">
      <header className="header">
        <div className="header-logo">
          <div className="header-logo-mark">
            <svg viewBox="0 0 16 16" fill="none">
              <path d="M2 8h3l2-5 2 10 2-5h3" stroke="#0a0e1a" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div>
            <div className="header-title">WACH Insight</div>
            <div className="header-subtitle">Women &amp; Child Ward · Hospital KL · AHU Analytics</div>
          </div>
        </div>
        <div className="header-right">
          <div
            onClick={() => setShowRiskCheck(!showRiskCheck)}
            className="unmapped-badge"
            style={{ cursor: 'pointer', border: '1px solid #3b82f655', color: '#3b82f6', background: '#3b82f60a' }}
          >
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="2" y1="12" x2="22" y2="12" />
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
            {showRiskCheck ? 'Back to Chat' : 'Electrical Risk Check'}
          </div>
          <div className="unmapped-badge"
            title={`${MAPPED_COUNT} of ~150 device IDs have confirmed location records. Some devices could not be matched to a department.`}>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            Some devices unidentified
          </div>
          <div className="header-status">
            <div className="status-dot" />
            LIVE
          </div>
        </div>
      </header>
      {showRiskCheck ? (
        <ElectricalRiskView />
      ) : (
        <ChatView
          messages={messages}
          isLoading={isLoading}
          onQuery={handleQuery}
          onForecast={handleForecast}
          onClear={handleClear}
        />
      )}
    </div>
  )
}
