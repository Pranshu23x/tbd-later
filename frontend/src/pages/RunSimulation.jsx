import { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import * as d3 from 'd3'
import ReactMarkdown from 'react-markdown'

const API_BASE_URL = 'https://reflex-36xb.onrender.com'

/* ── Color palette for entity types (from MiroFish GraphPanel) ── */
const ENTITY_COLORS = {
  Company:  '#5c67f2',
  Investor: '#f59e0b',
  'C-Level': '#ef4444',
  VP:       '#8b5cf6',
  Senior:   '#06b6d4',
  Mid:      '#10b981',
  default:  '#999',
}

const getColor = (type) => ENTITY_COLORS[type] || ENTITY_COLORS.default

/* ══════════════════════════════════════════════════════════════════
   D3 Force Graph — ported from MiroFish GraphPanel.vue
   ══════════════════════════════════════════════════════════════════ */
const GraphCanvas = ({ graphData }) => {
  const svgRef = useRef(null)
  const containerRef = useRef(null)
  const simRef = useRef(null)

  const renderGraph = useCallback(() => {
    if (!svgRef.current || !containerRef.current || !graphData) return

    // Stop previous simulation
    if (simRef.current) simRef.current.stop()

    const width  = containerRef.current.clientWidth
    const height = containerRef.current.clientHeight

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)

    svg.selectAll('*').remove()

    const nodesData = graphData.nodes || []
    const edgesData = graphData.edges || []
    if (nodesData.length === 0) return

    // Build lookup
    const nodeMap = {}
    nodesData.forEach(n => { nodeMap[n.id] = n })

    const nodes = nodesData.map(n => ({
      id: n.id,
      name: n.name || 'Unknown',
      type: n.type || 'Company',
    }))

    const nodeIds = new Set(nodes.map(n => n.id))

    // Build edges — handle multi-edges between same pair
    const pairCount = {}
    const validEdges = edgesData.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))

    validEdges.forEach(e => {
      const key = [e.source, e.target].sort().join('|')
      pairCount[key] = (pairCount[key] || 0) + 1
    })

    const pairIndex = {}
    const edges = validEdges.map(e => {
      const key = [e.source, e.target].sort().join('|')
      const idx = pairIndex[key] || 0
      pairIndex[key] = idx + 1
      const total = pairCount[key]

      let curvature = 0
      if (total > 1) {
        curvature = ((idx / (total - 1)) - 0.5) * 1.2
      }

      return { source: e.source, target: e.target, label: e.label || '', curvature, pairTotal: total }
    })

    // Simulation
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(edges).id(d => d.id).distance(160))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide(50))
      .force('x', d3.forceX(width / 2).strength(0.04))
      .force('y', d3.forceY(height / 2).strength(0.04))

    simRef.current = simulation

    const g = svg.append('g')

    // Zoom
    svg.call(
      d3.zoom()
        .scaleExtent([0.15, 4])
        .on('zoom', (event) => g.attr('transform', event.transform))
    )

    // --- Helper: curved path ---
    const linkPath = (d) => {
      const sx = d.source.x, sy = d.source.y
      const tx = d.target.x, ty = d.target.y
      if (d.curvature === 0) return `M${sx},${sy} L${tx},${ty}`
      const dx = tx - sx, dy = ty - sy
      const dist = Math.sqrt(dx * dx + dy * dy) || 1
      const off = Math.max(35, dist * 0.25) * d.curvature
      const cx = (sx + tx) / 2 + (-dy / dist) * off
      const cy = (sy + ty) / 2 + (dx / dist) * off
      return `M${sx},${sy} Q${cx},${cy} ${tx},${ty}`
    }

    const linkMid = (d) => {
      const sx = d.source.x, sy = d.source.y
      const tx = d.target.x, ty = d.target.y
      if (d.curvature === 0) return { x: (sx + tx) / 2, y: (sy + ty) / 2 }
      const dx = tx - sx, dy = ty - sy
      const dist = Math.sqrt(dx * dx + dy * dy) || 1
      const off = Math.max(35, dist * 0.25) * d.curvature
      const cx2 = (sx + tx) / 2 + (-dy / dist) * off
      const cy2 = (sy + ty) / 2 + (dx / dist) * off
      return { x: 0.25 * sx + 0.5 * cx2 + 0.25 * tx, y: 0.25 * sy + 0.5 * cy2 + 0.25 * ty }
    }

    // Links
    const linkG = g.append('g')
    const link = linkG.selectAll('path')
      .data(edges).enter().append('path')
      .attr('stroke', d => d.label === 'INVESTED_IN' ? '#d97706' : '#3f3f46')
      .attr('stroke-width', 1.5).attr('fill', 'none')
      .attr('stroke-dasharray', d => d.label === 'INVESTED_IN' ? '4,4' : 'none')

    // Link labels
    const linkLabel = linkG.selectAll('text')
      .data(edges).enter().append('text')
      .text(d => d.label === 'INVESTED_IN' ? '' : d.label) // Hide INVESTED_IN labels for cleaner look like image
      .attr('font-size', '8px').attr('fill', '#52525b')
      .attr('text-anchor', 'middle').attr('dominant-baseline', 'middle')
      .style('pointer-events', 'none')

    // Nodes
    const nodeG = g.append('g')

    const node = nodeG.selectAll('circle')
      .data(nodes).enter().append('circle')
      .attr('r', d => d.type === 'Company' ? 22 : 10)
      .attr('fill', d => getColor(d.type))
      .attr('stroke', '#18181b').attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .call(d3.drag()
        .on('start', (e, d) => { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
        .on('drag',  (e, d) => { d.fx = e.x; d.fy = e.y })
        .on('end',   (e, d) => { if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null })
      )

    const nodeLabel = nodeG.selectAll('text')
      .data(nodes).enter().append('text')
      .text(d => d.name.length > 18 ? d.name.slice(0, 18) + '…' : d.name)
      .attr('font-size', d => d.type === 'Company' ? '13px' : '10px')
      .attr('fill', d => d.type === 'Company' ? '#fff' : '#a1a1aa')
      .attr('font-weight', d => d.type === 'Company' ? 700 : 500)
      .attr('dx', d => d.type === 'Company' ? 28 : 16)
      .attr('dy', 4).style('pointer-events', 'none')

    // Tick
    simulation.on('tick', () => {
      link.attr('d', linkPath)
      linkLabel.each(function (d) {
        const m = linkMid(d)
        d3.select(this).attr('x', m.x).attr('y', m.y)
      })
      node.attr('cx', d => d.x).attr('cy', d => d.y)
      nodeLabel.attr('x', d => d.x).attr('y', d => d.y)
    })
  }, [graphData])

  useEffect(() => { renderGraph() }, [renderGraph])

  // Resize handler
  useEffect(() => {
    const onResize = () => renderGraph()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [renderGraph])

  return (
    <div className="graph-wrap" ref={containerRef}>
      <svg ref={svgRef} />
      {/* Legend */}
      <div className="graph-legend-box">
        <span className="legend-title">ENTITY TYPES</span>
        {Object.entries(ENTITY_COLORS).filter(([k]) => k !== 'default').map(([k, c]) => (
          <div key={k} className="legend-row">
            <span className="legend-dot" style={{ background: c }} />
            <span>{k}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ══════════════════════════════════════════════════════════════════
   Timeline Feed — ported from MiroFish Step3Simulation.vue
   ══════════════════════════════════════════════════════════════════ */
const TimelineFeed = ({ messages, status }) => {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const getBadgeClass = (role) => {
    if (!role) return 'badge-default'
    const r = role.toLowerCase()
    if (r.includes('ceo') || r.includes('chair')) return 'badge-verdict'
    if (r.includes('strategist') || r.includes('plan')) return 'badge-plan'
    if (r.includes('system')) return 'badge-system'
    return 'badge-agent'
  }

  return (
    <div className="timeline-feed">
      <div className="timeline-axis" />

      {messages.length === 0 && (
        <div className="waiting-state">
          <div className="pulse-ring" />
          <span>Waiting for agent actions…</span>
        </div>
      )}

      {messages.map((msg, idx) => (
        <div key={idx} className={`timeline-item ${msg.type}`}>
          <div className="timeline-marker"><div className="marker-dot" /></div>
          <div className="timeline-card">
            <div className="card-header">
              <div className="agent-info">
                <div className="avatar-placeholder">{(msg.role || 'A')[0]}</div>
                <span className="agent-name-label">{msg.role}</span>
              </div>
              <div className="header-meta">
                <div className={`action-badge ${getBadgeClass(msg.role)}`}>
                  {msg.type === 'verdict' ? 'VERDICT' : msg.type === 'plan' ? 'MEMO' : msg.type === 'system' ? 'SYSTEM' : 'DEBATE'}
                </div>
              </div>
            </div>
            <div className="card-body">
              <div className="content-text"><ReactMarkdown>{msg.content}</ReactMarkdown></div>
            </div>
            <div className="card-footer">
              <span className="time-tag">
                {msg.round ? `R${msg.round}` : '—'} • {new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}

/* ══════════════════════════════════════════════════════════════════
   Main Page
   ══════════════════════════════════════════════════════════════════ */
const RunSimulation = () => {
  const [searchParams] = useSearchParams()
  const query = searchParams.get('query')
  const [messages, setMessages]   = useState([])
  const [status, setStatus]       = useState('initializing')
  const [graphData, setGraphData] = useState(null)
  const [elapsed, setElapsed]     = useState(0)

  // Ref to track the current streaming bubble
  const streamBuf = useRef({ active: false, role: '', round: 0, type: 'agent', content: '' })

  // Timer
  useEffect(() => {
    if (status === 'analyzing') {
      const id = setInterval(() => setElapsed(p => p + 1), 1000)
      return () => clearInterval(id)
    }
  }, [status])

  // SSE stream
  useEffect(() => {
    if (!query) return

    const run = async () => {
      try {
        setStatus('analyzing')
        // Display the user prompt immediately at the top of the timeline
        setMessages([{ role: 'System', content: `**User Prompt:** ${query}`, type: 'system' }])
        
        const res = await fetch(`${API_BASE_URL}/api/simulate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_type: 'Strategic Analyst',
            target_company: query,
            compare_against: 'Competitor',
            benchmarks: ['Revenue', 'Market Share', 'Tech Stack'],
            planning: ['100-Day Plan'],
            planning_custom: '',
            num_rounds: parseInt(searchParams.get('rounds')) || 3,
          }),
        })

        const reader  = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { value, done } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          
          let eolIndex;
          while ((eolIndex = buffer.indexOf('\n\n')) >= 0) {
            const eventStr = buffer.slice(0, eolIndex).trim()
            buffer = buffer.slice(eolIndex + 2)
            
            if (eventStr.startsWith('data: ')) {
              try {
                const evt = JSON.parse(eventStr.slice(6))
                handleEvent(evt)
              } catch (e) {
                console.error("Failed to parse SSE JSON:", e)
              }
            }
          }
        }
      } catch (err) {
        console.error('Simulation stream error', err)
        setStatus('error')
      }
    }

    run()
  }, [query])

  const handleEvent = (evt) => {
    switch (evt.status) {
      /* ── Backend streaming protocol ── */
      case 'connected': {
        setMessages(p => [...p, { role: 'System', content: `**Reflex:** ${evt.message || 'Intelligence initialized...'}`, type: 'system' }])
        break
      }
      case 'system': {
        if (evt.message || evt.detail) {
          setMessages(p => [...p, { role: 'System', content: evt.message || `*${evt.detail}*`, type: 'system' }])
        }
        break
      }
      case 'stream_start': {
        // Determine bubble type from speaker/label
        const speaker = evt.speaker || evt.label || 'Agent'
        const lbl = (evt.label || speaker).toLowerCase()
        let type = 'agent'
        if (lbl.includes('verdict') || lbl.includes('chair') || lbl.includes('ceo')) type = 'verdict'
        else if (lbl.includes('strategist') || lbl.includes('plan') || lbl.includes('memo')) type = 'plan'

        streamBuf.current = { active: true, role: speaker, round: evt.round || 0, type, content: '' }
        // Create a new empty bubble immediately
        setMessages(p => [...p, { role: speaker, content: '', round: evt.round || 0, type }])
        break
      }
      case 'stream_token': {
        if (!streamBuf.current.active) break
        streamBuf.current.content += (evt.token || '')
        const txt = streamBuf.current.content
        // Update the last bubble in-place
        setMessages(p => {
          const next = [...p]
          if (next.length > 0) next[next.length - 1] = { ...next[next.length - 1], content: txt }
          return next
        })
        break
      }
      case 'stream_end':
        streamBuf.current.active = false
        break

      /* ── Legacy / fallback events ── */
      case 'data_ready':
        setStatus('analyzing')
        if (evt.data) {
          buildGraphFromData(evt.data)
          
          let matchStr = `**Found ${evt.data.pipeline?.length || 0} matching companies:**\n`
          if (evt.data.pipeline) {
             evt.data.pipeline.forEach((co, i) => {
               const hc = co.muscle?.headcount || 'N/A'
               const fund = co.capital?.funding_total ? `$${co.capital.funding_total.toLocaleString()}` : 'N/A'
               matchStr += `${i+1}. **${co.name}** | HC: ${hc} | Funding: ${fund}\n`
             })
          }
          setMessages(p => [...p, { role: 'System', content: matchStr, type: 'system' }])
        }
        break
      case 'debate_turn':
        setMessages(p => [...p, { role: evt.speaker, content: evt.content, round: evt.round, type: 'agent' }])
        break
      case 'verdict':
        setMessages(p => [...p, { role: 'Committee Chair', content: evt.content, type: 'verdict' }])
        break
      case 'plan':
        setMessages(p => [...p, { role: 'Strategist', content: evt.content, type: 'plan' }])
        break
      case 'complete':
        setStatus('complete')
        break
      case 'error':
        setStatus('error')
        setMessages(p => [...p, { role: 'System', content: evt.message, type: 'error' }])
        break
      default:
        // Handle orchestrator phases that might not have a 'status' field
        if (evt.phase === 'search' || evt.phase === 'enrich') {
          setMessages(p => [...p, { role: 'System', content: `*${evt.detail}*`, type: 'system' }])
        } else if (evt.phase === 'data_ready' && !evt.status) {
          // Fallback if status was somehow stripped
          if (evt.data) buildGraphFromData(evt.data)
        }
        break
    }
  }

  /* Build a D3-compatible graph from the dual_fetch data structure:
     { target: { company: {...}, employees: [] }, rival: { company: {...}, employees: [] } }
     Company shape: { name, people: { founders, cxos, decision_makers }, backing: { investor_list }, ... }
  */
  const buildGraphFromData = (data) => {
    const nodes = []
    const edges = []
    const investorIndex = {}  // deduplicate shared investors

    const addCompany = (wrapper, key) => {
      const co = wrapper?.company || wrapper
      if (!co || !co.name) return

      // Company node
      nodes.push({ id: key, name: co.name, type: 'Company' })

      // ── People (CXOs + Founders) ──
      const cxos     = co.people?.cxos || []
      const founders = co.people?.founders || []
      const allPeople = [...founders, ...cxos]
      const seenNames = new Set()

      allPeople.forEach((person, i) => {
        const name = person.name || person.full_name || `Exec ${i}`
        if (seenNames.has(name)) return
        seenNames.add(name)

        const eid = `${key}_p_${i}`
        const title = (person.title || person.current_title || '').toLowerCase()
        let type = 'Mid'
        if (title.includes('ceo') || title.includes('cto') || title.includes('cfo') || title.includes('coo') || title.includes('chief') || title.includes('founder')) type = 'C-Level'
        else if (title.includes('vp') || title.includes('vice president')) type = 'VP'
        else if (title.includes('senior') || title.includes('director') || title.includes('head')) type = 'Senior'

        nodes.push({ id: eid, name, type })
        edges.push({ source: key, target: eid, label: person.title || person.current_title || 'WORKS_AT' })
      })

      // ── Investors ──
      const investors = co.backing?.investor_list || []
      investors.forEach((inv) => {
        const invName = typeof inv === 'string' ? inv : (inv.name || inv.investor_name || '')
        if (!invName) return

        // Shared investors get one node with edges to both companies
        const iid = `inv_${invName.replace(/\s+/g, '_').toLowerCase()}`
        if (!investorIndex[iid]) {
          investorIndex[iid] = true
          nodes.push({ id: iid, name: invName, type: 'Investor' })
        }
        edges.push({ source: iid, target: key, label: 'INVESTED_IN' })
      })
    }

    // If we have a pipeline from the orchestrator, map all companies
    if (data.pipeline && data.pipeline.length > 0) {
      data.pipeline.forEach((co, idx) => {
        addCompany({ company: co }, `co_${idx}`)
      })
      // Link the first company (Target) to the rest as competitors
      for (let i = 1; i < data.pipeline.length; i++) {
        if (nodes.find(n => n.id === 'co_0') && nodes.find(n => n.id === `co_${i}`)) {
          edges.push({ source: 'co_0', target: `co_${i}`, label: 'COMPETES_WITH' })
        }
      }
    } else {
      // Fallback: Process target + rival from dual_fetch response
      addCompany(data.target, 'target')
      addCompany(data.rival,  'rival')

      // Competitor edge
      if (nodes.find(n => n.id === 'target') && nodes.find(n => n.id === 'rival')) {
        edges.push({ source: 'target', target: 'rival', label: 'COMPETES_WITH' })
      }
    }

    setGraphData({ nodes, edges })
  }

  const fmtTime = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

  return (
    <div className="studio-page">
      {/* ── Top nav ── */}
      <nav className="studio-topbar">
        <div className="topbar-left">
          <Link to="/simulate" className="back-arrow">‹</Link>
          <span className="topbar-logo">reflex</span>
          <span className="topbar-title">Reflex Studio</span>
        </div>
        <div className="topbar-right">
          <div className="topbar-stat">
            <span className={`status-led ${status}`} />
            <span>{status === 'complete' ? 'Complete' : status === 'error' ? 'Error' : 'Simulating'}</span>
          </div>
          <div className="topbar-stat mono">{fmtTime(elapsed)}</div>
          <div className="topbar-stat mono">ACTS {messages.length}</div>
          <button className="btn-export">Export Report</button>
          <button className="btn-rerun">▶ Re-run</button>
        </div>
      </nav>

      {/* ── Main split ── */}
      <div className="studio-split">
        {/* LEFT — Timeline / Debate */}
        <aside className="studio-left">
          <div className="panel-bar">
            <div className="panel-bar-left">
              <span className="panel-icon">💬</span>
              <span className="panel-label">WAR ROOM</span>
              <span className="panel-count">{messages.length}</span>
            </div>
            <div className="panel-bar-right">
              <span className="depth-label">ROUNDS</span>
              <span className="depth-value">3</span>
            </div>
          </div>
          <div className="timeline-scroll">
            <TimelineFeed messages={messages} status={status} />
          </div>
          <div className="studio-input-row">
            <input type="text" placeholder="Ask the swarm…" disabled />
            <button className="send-arrow" disabled>↗</button>
          </div>
        </aside>

        {/* RIGHT — Graph */}
        <main className="studio-right">
          <div className="graph-bar">
            <div className="graph-bar-stats">
              <span>🏢 {graphData?.nodes?.filter(n => n.type === 'Company').length || 0} Companies</span>
              <span>👤 {graphData?.nodes?.filter(n => ['C-Level','VP','Senior','Mid'].includes(n.type)).length || 0} People</span>
              <span>💰 {graphData?.nodes?.filter(n => n.type === 'Investor').length || 0} Investors</span>
            </div>
          </div>
          <GraphCanvas graphData={graphData} />
        </main>
      </div>

      {/* ── Bottom system log ── */}
      <div className="syslog-bar">
        <span className="syslog-title">SIMULATION MONITOR</span>
        <span className="syslog-msg">
          {status === 'analyzing' ? `Streaming debate for "${query}" …` : status === 'complete' ? 'Simulation finished.' : 'Initializing engine…'}
        </span>
      </div>
    </div>
  )
}

export default RunSimulation
