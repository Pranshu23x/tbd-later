import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

const Header = () => {
  const [isScrolled, setIsScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <header className={`app-header ${isScrolled ? 'scrolled' : ''}`}>
      <div className="nav-logo">reflex</div>
      <div className="nav-links">
        <a href="#" className="nav-link">Intelligence</a>
        <a href="#" className="nav-link">Data</a>
        <a href="#" className="nav-link">Architecture</a>
        <a href="#" className="nav-link">Memos</a>
      </div>
      <div className="nav-actions">
        <button className="btn btn-ghost">View Methodology</button>
        <Link to="/simulate" className="btn btn-primary" style={{ textDecoration: 'none' }}>Run Simulation</Link>
      </div>
    </header>
  )
}

const Hero = () => (
  <section className="hero">
    <div className="hero-container">
      <div className="hero-content">
        <h1 className="hero-title">Turn Market Signals into Investment Decisions</h1>
        <p style={{ fontSize: '1.25rem', marginBottom: '1.5rem', lineHeight: '1.4', opacity: 0.9 }}>
          Give Reflex a market thesis. It runs a Bull vs Bear debate on real data powered by <span className="text-purple-500 font-semibold">Crustdata</span> and delivers a clear investment decision with an action plan.
        </p>
        <div className="hero-list-item" style={{ marginBottom: '2.5rem', fontSize: '14px', letterSpacing: '1px' }}>
          Input → Debate → Decision → Execution
        </div>
        <Link to="/simulate" className="get-started-btn" style={{ textDecoration: 'none' }}>
          Run Simulation 
          <svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M8.14645 3.14645C8.34171 2.95118 8.65829 2.95118 8.85355 3.14645L12.8536 7.14645C13.0488 7.34171 13.0488 7.65829 12.8536 7.85355L8.85355 11.8536C8.65829 12.0488 8.34171 12.0488 8.14645 11.8536C7.95118 11.6583 7.95118 11.3417 8.14645 11.1464L11.2929 8H2.5C2.22386 8 2 7.77614 2 7.5C2 7.22386 2.22386 7 2.5 7H11.2929L8.14645 3.85355C7.95118 3.65829 7.95118 3.34171 8.14645 3.14645Z" fill="currentColor" fillRule="evenodd" clipRule="evenodd"></path>
          </svg>
        </Link>
      </div>
    </div>
  </section>
)

const WhatReflexDoes = () => (
  <section className="feature-grid-section">
    <div className="feature-statement">
      From Market Idea to Investment Decision
    </div>
    <div style={{ maxWidth: '800px', marginBottom: '4rem' }}>
      <p style={{ fontSize: '1.25rem', color: '#1a1a1a', marginBottom: '1.5rem' }}>Reflex takes a market filter like:</p>
      <div style={{ background: '#f5f5f5', padding: '1.5rem', borderRadius: '12px', fontStyle: 'italic', marginBottom: '2rem', borderLeft: '4px solid var(--brand-orange)' }}>
        “B2B SaaS, EU, 10–100 employees, &gt;20% growth, no US VC funding”
      </div>
      <p style={{ fontSize: '1.1rem', color: '#444' }}>It then:</p>
      <ul style={{ listStyle: 'none', padding: 0, marginTop: '1rem' }}>
        <li style={{ marginBottom: '.5rem' }}>• Finds matching companies using <span className="text-purple-500 font-semibold">Crustdata</span></li>
        <li style={{ marginBottom: '.5rem' }}>• Enriches them with real-time metrics</li>
        <li style={{ marginBottom: '.5rem' }}>• Runs a structured Bull vs Bear debate</li>
        <li style={{ marginBottom: '.5rem' }}>• Delivers a final decision with reasoning and next steps</li>
      </ul>
    </div>
  </section>
)

const CoreSystem = () => (
  <section className="research-section" style={{ paddingBottom: '4rem' }}>
    <div className="research-container">
      <div className="research-left">
        <div className="label-micro" style={{ marginBottom: '1.5rem', color: '#ffffff' }}>How Reflex Thinks</div>
        <h2 className="research-mission" style={{ fontSize: '2.5rem' }}>
          Adversarial Reasoning Powered by Real-Time Data
        </h2>
        <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: '1.1rem', marginBottom: '2rem' }}>
          Reflex replaces static research with adversarial AI decision-making.
        </p>
      </div>
      <div className="research-right">
        <div className="research-item">
          <div className="research-item-header">
            <h3>Multi-Agent Debate</h3>
          </div>
          <p>Three agents challenge each other: Bull finds upside, Bear identifies risks, and the Committee makes the final call. Every argument is backed by <span className="text-purple-500 font-semibold">Crustdata</span>.</p>
        </div>
        <div className="research-item">
          <div className="research-item-header">
            <h3>Real-Time Signals</h3>
          </div>
          <p>Grounding every claim in live headcount growth, hiring activity, and funding history from <span className="text-purple-500 font-semibold">Crustdata</span>. No generic insights. No guesswork.</p>
        </div>
        <div className="research-item">
          <div className="research-item-header">
            <h3>Strategy Context</h3>
          </div>
          <p>Relationships between companies and rivals are enriched with market context, ensuring decisions are made with full strategic awareness.</p>
        </div>
      </div>
    </div>
  </section>
)

