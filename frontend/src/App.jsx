import { useState, useCallback } from 'react'
import api from './api.js'
import ChatView from './components/ChatView.jsx'

const SESSION_ID = crypto.randomUUID()

export default function App() {
  const [messages, setMessages] = useState([
    {
      id: '0',
      role: 'assistant',
      text: 'Ask me about AHU energy performance in the WACH ward. Try one of the examples below, or type your own query.',
      result: null,
    }
  ])
  const [isLoading, setIsLoading] = useState(false)

  const handleQuery = useCallback(async (query) => {
    if (!query.trim() || isLoading) return

    const userMsg = {
      id: crypto.randomUUID(),
      role: 'user',
      text: query,
      result: null,
    }
    const assistantId = crypto.randomUUID()
    const pendingMsg = {
      id: assistantId,
      role: 'assistant',
      text: null,
      result: null,
    }

    setMessages(prev => [...prev, userMsg, pendingMsg])
    setIsLoading(true)

    try {
      const response = await api.post('/api/query', {
        user_query: query,
        session_id: SESSION_ID,
      })
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
        ...m,
        role: 'error',
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
        <div className="header-status">
          <div className="status-dot" />
          LIVE
        </div>
      </header>

      <ChatView
        messages={messages}
        isLoading={isLoading}
        onQuery={handleQuery}
        onClear={handleClear}
      />
    </div>
  )
}