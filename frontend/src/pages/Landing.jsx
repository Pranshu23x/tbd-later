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
        <a href="#" className="nav-link">Architecture</a>
        <a href="#" className="nav-link">Agents</a>
        <a href="#" className="nav-link">Benchmarks</a>
        <a href="#" className="nav-link">Docs</a>
        <a href="#" className="nav-link">Company</a>
      </div>
      <div className="nav-actions">
        <button className="btn btn-ghost">Watch Demo</button>
        <Link to="/simulate" className="btn btn-primary" style={{ textDecoration: 'none' }}>Run Simulation</Link>
      </div>
    </header>
  )
}

const Hero = () => (
  <section className="hero">
    <div className="hero-container">
      <div className="hero-content">
        <h1 className="hero-title">Simulating Market Wars through Intelligence</h1>
        <ul className="hero-list">
          <li className="hero-list-item">Multi-Agent ReACT Debate</li>
          <li className="hero-list-item">Real-time Data Enrichment</li>
          <li className="hero-list-item">Graph-Based Strategy Mapping</li>
          <li className="hero-list-item">Decisive Investment Memos</li>
        </ul>
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

const FeatureGrid = () => (
  <section className="feature-grid-section">
    <div className="feature-statement">
      Reflex is changing how markets are analyzed,<br />
      how strategic progress is made and how<br />
      the next frontiers of capital are reached.
    </div>
    <div className="feature-grid">
      <div className="feature-card">
        <div className="feature-image" style={{ background: 'linear-gradient(135deg, #1a1a1a, #000)' }}></div>
        <div className="feature-info">
          <h4>Multi-Agent ReACT Debate</h4>
          <p>Reasoning + Acting loop for autonomous conflict.</p>
        </div>
      </div>
      <div className="feature-card">
        <div className="feature-image" style={{ background: 'linear-gradient(135deg, #222, #111)' }}></div>
        <div className="feature-info">
          <h4>Real-time Data Enrichment</h4>
          <p>Grounding simulations in live Crustdata metrics.</p>
        </div>
      </div>
      <div className="feature-card">
        <div className="feature-image" style={{ background: 'linear-gradient(135deg, #111, #222)' }}></div>
        <div className="feature-info">
          <h4>Graph-Based Strategy Mapping</h4>
          <p>Neo4j-powered relationship and rival analysis.</p>
        </div>
      </div>
      <div className="feature-card">
        <div className="feature-image" style={{ background: 'linear-gradient(135deg, #000, #1a1a1a)' }}></div>
        <div className="feature-info">
          <h4>Decisive Investment Memos</h4>
          <p>Board-quality reports ready for execution.</p>
        </div>
      </div>
    </div>
  </section>
)

const ResearchSection = () => (
  <section className="research-section">
    <div className="research-container">
      <div className="research-left">
        <div className="label-micro" style={{ marginBottom: '1.5rem', color: '#ffffff' }}>Reflex Architecture</div>
        <h2 className="research-mission">
          We are building the foundational intelligence layer for market simulations. Using a specialized multi-agent ReACT loop, Reflex autonomously researches, debates, and extracts board-quality strategic insights from raw market data.
        </h2>
        <button className="btn-outline">View Architecture</button>
      </div>
      <div className="research-right">
        <div className="research-item">
          <div className="research-item-header">
            <h3>Reasoning-Action Loop</h3>
            <span className="arrow-up">↗</span>
          </div>
          <p>Each agent executes an internal ReACT loop, querying live Crustdata APIs to ground every strategic move in quantitative reality.</p>
        </div>
        <div className="research-item">
          <div className="research-item-header">
            <h3>GraphRAG Engine</h3>
            <span className="arrow-up">↗</span>
          </div>
          <p>A Neo4j-backed knowledge graph maps the complex relationships between companies, rivals, and executives for deep context retrieval.</p>
        </div>
        <div className="research-item">
          <div className="research-item-header">
            <h3>DeepSeek-V3 Reasoning</h3>
            <span className="arrow-up">↗</span>
          </div>
          <p>Leveraging high-parameter reasoning models to orchestrate fierce debates between agents, ensuring every consensus is stress-tested.</p>
        </div>
      </div>
    </div>
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
    <FeatureGrid />
    <ResearchSection />
    <Footer />
  </div>
)

export default Landing
