import type { Role, SSEEvent, TraceDetail, TraceItem, KnowledgePage } from './types'

export async function streamChat(
  query: string,
  role: Role,
  attachmentText: string | null,
  onEvent: (evt: SSEEvent) => void,
): Promise<void> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, role, attachment_text: attachmentText }),
  })

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split(/\r?\n/)
    buffer = lines.pop() ?? ''

    let currentEvent = ''
    for (const raw of lines) {
      const line = raw.replace(/\r$/, '')
      if (!line) continue
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim()
      } else if (line.startsWith('data: ') && currentEvent) {
        try {
          const data = JSON.parse(line.slice(6))
          onEvent({ event: currentEvent, data })
        } catch {
          /* skip malformed */
        }
        currentEvent = ''
      }
    }
  }
}

export async function uploadDoc(file: File) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/upload', { method: 'POST', body: form })
  return res.json() as Promise<{ filename: string; text_length: number; text_preview: string }>
}

export async function getTrace(traceId: string): Promise<TraceDetail> {
  const res = await fetch(`/api/trace/${traceId}`)
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string }
    throw new Error(err.detail || `加载失败 (${res.status})`)
  }
  return res.json()
}

export async function listTraces(page = 1, pageSize = 20): Promise<{ items: TraceItem[]; total: number }> {
  const res = await fetch(`/api/traces?page=${page}&page_size=${pageSize}`)
  if (!res.ok) throw new Error('无法加载历史列表')
  return res.json()
}

export async function deleteTrace(traceId: string): Promise<void> {
  const res = await fetch(`/api/trace/${encodeURIComponent(traceId)}`, { method: 'DELETE' })
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string }
    throw new Error(err.detail || '删除失败')
  }
}

export async function deleteAllTraces(): Promise<{ deleted: number }> {
  const res = await fetch('/api/traces', { method: 'DELETE' })
  if (!res.ok) throw new Error('清空失败')
  return res.json() as Promise<{ deleted: number }>
}

export async function browseKnowledge(
  type: 'laws' | 'cases',
  page = 1,
  pageSize = 20,
  q?: string,
): Promise<KnowledgePage> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (q) params.set('q', q)
  const res = await fetch(`/api/knowledge/${type}?${params}`)
  return res.json()
}
