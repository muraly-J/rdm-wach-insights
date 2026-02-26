import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// Suppress recharts prop warnings (harmless internal props)
const originalWarn = console.warn
console.warn = function(...args) {
  if (args[0]?.includes('does not recognize the') && args[0]?.includes('prop')) {
    // Skip recharts prop warnings
    return
  }
  originalWarn.apply(console, args)
}

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>,
)
