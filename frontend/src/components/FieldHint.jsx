import { useState, useRef, useEffect } from 'react'

export default function FieldHint({ text }) {
  const [open, setOpen] = useState(false)
  const [style, setStyle] = useState({})
  const ref = useRef(null)

  useEffect(() => {
    if (!open || !ref.current) return

    const rect = ref.current.getBoundingClientRect()
    const tooltipWidth = 256
    const margin = 8
    let left = rect.left
    if (left + tooltipWidth > window.innerWidth - margin) {
      left = window.innerWidth - tooltipWidth - margin
    }
    if (left < margin) left = margin
    setStyle({ position: 'fixed', top: rect.bottom + 4, left, width: tooltipWidth })

    const handler = e => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    document.addEventListener('touchstart', handler)
    return () => {
      document.removeEventListener('mousedown', handler)
      document.removeEventListener('touchstart', handler)
    }
  }, [open])

  return (
    <span ref={ref} className="relative inline-flex items-center ml-1 align-middle">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        aria-label={text}
        aria-expanded={open}
        className="w-3.5 h-3.5 rounded-full border border-gray-400 text-gray-400 hover:border-gray-600 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-green-500 text-[9px] font-bold leading-none flex items-center justify-center transition-colors align-middle"
      >
        ?
      </button>
      {open && (
        <span
          role="tooltip"
          style={style}
          className="z-50 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs text-gray-600 shadow-md"
        >
          {text}
        </span>
      )}
    </span>
  )
}
