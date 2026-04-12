import { useState, useCallback } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Download, Loader2 } from 'lucide-react'
// @ts-ignore
import 'react-pdf/dist/Page/AnnotationLayer.css'
// @ts-ignore
import 'react-pdf/dist/Page/TextLayer.css'

// Worker copied to public/ to avoid Vite package exports resolution issues
pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs'

interface PDFViewerProps {
  url: string
  filename: string
}

export function PDFViewer({ url, filename }: PDFViewerProps) {
  const [numPages, setNumPages] = useState<number>(0)
  const [pageNumber, setPageNumber] = useState<number>(1)
  const [scale, setScale] = useState<number>(1.0)
  const [loading, setLoading] = useState(true)

  const onLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages)
    setLoading(false)
  }, [])

  const prevPage = () => setPageNumber((p) => Math.max(1, p - 1))
  const nextPage = () => setPageNumber((p) => Math.min(numPages, p + 1))
  const zoomIn = () => setScale((s) => Math.min(2.5, s + 0.2))
  const zoomOut = () => setScale((s) => Math.max(0.4, s - 0.2))

  return (
    <div className="flex flex-col h-full bg-[#f0f0f0]">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-white border-b border-[#e0e0e0] flex-shrink-0">
        <div className="flex items-center gap-1">
          <span className="text-xs text-[#555555] font-medium truncate max-w-[200px]">{filename}</span>
        </div>

        <div className="flex items-center gap-1">
          {/* Page nav */}
          <button
            onClick={prevPage}
            disabled={pageNumber <= 1}
            className="w-7 h-7 flex items-center justify-center rounded border border-[#e0e0e0] hover:border-[#C8102E] hover:text-[#C8102E] disabled:opacity-40 text-[#555555] transition-colors"
          >
            <ChevronLeft size={15} />
          </button>
          <span className="text-xs text-[#555555] min-w-[52px] text-center">
            {pageNumber} / {numPages || '—'}
          </span>
          <button
            onClick={nextPage}
            disabled={pageNumber >= numPages}
            className="w-7 h-7 flex items-center justify-center rounded border border-[#e0e0e0] hover:border-[#C8102E] hover:text-[#C8102E] disabled:opacity-40 text-[#555555] transition-colors"
          >
            <ChevronRight size={15} />
          </button>

          <div className="w-px h-4 bg-[#e0e0e0] mx-1" />

          {/* Zoom */}
          <button
            onClick={zoomOut}
            className="w-7 h-7 flex items-center justify-center rounded border border-[#e0e0e0] hover:border-[#C8102E] hover:text-[#C8102E] text-[#555555] transition-colors"
          >
            <ZoomOut size={14} />
          </button>
          <span className="text-xs text-[#666666] w-10 text-center">{Math.round(scale * 100)}%</span>
          <button
            onClick={zoomIn}
            className="w-7 h-7 flex items-center justify-center rounded border border-[#e0e0e0] hover:border-[#C8102E] hover:text-[#C8102E] text-[#555555] transition-colors"
          >
            <ZoomIn size={14} />
          </button>

          <div className="w-px h-4 bg-[#e0e0e0] mx-1" />

          <a
            href={url}
            download={filename}
            className="w-7 h-7 flex items-center justify-center rounded border border-[#e0e0e0] hover:border-[#C8102E] hover:text-[#C8102E] text-[#555555] transition-colors"
          >
            <Download size={14} />
          </a>
        </div>
      </div>

      {/* PDF Content */}
      <div className="flex-1 overflow-auto flex items-start justify-center p-6">
        {loading && (
          <div className="flex items-center gap-2 text-[#888888] mt-20">
            <Loader2 size={20} className="animate-spin text-[#C8102E]" />
            <span className="text-sm">Loading document...</span>
          </div>
        )}
        <Document
          file={url}
          onLoadSuccess={onLoadSuccess}
          onLoadError={() => setLoading(false)}
          loading=""
        >
          <Page
            pageNumber={pageNumber}
            scale={scale}
            renderAnnotationLayer
            renderTextLayer
          />
        </Document>
      </div>
    </div>
  )
}
