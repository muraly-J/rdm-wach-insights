import { useState, useRef, useEffect } from 'react'

const EXAMPLE_QUERIES = [
  'Rank top 10 by power this month',
  'Show e0101 energy last 7 days',
  'Compare e0101 vs e0206 power today',
  'e0405 and e0410 and e0411 power last 7 days',
  'Show e0206 voltage today',
  'Top 5 by reactive power all time',
]

const METRICS = [
  'power_total', 'energy_import', 'power_factor_avg', 'current_avg',
  'volts_l_n_avg', 'apparent_power_total', 'power_demand', 'reactive_power_total',
]

export default function ChatPanel({ messages, isLoading, onQuery, onClear, className }) {
  const [input, setInput]           = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const messagesEndRef  = useRef(null)
  const textareaRef     = useRef(null)
  const recognitionRef  = useRef(null)

  // Auto-focus input on mount
  useEffect(() => { textareaRef.current?.focus() }, [])

  // Auto-scroll to bottom whenever messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = `${Math.min(ta.scrollHeight, 120)}px`
  }, [input])

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  function submit() {
    const q = input.trim()
    if (!q || isLoading) return
    onQuery(q)
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = '42px'
  }

  function handleChipClick(text) {
    onQuery(text)
  }

  function handleUserMessageClick(text) {
    if (!isLoading) onQuery(text)
  }

  function toggleVoice() {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      alert('Voice input is not supported in this browser. Try Chrome.')
      return
    }
    if (isRecording) {
      recognitionRef.current?.stop()
      setIsRecording(false)
      return
    }
    const SR  = window.SpeechRecognition || window.webkitSpeechRecognition
    const rec = new SR()
    rec.lang            = 'en-US'
    rec.interimResults  = false
    rec.maxAlternatives = 1
    rec.onresult = (e) => {
      const transcript = e.results[0][0].transcript
      setInput(prev => prev ? `${prev} ${transcript}` : transcript)
    }
    rec.onend   = () => setIsRecording(false)
    rec.onerror = () => setIsRecording(false)
    rec.start()
    recognitionRef.current = rec
    setIsRecording(true)
  }

  return (
    <div className={`chat-panel${className ? ' ' + className : ''}`}>

      {/* Instruction banner */}
      <div className="instruction-banner">
        <div className="banner-header">
          <h3>Example Queries</h3>
          <button className="clear-btn" onClick={onClear} title="Clear chat">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
              <path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/>
            </svg>
            Clear
          </button>
        </div>
        <div className="instruction-chips">
          {EXAMPLE_QUERIES.map(q => (
            <button key={q} className="chip" onClick={() => handleChipClick(q)} disabled={isLoading}>{q}</button>
          ))}
        </div>
        <div className="metrics-list">
          {METRICS.map(m => <span key={m} className="metric-tag">{m}</span>)}
        </div>
      </div>

      {/* Messages */}
      <div className="messages">
        {messages.map(msg => (
          <div key={msg.id} className={`message ${msg.role}`}>
            <div
              className={`message-bubble ${msg.role === 'user' && !isLoading ? 'clickable' : ''}`}
              style={{ whiteSpace: 'pre-wrap' }}
              onClick={() => msg.role === 'user' && handleUserMessageClick(msg.text)}
              title={msg.role === 'user' ? 'Click to re-run' : undefined}
            >
              {msg.text}
            </div>
            {msg.time && <span className="message-time">{msg.time}</span>}
          </div>
        ))}

        {isLoading && (
          <div className="message assistant">
            <div className="thinking">
              <div className="thinking-dots"><span /><span /><span /></div>
              querying...
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="input-area">
        <div className="input-row">
          <textarea
            ref={textareaRef}
            className="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about AHU energy performance..."
            rows={1}
            disabled={isLoading}
          />
          <button
            className={`mic-btn ${isRecording ? 'recording' : ''}`}
            onClick={toggleVoice}
            title={isRecording ? 'Stop recording' : 'Voice input'}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" y1="19" x2="12" y2="23"/>
              <line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
          </button>
          <button
            className="send-btn"
            onClick={submit}
            disabled={isLoading || !input.trim()}
            title="Send"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </div>
        <p className="input-hint">Enter to send · Shift+Enter for new line · Click a past query to re-run</p>
      </div>
    </div>
  )
}