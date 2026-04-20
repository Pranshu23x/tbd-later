import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

const Simulation = () => {
  const [input, setInput] = useState('')
  const navigate = useNavigate()

  const handleSearch = () => {
    if (input.trim()) {
      navigate(`/run?query=${encodeURIComponent(input)}`)
    }
  }

  return (
    <div className="sim-page">
      {/* Sidebar */}
      <aside className="sim-sidebar">
        <div className="sim-sidebar-header">
          <Link to="/" className="nav-logo" style={{ color: 'white', textDecoration: 'none' }}>reflex</Link>
          <button className="new-chat-btn" onClick={() => setInput('')}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            New Simulation
          </button>
        </div>
        <div className="sim-history">
          <div className="label-micro" style={{ padding: '0 1rem', marginBottom: '0.5rem' }}>Recent History</div>
          <div className="history-item">US Fintech Market Analysis</div>
          <div className="history-item">SaaS Rivalry Map</div>
          <div className="history-item">AI Infrastructure War</div>
        </div>
        <div className="sim-sidebar-footer">
          <div className="user-profile">
            <div className="user-avatar">JD</div>
            <span>John Doe</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="sim-main">
        <div className="sim-center-content">
          <div className="sim-welcome">
            <h1 style={{ fontSize: '2rem', marginBottom: '1rem', letterSpacing: '-1px' }}>What should we simulate today?</h1>
            <p style={{ color: '#767d88' }}>Ask about market niches, rivals, or executive survival plans.</p>
          </div>
          
          <div className="sim-input-wrapper">
            <textarea 
              className="sim-input"
              placeholder="Ask Reflex..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              rows="1"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSearch();
                }
              }}
              onInput={(e) => {
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
              }}
            />
            <button 
              className="sim-send-btn" 
              disabled={!input.trim()}
              onClick={handleSearch}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </div>
          
          <div className="sim-footer-note orange-highlighter">
            Reflex may ground simulations in real-time Crustdata. Use with strategic discretion.
          </div>
        </div>
      </main>
    </div>
  )
}

export default Simulation
