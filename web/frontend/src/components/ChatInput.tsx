import { useState, useRef, type KeyboardEvent } from 'react'
import { uploadDoc } from '../api'

interface Props {
  onSend: (text: string, attachmentText: string | null) => void
  disabled: boolean
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [text, setText] = useState('')
  const [attachment, setAttachment] = useState<{ name: string; text: string } | null>(null)
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleSend = () => {
    const q = text.trim()
    if (!q || disabled) return
    onSend(q, attachment?.text ?? null)
    setText('')
    setAttachment(null)
  }

  const handleKey = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleFile = async (file: File) => {
    setUploading(true)
    try {
      const res = await uploadDoc(file)
      setAttachment({ name: res.filename, text: res.text_preview })
    } catch {
      alert('文件上传失败')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="p-6 bg-surface border-t border-outline-variant/10">
      <div className="max-w-4xl mx-auto">
        {attachment && (
          <div className="mb-2 flex items-center gap-2 text-sm text-primary bg-primary-fixed/30 px-3 py-1.5 rounded-lg w-fit">
            <span className="material-symbols-outlined text-[16px]">description</span>
            {attachment.name}
            <button onClick={() => setAttachment(null)} className="text-on-surface-variant hover:text-error cursor-pointer">
              <span className="material-symbols-outlined text-[14px]">close</span>
            </button>
          </div>
        )}
        <div className="relative bg-surface-container-highest rounded-xl transition-all duration-300 focus-within:ring-2 focus-within:ring-primary/30 focus-within:bg-surface-container-lowest focus-within:shadow-[0_0_15px_rgba(70,95,136,0.1)]">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKey}
            className="w-full bg-transparent border-none focus:ring-0 focus:outline-none resize-none p-4 pb-12 text-sm text-on-surface placeholder-on-surface-variant"
            placeholder="输入价格行为描述，进行合规分析..."
            rows={2}
            disabled={disabled}
          />
          <div className="absolute bottom-3 left-3 flex gap-2">
            <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" className="hidden" onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
            <button
              onClick={() => fileRef.current?.click()}
              disabled={uploading || disabled}
              className="p-1.5 text-on-surface-variant hover:text-primary rounded-md hover:bg-surface-container-low transition-colors cursor-pointer disabled:opacity-40"
            >
              <span className="material-symbols-outlined text-[20px]">{uploading ? 'hourglass_empty' : 'attach_file'}</span>
            </button>
          </div>
          <button
            onClick={handleSend}
            disabled={!text.trim() || disabled}
            className="absolute bottom-3 right-3 bg-primary-container text-on-primary px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-primary transition-colors flex items-center gap-2 cursor-pointer disabled:opacity-40"
          >
            发送 <span className="material-symbols-outlined text-[18px]">send</span>
          </button>
        </div>
        <div className="text-center mt-2">
          <span className="text-[10px] text-on-surface-variant">AI 分析结果仅供参考，关键法律判断请以专业意见为准</span>
        </div>
      </div>
    </div>
  )
}
