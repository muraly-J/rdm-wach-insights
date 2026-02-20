import { useState, useCallback } from 'react'
<<<<<<< HEAD
import axios from 'axios'
import ChatPanel from './components/ChatPanel.jsx'
import OutputPanel from './components/OutputPanel.jsx'
=======
import api from './api.js'
import ChatView from './components/ChatView.jsx'
import { MAPPED_COUNT } from './deviceMap.js'
>>>>>>> dev

const SESSION_ID = crypto.randomUUID()

export default function App() {
  const [messages, setMessages] = useState([
    {
      id: '0',
      role: 'assistant',
<<<<<<< HEAD
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

=======
      text: 'Ask me about AHU energy performance in the WACH ward. Try one of the examples below, or type your own query.',
      result: null,
    }
  ])
  const [isLoading, setIsLoading] = useState(false)

>>>>>>> dev
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
<<<<<<< HEAD
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
=======
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
>>>>>>> dev
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
            className="unmapped-badge"
            title={`${MAPPED_COUNT} of ~150 device IDs have confirmed location records. Some devices in the database could not be matched to a department — their IDs will still appear in results but without a location name.`}
          >
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
<<<<<<< HEAD

      <div className="body">
        <ChatPanel
          messages={messages}
          isLoading={isLoading}
          onQuery={handleQuery}
          onClear={handleClear}
        />
        <OutputPanel result={currentResult} isLoading={isLoading} />
      </div>
=======
      <ChatView
        messages={messages}
        isLoading={isLoading}
        onQuery={handleQuery}
        onClear={handleClear}
      />
>>>>>>> dev
    </div>
  )
}