import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import TopAppBar from '../components/TopAppBar'
import Pagination from '../components/Pagination'
import { browseKnowledge } from '../api'
import type { Role, KnowledgeItem } from '../types'

type Tab = 'laws' | 'cases'

export default function Knowledge() {
  const [params] = useSearchParams()
  const role = (params.get('role') || undefined) as Role | undefined

  const [tab, setTab] = useState<Tab>('laws')
  const [page, setPage] = useState(1)
  const [query, setQuery] = useState('')
  const [items, setItems] = useState<KnowledgeItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const pageSize = 15
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined)

  const load = async (t: Tab, p: number, q: string) => {
    setLoading(true)
    try {
      const res = await browseKnowledge(t, p, pageSize, q || undefined)
      setItems(res.items)
      setTotal(res.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load(tab, page, query)
  }, [tab, page])

  const handleSearch = (val: string) => {
    setQuery(val)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setPage(1)
      load(tab, 1, val)
    }, 300)
  }

  const handleTabChange = (t: Tab) => {
    setTab(t)
    setPage(1)
    setQuery('')
  }

  return (
    <div className="min-h-screen bg-surface text-on-surface font-body">
      <TopAppBar role={role} />

      <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {/* Header */}
        <div>
          <h1 className="font-headline font-bold text-3xl text-primary m-0">知识库</h1>
          <p className="text-on-surface-variant text-sm mt-2 m-0">浏览系统内置的法规条文与行政处罚案例</p>
        </div>

        {/* Tab switcher */}
        <div className="flex gap-2">
          <button
            onClick={() => handleTabChange('laws')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
              tab === 'laws' ? 'bg-primary text-on-primary' : 'bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest'
            }`}
          >
            <span className="material-symbols-outlined text-[16px] align-middle mr-1">gavel</span>
            法规库 ({tab === 'laws' ? total : '691'})
          </button>
          <button
            onClick={() => handleTabChange('cases')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
              tab === 'cases' ? 'bg-primary text-on-primary' : 'bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest'
            }`}
          >
            <span className="material-symbols-outlined text-[16px] align-middle mr-1">folder_open</span>
            案例库 ({tab === 'cases' ? total : '133'})
          </button>
        </div>

        {/* Search */}
        <div className="relative">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline">search</span>
          <input
            type="text"
            value={query}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-3 bg-surface-container-highest border-0 rounded-lg text-sm focus:ring-2 focus:ring-primary/30 text-on-surface outline-none"
            placeholder={tab === 'laws' ? '搜索法规条文（如：明码标价）...' : '搜索处罚案例...'}
          />
        </div>

        {/* Items */}
        {loading ? (
          <div className="text-center py-12 text-on-surface-variant">
            <span className="material-symbols-outlined text-2xl animate-spin">sync</span>
            <p className="mt-2 text-sm">加载中...</p>
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-12 text-on-surface-variant">
            <span className="material-symbols-outlined text-4xl opacity-30">search_off</span>
            <p className="mt-2 text-sm">未找到匹配结果</p>
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((item) => (
              <div key={item.chunk_id} className="bg-surface-container-lowest rounded-lg ghost-border p-5 hover:shadow-ambient transition-shadow">
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    {item.metadata.law_name && (
                      <span className="text-sm font-bold text-primary">{item.metadata.law_name}</span>
                    )}
                    {item.metadata.article && (
                      <span className="text-xs bg-primary-fixed text-on-primary-fixed-variant px-2 py-0.5 rounded-sm font-medium">
                        {item.metadata.article}
                      </span>
                    )}
                    {item.metadata.law_level && (
                      <span className="text-xs bg-surface-container-high text-on-surface-variant px-2 py-0.5 rounded-sm">
                        {item.metadata.law_level}
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] text-outline shrink-0">{item.chunk_id}</span>
                </div>
                <p className="text-sm text-on-surface leading-relaxed line-clamp-4">{item.content}</p>
              </div>
            ))}
          </div>
        )}

        <Pagination page={page} total={total} pageSize={pageSize} onChange={setPage} />
      </div>
    </div>
  )
}
