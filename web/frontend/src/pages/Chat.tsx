import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import TopAppBar from '../components/TopAppBar'
import ProgressTimeline from '../components/ProgressTimeline'
import MessageBubble from '../components/MessageBubble'
import EvidenceCard from '../components/EvidenceCard'
import ChatInput from '../components/ChatInput'
import TraceDrawer from '../components/TraceDrawer'
import { streamChat, listTraces, deleteTrace, deleteAllTraces } from '../api'
import { NODE_NAMES } from '../types'
import type { Role, Message, NodeState, TraceItem } from '../types'

function makeInitialNodes(): NodeState[] {
  return NODE_NAMES.map((name) => ({ name, status: 'pending' as const }))
}

export default function Chat() {
  const [params] = useSearchParams()
  const role = (params.get('role') || 'consumer') as Role

  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [history, setHistory] = useState<TraceItem[]>([])
  const [drawerTraceId, setDrawerTraceId] = useState<string | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  const refreshHistory = () =>
    listTraces(1, 30)
      .then((res) => setHistory(res.items))
      .catch(() => setHistory([]))

  useEffect(() => {
    refreshHistory()
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async (text: string, attachmentText: string | null) => {
    const userMsg: Message = { id: crypto.randomUUID(), sender: 'user', content: text }
    const aiMsg: Message = { id: crypto.randomUUID(), sender: 'ai', content: '', nodes: makeInitialNodes() }

    setMessages((prev) => [...prev, userMsg, aiMsg])
    setIsStreaming(true)

    const aiId = aiMsg.id

    try {
      await streamChat(text, role, attachmentText, (evt) => {
        const { event, data } = evt

        if (event === 'done') {
          try {
            const result = (data as Record<string, unknown>).result as Message['result']
            const traceId = (data as Record<string, unknown>).trace_id as string
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aiId
                  ? { ...m, result, traceId, nodes: m.nodes?.map((n) => ({ ...n, status: 'done' as const })) }
                  : m,
              ),
            )
          } catch (e) {
            console.error(e)
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aiId ? { ...m, error: '结果解析异常，请查看历史记录中的原始 JSON' } : m,
              ),
            )
          }
          refreshHistory()
        } else if (event === 'error') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === aiId ? { ...m, error: (data as Record<string, unknown>).message as string } : m,
            ),
          )
        } else {
          // Node progress event
          const nodeName = event as NodeState['name']
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== aiId) return m
              const nodes = m.nodes?.map((n) => {
                if (n.name === nodeName) return { ...n, status: 'done' as const, detail: (data as Record<string, unknown>).detail as Record<string, unknown> }
                // Mark next pending node as active
                return n
              })
              // Find first pending and set to active
              if (nodes) {
                const doneIdx = nodes.findIndex((n) => n.name === nodeName)
                for (let i = doneIdx + 1; i < nodes.length; i++) {
                  if (nodes[i].status === 'pending') {
                    nodes[i] = { ...nodes[i], status: 'active' }
                    break
                  }
                }
              }
              return { ...m, nodes }
            }),
          )
        }
      })
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) => (m.id === aiId ? { ...m, error: '连接失败，请检查后端是否运行' } : m)),
      )
    } finally {
      setIsStreaming(false)
    }
  }

  const openTrace = (traceId: string) => {
    setDrawerTraceId(traceId)
    setDrawerOpen(true)
  }

  const handleDeleteHistory = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    if (!window.confirm('确定删除这条历史记录？')) return
    try {
      await deleteTrace(id)
      if (drawerTraceId === id) {
        setDrawerOpen(false)
        setDrawerTraceId(null)
      }
      await refreshHistory()
    } catch (err) {
      alert(err instanceof Error ? err.message : '删除失败')
    }
  }

  const handleClearAllHistory = async () => {
    if (!window.confirm('确定清空全部历史记录？此操作不可恢复。')) return
    try {
      await deleteAllTraces()
      setDrawerOpen(false)
      setDrawerTraceId(null)
      await refreshHistory()
    } catch (err) {
      alert(err instanceof Error ? err.message : '清空失败')
    }
  }

  return (
    <div className="h-screen flex flex-col bg-surface text-on-surface font-body overflow-hidden">
      <TopAppBar role={role} />

      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar: history */}
        <aside className="w-72 bg-surface-container-low border-r border-outline-variant/15 flex flex-col flex-shrink-0">
          <div className="p-4 border-b border-outline-variant/15 flex justify-between items-center gap-2">
            <span className="font-headline font-bold text-sm text-primary">历史记录</span>
            {history.length > 0 && (
              <button
                type="button"
                title="清空全部"
                onClick={handleClearAllHistory}
                className="text-xs text-on-surface-variant hover:text-error px-2 py-1 rounded cursor-pointer"
              >
                清空
              </button>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-1">
            {history.length === 0 && (
              <p className="text-xs text-on-surface-variant text-center py-8">暂无历史记录</p>
            )}
            {history.map((h) => (
              <div
                key={h.id}
                className="group flex items-center gap-1 rounded-md hover:bg-surface-container-high transition-colors"
              >
                <button
                  type="button"
                  onClick={() => openTrace(h.id)}
                  className="flex-1 min-w-0 text-left px-3 py-2 text-on-surface-variant text-sm flex items-center gap-2 cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[18px] shrink-0">chat_bubble_outline</span>
                  <span className="truncate">{(h.query ?? '').slice(0, 40)}</span>
                </button>
                <button
                  type="button"
                  title="删除"
                  onClick={(e) => handleDeleteHistory(e, h.id)}
                  className="shrink-0 p-2 text-on-surface-variant hover:text-error opacity-70 hover:opacity-100 cursor-pointer rounded"
                >
                  <span className="material-symbols-outlined text-[18px]">delete</span>
                </button>
              </div>
            ))}
          </div>
        </aside>

        {/* Main chat area */}
        <main className="flex-1 flex flex-col relative">
          <div className="flex-1 overflow-y-auto p-8 space-y-8">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-on-surface-variant space-y-4">
                <span className="material-symbols-outlined text-6xl opacity-20">balance</span>
                <p className="text-lg font-headline">输入价格行为描述，开始合规分析</p>
                <p className="text-sm max-w-md text-center">
                  支持输入商品定价情况、促销活动描述、价格标示问题等，AI 将自动检索法规并给出分析结论。
                </p>
              </div>
            )}

            {messages.map((msg) => {
              if (msg.sender === 'user') {
                return <MessageBubble key={msg.id} sender="user" content={msg.content} />
              }

              return (
                <div key={msg.id} className="flex items-start gap-4 max-w-4xl">
                  <div className="w-8 h-8 rounded-full bg-primary-container flex items-center justify-center flex-shrink-0 mt-1">
                    <span className="material-symbols-outlined text-on-primary text-sm">balance</span>
                  </div>
                  <div className="flex-1 space-y-4">
                    {/* Progress timeline */}
                    {msg.nodes && <ProgressTimeline nodes={msg.nodes} />}

                    {/* Error */}
                    {msg.error && (
                      <div className="bg-error-container text-on-error-container p-4 rounded-lg text-sm flex items-center gap-2">
                        <span className="material-symbols-outlined text-[18px]">error</span>
                        {msg.error}
                      </div>
                    )}

                    {/* Result card */}
                    {msg.result && (
                      <EvidenceCard
                        result={msg.result}
                        role={role}
                        onOpenTrace={() => msg.traceId && openTrace(msg.traceId)}
                      />
                    )}

                    {/* Loading state */}
                    {!msg.result && !msg.error && (
                      <div className="text-sm text-on-surface-variant flex items-center gap-2">
                        <span className="material-symbols-outlined text-[16px] animate-spin">sync</span>
                        分析中...
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
            <div ref={chatEndRef} />
          </div>

          <ChatInput onSend={handleSend} disabled={isStreaming} />
        </main>
      </div>

      {/* Trace drawer */}
      <TraceDrawer traceId={drawerTraceId} open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  )
}
