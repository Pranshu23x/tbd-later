import { useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import Lenis from 'lenis'
import Landing from './pages/Landing'
import Simulation from './pages/Simulation'
import RunSimulation from './pages/RunSimulation'
import './index.css'

gsap.registerPlugin(ScrollTrigger)

function App() {
  useEffect(() => {
    // Initialize Lenis for smooth scrolling
    const lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true
    })

    function raf(time) {
      lenis.raf(time)
      requestAnimationFrame(raf)
    }

    requestAnimationFrame(raf)

    // Connect Lenis to ScrollTrigger
    lenis.on('scroll', ScrollTrigger.update)

    gsap.ticker.add((time) => {
      lenis.raf(time * 1000)
    })

    gsap.ticker.lagSmoothing(0)

    return () => {
      lenis.destroy()
    }
  }, [])

  return (
    <Router>
      <div id="smooth-wrapper">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/simulate" element={<Simulation />} />
          <Route path="/run" element={<RunSimulation />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
