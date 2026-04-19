import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'

const PLACEHOLDERS = [
  "Ask Reflex...",
  "B2B SaaS, 10–100 employees, >20% headcount growth in last 6 months...",
  "Portfolio health check: headcount and key exec departures in the last 30 days...",
  "Identify AI startups with sudden hiring spikes in GPU engineering roles..."
]

const Simulation = () => {
  const [input, setInput] = useState('')
  const [rounds, setRounds] = useState(3)
  const navigate = useNavigate()

  const [phText, setPhText] = useState('')
  const [phIndex, setPhIndex] = useState(0)
  const [charIndex, setCharIndex] = useState(0)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    const currentString = PLACEHOLDERS[phIndex]
    let timer

    if (isDeleting) {
      if (charIndex > 0) {
        timer = setTimeout(() => {
          setPhText(currentString.substring(0, charIndex - 1))
          setCharIndex(c => c - 1)
        }, 30) // Fast backspace
      } else {
        setIsDeleting(false)
        setPhIndex((p) => (p + 1) % PLACEHOLDERS.length)
      }
    } else {
      if (charIndex < currentString.length) {
        timer = setTimeout(() => {
          setPhText(currentString.substring(0, charIndex + 1))
          setCharIndex(c => c + 1)
        }, 60) // Typing speed
      } else {
        timer = setTimeout(() => {
          setIsDeleting(true)
        }, 2500) // Pause before deleting
      }
    }
    return () => clearTimeout(timer)
  }, [charIndex, isDeleting, phIndex])

  const handleSearch = () => {
    if (input.trim()) {
      navigate(`/run?query=${encodeURIComponent(input)}&rounds=${rounds}`)
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
        
        <div style={{ padding: '1rem', borderBottom: '1px solid #222', marginBottom: '1rem' }}>
          <div className="label-micro" style={{ marginBottom: '0.8rem', color: '#a1a1aa' }}>Simulation Settings</div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '13px', color: '#e4e4e7' }}>Debate Rounds</span>
            <span style={{ fontSize: '13px', fontWeight: 'bold', color: 'var(--brand-orange)' }}>{rounds}</span>
          </div>
          <input 
            type="range" 
            min="1" max="10" 
            value={rounds} 
            onChange={(e) => setRounds(parseInt(e.target.value))}
            style={{ width: '100%', accentColor: 'var(--brand-orange)' }}
          />
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
              placeholder={phText || ' '}
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
          
          <div style={{ display: 'flex', gap: '0.8rem', flexWrap: 'wrap', marginTop: '1.5rem', justifyContent: 'center', width: '100%' }}>
            {[
              "B2B SaaS, 10–100 employees, >20% headcount growth in last 6 months, EU-based, no US VC funding yet.",
              "Portfolio health check: headcount and key exec departures in the last 30 days",
              "Identify AI startups with sudden hiring spikes in GPU engineering roles"
            ].map((s, idx) => (
              <div 
                key={idx} 
                onClick={() => setInput(s)}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  padding: '8px 14px',
                  borderRadius: '20px',
                  fontSize: '12px',
                  color: '#a1a1aa',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  maxWidth: '100%',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                }}
                onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'; e.currentTarget.style.color = '#fff'; }}
                onMouseOut={(e) => { e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'; e.currentTarget.style.color = '#a1a1aa'; }}
              >
                {s.length > 60 ? s.slice(0, 60) + '...' : s}
              </div>
            ))}
          </div>
          
          <div className="sim-footer-note orange-highlighter">
            Reflex ground in real-time using Crustdata so Agents dont hallucinate. Use with strategic discretion.
          </div>
        </div>
      </main>
    </div>
  )
}

export default Simulation
