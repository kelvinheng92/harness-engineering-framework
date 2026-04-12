import { useCallback, useState } from 'react'
import { Upload, FileText, Loader2 } from 'lucide-react'

interface UploadZoneProps {
  onUpload: (file: File) => Promise<void>
  uploading: boolean
}

export function UploadZone({ onUpload, uploading }: UploadZoneProps) {
  const [dragging, setDragging] = useState(false)

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      const file = e.dataTransfer.files[0]
      if (file && file.type === 'application/pdf') {
        onUpload(file)
      }
    },
    [onUpload],
  )

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) onUpload(file)
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`
        relative flex flex-col items-center justify-center gap-4
        border-2 border-dashed rounded p-12 text-center
        transition-all duration-200 cursor-pointer bg-white
        ${dragging
          ? 'border-[#C8102E] bg-[#fbeaed]'
          : 'border-[#cccccc] hover:border-[#C8102E] hover:bg-[#fbeaed]/30'
        }
      `}
      onClick={() => !uploading && document.getElementById('file-input')?.click()}
    >
      <input
        id="file-input"
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={handleFileInput}
        disabled={uploading}
      />

      <div className={`
        w-16 h-16 rounded-full flex items-center justify-center transition-all border-2
        ${dragging ? 'bg-[#fbeaed] border-[#C8102E]' : 'bg-[#f5f5f5] border-[#e0e0e0]'}
      `}>
        {uploading ? (
          <Loader2 size={28} className="text-[#C8102E] animate-spin" />
        ) : (
          <Upload size={26} className={dragging ? 'text-[#C8102E]' : 'text-[#888888]'} />
        )}
      </div>

      <div>
        <p className="text-base font-semibold text-[#333333]">
          {uploading ? 'Uploading document...' : 'Drop your PDF document here'}
        </p>
        <p className="text-sm text-[#888888] mt-1">
          {uploading ? 'Please wait' : 'or click to browse — PDF files only, max 50MB'}
        </p>
      </div>

      {!uploading && (
        <button className="flex items-center gap-2 px-5 py-2 bg-[#C8102E] text-white text-sm font-medium rounded hover:bg-[#a50d26] transition-colors">
          <FileText size={14} />
          Browse File
        </button>
      )}

      {!uploading && (
        <p className="text-xs text-[#aaaaaa]">
          Bank statements, invoices, loan documents, contracts
        </p>
      )}
    </div>
  )
}
