import { useState, useCallback } from 'react'
import axios from 'axios'
import ChatPanel from './components/ChatPanel.jsx'
import OutputPanel from './components/OutputPanel.jsx'

const SESSION_ID = crypto.randomUUID()

export default function App() {
  const [messages, setMessages] = useState([
    {
      id: '0',
      role: 'assistant',
      text: 'Ask me about AHU energy performance in the WACH ward. Try one of the example queries on the left, or type your own.',
    }
  ])
  const [currentResult, setCurrentResult] = useState(null)
  const [isLoading, setIsLoading]         = useState(false)

  const addMessage = useCallback((role, text, isError = false) => {
    const msg = {
      id:   crypto.randomUUID(),
      role: isError ? 'error' : role,
      text,
      time: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
    }
    setMessages(prev => [...prev, msg])
  }, [])

  const handleQuery = useCallback(async (query) => {
    if (!query.trim() || isLoading) return

    addMessage('user', query)
    setIsLoading(true)
    setCurrentResult(null)

    try {
      const { data } = await axios.post('/api/query', {
        user_query: query,
        session_id: SESSION_ID,
      })

      setCurrentResult(data)

      const label = data.query_type === 'time_series'
        ? `${data.device_ids.join(', ')} · ${data.metric.replace(/_/g, ' ')} · ${data.time_range.replace(/_/g, ' ')}`
        : `Top ${data.chart?.data?.length ?? '?'} devices · ${data.metric.replace(/_/g, ' ')} · ${data.time_range.replace(/_/g, ' ')}`

      addMessage('assistant', `Done — ${label}`)

    } catch (err) {
      const errMsg     = err.response?.data?.error      || 'Something went wrong. Please try again.'
      const suggestion = err.response?.data?.suggestion || null
      addMessage('assistant', suggestion ? `${errMsg}\n\n${suggestion}` : errMsg, true)
      setCurrentResult(null)
    } finally {
      setIsLoading(false)
    }
  }, [isLoading, addMessage])

  const handleClear = useCallback(() => {
    setMessages([{
      id:   crypto.randomUUID(),
      role: 'assistant',
      text: 'Chat cleared. Ask me about AHU energy performance in the WACH ward.',
    }])
    setCurrentResult(null)
  }, [])

  return (
    <div className="app">
      <header className="header">
        <div className="header-logo">
          <div className="header-logo-mark">
            <svg viewBox="0 0 16 16" fill="none">
              <path d="M2 8h3l2-5 2 10 2-5h3" stroke="#0a0e1a" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <div className="header-title">WACH Insight</div>
          </div>
        </div>
        <div className="header-subtitle">Women &amp; Child Ward · Hospital KL · AHU Analytics</div>
        <div className="header-status">
          <div className="status-dot" />
          LIVE
        </div>
      </header>

      <div className="body">
        <ChatPanel
          messages={messages}
          isLoading={isLoading}
          onQuery={handleQuery}
          onClear={handleClear}
        />
        <OutputPanel result={currentResult} isLoading={isLoading} />
      </div>
    </div>
  )
}