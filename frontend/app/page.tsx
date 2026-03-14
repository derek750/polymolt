"use client"

import { useEffect, useRef, useState } from "react"
import Link from "next/link"

export default function HeroPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [logoError, setLogoError] = useState(false)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    let animationId: number
    let phase = 0
    const dpr = Math.min(2, typeof window !== "undefined" ? window.devicePixelRatio : 1)

    const resize = () => {
      const w = window.innerWidth
      const h = window.innerHeight
      canvas.width = w * dpr
      canvas.height = h * dpr
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    const draw = () => {
      const w = canvas.width / dpr
      const h = canvas.height / dpr
      ctx.clearRect(0, 0, w, h)

      const lineCount = 5
      const baseY = h * 0.6
      const amp = h * 0.15
      const step = 80

      for (let L = 0; L < lineCount; L++) {
        ctx.beginPath()
        const offset = (L / lineCount) * Math.PI * 0.4 + phase * 0.3
        for (let x = 0; x <= w + step; x += step) {
          const t = x / w + offset + phase * 0.02
          const y =
            baseY -
            amp * Math.sin(t * 2) -
            amp * 0.5 * Math.sin(t * 5 + 1) +
            (L - lineCount / 2) * 25
          if (x === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        }
        const alpha = 0.08 + (L / lineCount) * 0.12
        ctx.strokeStyle = `rgba(23, 23, 23, ${alpha})`
        ctx.lineWidth = 1.5
        ctx.stroke()
      }

      phase += 0.008
      animationId = requestAnimationFrame(draw)
    }

    resize()
    window.addEventListener("resize", resize)
    draw()
    return () => {
      window.removeEventListener("resize", resize)
      cancelAnimationFrame(animationId)
    }
  }, [])

  return (
    <div className="relative min-h-screen bg-white overflow-hidden flex flex-col items-center justify-center">
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
        aria-hidden
      />

      <div className="relative z-10 flex flex-col items-center gap-8 px-6">
        <div className="flex items-center justify-center gap-6">
          <div className="relative w-24 h-24 sm:w-28 sm:h-28 flex-shrink-0">
            {!logoError ? (
              <img
                src="/logo.png"
                alt="Polymolt"
                className="object-contain w-full h-full"
                onError={() => setLogoError(true)}
              />
            ) : (
              <svg
                viewBox="0 0 100 120"
                className="w-full h-full text-neutral-900"
                aria-hidden
              >
                <path
                  fill="currentColor"
                  d="M50 8 L58 18 L55 28 L60 35 L58 45 L62 55 L58 65 L50 75 L42 65 L38 55 L42 45 L40 35 L45 28 L42 18 Z M30 40 L20 50 L25 60 L30 55 Z M70 40 L80 50 L75 60 L70 55 Z M50 75 L45 85 L50 95 L55 85 Z M50 95 L40 105 L50 115 L60 105 Z"
                />
              </svg>
            )}
          </div>
          <h1 className="font-bold text-neutral-900 text-4xl sm:text-5xl md:text-6xl tracking-tight">
            polymolt
          </h1>
        </div>

        <p className="text-neutral-500 text-center text-sm sm:text-base max-w-md">
          Sustainability prediction market — explore by location
        </p>

        <Link
          href="/map"
          className="mt-4 px-6 py-3 rounded-lg bg-neutral-900 text-white font-medium text-sm hover:bg-neutral-800 transition-colors"
        >
          Explore map
        </Link>
      </div>
    </div>
  )
}