const OutputSection = () => (
  <section className="feature-grid-section" style={{ background: '#fafafa' }}>
    <div className="feature-statement">What You Get</div>
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4rem' }}>
      <div>
        <p style={{ fontSize: '1.25rem', marginBottom: '1.5rem' }}>Reflex doesn’t give analysis. It gives decisions.</p>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          <li style={{ marginBottom: '.8rem' }}>• <strong>Invest / Pass verdict</strong></li>
          <li style={{ marginBottom: '.8rem' }}>• <strong>Key risks and opportunities</strong></li>
          <li style={{ marginBottom: '.8rem' }}>• <strong>Reasoning grounded in <span className="text-purple-500 font-semibold">Crustdata</span></strong></li>
          <li style={{ marginBottom: '.8rem' }}>• <strong>100-day action plan</strong></li>
          <li style={{ marginBottom: '.8rem' }}>• <strong>Reversal triggers (when to exit)</strong></li>
        </ul>
      </div>
      <div style={{ background: '#111', color: '#fff', padding: '2rem', borderRadius: '16px', fontSize: '13px', fontFamily: 'monospace' }}>
        <div style={{ color: 'var(--brand-orange)', marginBottom: '1rem' }}>// EXAMPLE OUTPUT</div>
        <div style={{ marginBottom: '.5rem' }}><strong>Decision:</strong> PASS on Huwise | CONSIDER Hypatos</div>
        <div style={{ marginBottom: '1rem' }}><strong>Why:</strong></div>
        <div style={{ marginBottom: '.2rem' }}>- Huwise → 2% growth (via Crustdata), no hiring → stalled</div>
        <div style={{ marginBottom: '1rem' }}>- Hypatos → 13.6% growth (via Crustdata) → actively scaling</div>
        <div style={{ marginBottom: '.5rem' }}><strong>Next Step:</strong> Verify burn rate before deploying capital</div>
        <div style={{ marginBottom: '.5rem' }}><strong>100-Day Plan:</strong> Track hiring velocity, Monitor runway</div>
        <div><strong>Reversal Trigger:</strong> Growth &lt; 10%, Runway &lt; 12mo</div>
      </div>
    </div>
  </section>
)

const FeatureGrid = () => (
  <section className="feature-grid-section">
    <div className="feature-statement" style={{ fontSize: '2rem', marginBottom: '3rem' }}>Built for Real Investment Decisions</div>
    <div className="feature-grid">
      <div className="feature-card">
        <div className="feature-image" style={{ background: 'linear-gradient(135deg, #1a1a1a, #000)', height: '200px' }}></div>
        <div className="feature-info">
          <h4>Multi-Agent Debate</h4>
          <p>Structured conflict between bullish and bearish perspectives, enforced by rigorous data protocols.</p>
        </div>
      </div>
      <div className="feature-card">
        <div className="feature-image" style={{ background: 'linear-gradient(135deg, #222, #111)', height: '200px' }}></div>
        <div className="feature-info">
          <h4>Live Data Enrichment</h4>
          <p>Every claim is backed by real-time signals from <span className="text-purple-500 font-semibold">Crustdata</span>.</p>
        </div>
      </div>
      <div className="feature-card">
        <div className="feature-image" style={{ background: 'linear-gradient(135deg, #111, #222)', height: '200px' }}></div>
        <div className="feature-info">
          <h4>Strategy Mapping</h4>
          <p>Understand how companies relate to competitors and markets using relationship-enriched graphs.</p>
        </div>
      </div>
      <div className="feature-card">
        <div className="feature-image" style={{ background: 'linear-gradient(135deg, #000, #1a1a1a)', height: '200px' }}></div>
        <div className="feature-info">
          <h4>Investment Memos</h4>
          <p>Board-ready outputs combining AI reasoning with verified market insights.</p>
        </div>
      </div>
    </div>
  </section>
)

const FinalCTA = () => (
  <section style={{ padding: '8rem 1.5rem', background: '#000', color: '#fff', textAlign: 'center' }}>
    <h2 style={{ fontSize: '3rem', fontWeight: 500, marginBottom: '2rem', letterSpacing: '-1.5px' }}>Stop Analyzing Markets. Start Stress-Testing Them.</h2>
    <Link to="/simulate" className="get-started-btn" style={{ margin: '0 auto', background: 'var(--brand-orange)', color: '#fff' }}>
      Run Your First Simulation
    </Link>
  </section>
)

const Footer = () => (
  <footer className="app-footer">
    <div className="footer-top">
      <div className="footer-column">
        <div className="label-micro">Project</div>
        <a href="https://github.com" className="footer-link">GitHub</a>
        <a href="#" className="footer-link">Watch Demo</a>
      </div>
      <div className="footer-column">
        <div className="label-micro">Company</div>
        <a href="#" className="footer-link">About Us</a>
        <a href="#" className="footer-link">Research</a>
      </div>
      <div className="footer-column">
        <div className="label-micro">Connect</div>
        <a href="#" className="footer-link">Twitter</a>
        <a href="#" className="footer-link">Discord</a>
      </div>
    </div>
    <div className="footer-bottom">
      <div className="nav-logo">reflex</div>
      <div className="footer-legal">
        © 2026 REFLEX AI, INC. / TERMS OF USE / PRIVACY POLICY / SYSTEM STATUS
      </div>
    </div>
  </footer>
)

const Landing = () => (
  <div id="smooth-content">
    <Header />
    <Hero />
    <WhatReflexDoes />
    <CoreSystem />
    <OutputSection />
    <FeatureGrid />
    <FinalCTA />
    <Footer />
  </div>
)

export default Landing
