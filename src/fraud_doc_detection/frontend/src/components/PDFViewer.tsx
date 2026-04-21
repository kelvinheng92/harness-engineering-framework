import { useState, useCallback, useRef, useEffect } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Download, Loader2 } from 'lucide-react'
// @ts-ignore
import 'react-pdf/dist/Page/AnnotationLayer.css'
// @ts-ignore
import 'react-pdf/dist/Page/TextLayer.css'
import type { HighlightBox } from '../types'
import { getColor } from '../utils/highlightColors'

pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs'

export interface HighlightWithMeta extends HighlightBox {
  indicatorId: string
  colorIndex: number
}

interface PDFViewerProps {
  url: string
  filename: string
  highlights?: HighlightWithMeta[]
  activeIndicatorId?: string | null
  jumpToPage?: number | null
}

export function PDFViewer({
  url,
  filename,
  highlights = [],
  activeIndicatorId = null,
  jumpToPage = null,
}: PDFViewerProps) {
  const [numPages, setNumPages] = useState<number>(0)
  const [pageNumber, setPageNumber] = useState<number>(1)
  const [scale, setScale] = useState<number>(1.0)
  const [loading, setLoading] = useState(true)
  const [renderedSize, setRenderedSize] = useState<{ w: number; h: number } | null>(null)
  const pageWrapperRef = useRef<HTMLDivElement>(null)

  const onDocLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages)
    setLoading(false)
  }, [])

  // Jump to page when active indicator changes
  useEffect(() => {
    if (jumpToPage !== null && jumpToPage >= 1) setPageNumber(jumpToPage)
  }, [jumpToPage])

  // Invalidate measured size on page/scale change
  useEffect(() => { setRenderedSize(null) }, [pageNumber, scale])

  const onPageRenderSuccess = useCallback(() => {
    if (!pageWrapperRef.current) return
    const canvas = pageWrapperRef.current.querySelector('canvas') as HTMLElement | null
    const target = canvas ?? pageWrapperRef.current
    setRenderedSize({ w: target.offsetWidth, h: target.offsetHeight })
  }, [])

  const prevPage = () => setPageNumber((p) => Math.max(1, p - 1))
  const nextPage = () => setPageNumber((p) => Math.min(numPages, p + 1))
  const zoomIn  = () => setScale((s) => Math.min(2.5, parseFloat((s + 0.2).toFixed(1))))
  const zoomOut = () => setScale((s) => Math.max(0.4, parseFloat((s - 0.2).toFixed(1))))

  const pageHighlights = highlights.filter((h) => h.page === pageNumber)
  const hasAnyHighlights = highlights.length > 0
  const hasActiveSelection = activeIndicatorId !== null

  return (
    <div className="flex flex-col h-full bg-[#f0f0f0]">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-white border-b border-[#e0e0e0] flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs text-[#555555] font-medium truncate max-w-[180px]">{filename}</span>
          {hasAnyHighlights && (
            <span className="flex-shrink-0 text-[10px] px-1.5 py-0.5 rounded bg-red-50 text-[#C8102E] border border-red-200 font-medium whitespace-nowrap">
              {highlights.length} region{highlights.length !== 1 ? 's' : ''} flagged
            </span>
          )}
        </div>

        <div className="flex items-center gap-1">
          <button onClick={prevPage} disabled={pageNumber <= 1}
            className="w-7 h-7 flex items-center justify-center rounded border border-[#e0e0e0] hover:border-[#C8102E] hover:text-[#C8102E] disabled:opacity-40 text-[#555555] transition-colors">
            <ChevronLeft size={15} />
          </button>
          <span className="text-xs text-[#555555] min-w-[52px] text-center">
            {pageNumber} / {numPages || '—'}
          </span>
          <button onClick={nextPage} disabled={pageNumber >= numPages}
            className="w-7 h-7 flex items-center justify-center rounded border border-[#e0e0e0] hover:border-[#C8102E] hover:text-[#C8102E] disabled:opacity-40 text-[#555555] transition-colors">
            <ChevronRight size={15} />
          </button>

          <div className="w-px h-4 bg-[#e0e0e0] mx-1" />

          <button onClick={zoomOut}
            className="w-7 h-7 flex items-center justify-center rounded border border-[#e0e0e0] hover:border-[#C8102E] hover:text-[#C8102E] text-[#555555] transition-colors">
            <ZoomOut size={14} />
          </button>
          <span className="text-xs text-[#666666] w-10 text-center">{Math.round(scale * 100)}%</span>
          <button onClick={zoomIn}
            className="w-7 h-7 flex items-center justify-center rounded border border-[#e0e0e0] hover:border-[#C8102E] hover:text-[#C8102E] text-[#555555] transition-colors">
            <ZoomIn size={14} />
          </button>

          <div className="w-px h-4 bg-[#e0e0e0] mx-1" />

          <a href={url} download={filename}
            className="w-7 h-7 flex items-center justify-center rounded border border-[#e0e0e0] hover:border-[#C8102E] hover:text-[#C8102E] text-[#555555] transition-colors">
            <Download size={14} />
          </a>
        </div>
      </div>

      {/* PDF content */}
      <div className="flex-1 overflow-auto flex items-start justify-center p-6">
        {loading && (
          <div className="flex items-center gap-2 text-[#888888] mt-20">
            <Loader2 size={20} className="animate-spin text-[#C8102E]" />
            <span className="text-sm">Loading document...</span>
          </div>
        )}
        <Document
          file={url}
          onLoadSuccess={onDocLoadSuccess}
          onLoadError={() => setLoading(false)}
          loading=""
        >
          <div ref={pageWrapperRef} style={{ position: 'relative', display: 'inline-block' }}>
            <Page
              pageNumber={pageNumber}
              scale={scale}
              renderAnnotationLayer
              renderTextLayer
              onRenderSuccess={onPageRenderSuccess}
            />

            {/* All highlights rendered simultaneously */}
            {renderedSize && pageHighlights.map((h, i) => {
              const color = getColor(h.colorIndex)
              const isActive = h.indicatorId === activeIndicatorId
              // When something is selected, dim unrelated highlights
              const dimmed = hasActiveSelection && !isActive

              const sx = renderedSize.w / h.page_width
              const sy = renderedSize.h / h.page_height

              return (
                <div
                  key={i}
                  title={h.label}
                  style={{
                    position: 'absolute',
                    left:   h.x0 * sx,
                    top:    h.y0 * sy,
                    width:  Math.max((h.x1 - h.x0) * sx, 8),
                    height: Math.max((h.y1 - h.y0) * sy, 8),
                    backgroundColor: dimmed ? 'rgba(0,0,0,0.04)' : color.bg,
                    border: `${isActive ? 2.5 : 1.5}px solid ${dimmed ? 'rgba(150,150,150,0.3)' : color.border}`,
                    borderRadius: 3,
                    opacity: dimmed ? 0.4 : 1,
                    transition: 'opacity 0.2s, border-width 0.15s',
                    pointerEvents: 'none',
                    zIndex: isActive ? 20 : 10,
                    boxSizing: 'border-box',
                    // Active highlight gets a subtle outer glow
                    boxShadow: isActive ? `0 0 0 2px ${color.border}33` : 'none',
                  }}
                />
              )
            })}
          </div>
        </Document>
      </div>
    </div>
  )
}
