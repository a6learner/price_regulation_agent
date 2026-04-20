import { useState, useMemo, useEffect } from 'react'
import type { RetrievedLegalSource } from '../types'

interface Props {
  sources?: RetrievedLegalSource[] | null
  /** 无全文数据时的引用短句（模型输出） */
  fallbackRefs?: string[]
}

/**
 * 法律依据：下拉选择检索到的条文，下方展示全文。
 * 无 retrieved_legal_sources 时仅展示 fallback 引用短句。
 */
export default function LegalSourcesPanel({ sources, fallbackRefs = [] }: Props) {
  const list = useMemo(
    () => (sources ?? []).filter((s) => s.content && String(s.content).trim()),
    [sources],
  )
  const [idx, setIdx] = useState(0)

  useEffect(() => {
    if (idx >= list.length) setIdx(0)
  }, [idx, list.length])

  if (list.length === 0) {
    if (fallbackRefs.length === 0) return null
    return (
      <div>
        <div className="text-xs text-on-surface-variant mb-2 font-medium">法律依据（摘要）</div>
        <ul className="flex flex-wrap gap-2">
          {fallbackRefs.map((ref, i) => (
            <li
              key={i}
              className="bg-surface-container-low border border-outline-variant/20 px-3 py-1.5 rounded-md text-sm text-primary flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-[16px]">gavel</span>
              {ref}
            </li>
          ))}
        </ul>
        <p className="text-xs text-on-surface-variant mt-2">
          本条记录未保存检索条文全文，请重新分析以查看全文。
        </p>
      </div>
    )
  }

  const current = list[Math.min(idx, list.length - 1)]

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
        <label htmlFor="legal-source-select" className="text-xs text-on-surface-variant shrink-0 font-medium">
          选择条文查看全文
        </label>
        <select
          id="legal-source-select"
          className="flex-1 min-w-0 rounded-lg border border-outline-variant/30 bg-surface-container-low px-3 py-2 text-sm text-on-surface cursor-pointer"
          value={idx}
          onChange={(e) => setIdx(Number(e.target.value))}
        >
          {list.map((s, i) => (
            <option key={s.chunk_id ?? `law-${i}`} value={i}>
              {s.label}
            </option>
          ))}
        </select>
      </div>
      {typeof current.score === 'number' && (
        <p className="text-[11px] text-on-surface-variant">检索相关度评分: {current.score.toFixed(3)}</p>
      )}
      <div className="max-h-80 overflow-y-auto rounded-lg border border-outline-variant/15 bg-surface-container-lowest p-4 text-sm leading-relaxed text-on-surface whitespace-pre-wrap">
        {current.content}
      </div>
    </div>
  )
}
