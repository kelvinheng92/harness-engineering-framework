import { useRef, useState, useCallback, useEffect } from 'react'

interface ResizableSplitProps {
  left: React.ReactNode
  right: React.ReactNode
  initialLeftWidth?: number   // pixels
  minLeft?: number
  minRight?: number
}

export function ResizableSplit({
  left,
  right,
  initialLeftWidth = 600,
  minLeft = 320,
  minRight = 320,
}: ResizableSplitProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [leftWidth, setLeftWidth] = useState(initialLeftWidth)
  const dragging = useRef(false)
  const startX = useRef(0)
  const startWidth = useRef(0)

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    dragging.current = true
    startX.current = e.clientX
    startWidth.current = leftWidth
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    e.preventDefault()
  }, [leftWidth])

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return
      const delta = e.clientX - startX.current
      const containerW = containerRef.current.offsetWidth
      const next = Math.min(
        containerW - minRight,
        Math.max(minLeft, startWidth.current + delta),
      )
      setLeftWidth(next)
    }

    const onMouseUp = () => {
      if (!dragging.current) return
      dragging.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [minLeft, minRight])

  return (
    <div ref={containerRef} className="flex flex-1 overflow-hidden">
      {/* Left pane */}
      <div
        style={{ width: leftWidth, minWidth: minLeft }}
        className="flex-shrink-0 overflow-y-auto bg-[#f5f5f5]"
      >
        {left}
      </div>

      {/* Drag handle */}
      <div
        onMouseDown={onMouseDown}
        className="w-1 flex-shrink-0 bg-[#e0e0e0] hover:bg-[#C8102E] active:bg-[#C8102E] cursor-col-resize transition-colors group relative"
        title="Drag to resize"
      >
        {/* Visual grip dots */}
        <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 flex flex-col items-center justify-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
          {[0, 1, 2].map((i) => (
            <div key={i} className="w-1 h-1 rounded-full bg-white" />
          ))}
        </div>
      </div>

      {/* Right pane */}
      <div className="flex-1 overflow-hidden">
        {right}
      </div>
    </div>
  )
}
