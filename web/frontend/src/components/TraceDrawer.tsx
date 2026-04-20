import { useEffect, useState } from 'react'
import { getTrace } from '../api'
import type { TraceDetail, RetrievedLegalSource, Role } from '../types'
import { getAdviceSectionTitle } from '../adviceHeading'
import { formatReasoningChain, formatRemediationStep, normalizeLegalReferences } from '../analysisDisplay'
import LegalSourcesPanel from './LegalSourcesPanel'

interface Props {
  traceId: string | null
  open: boolean
  onClose: () => void
}

export default function TraceDrawer({ traceId, open, onClose }: Props) {
  const [trace, setTrace] = useState<TraceDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    if (!traceId || !open) return
    setLoading(true)
    setLoadError(null)
    setTrace(null)
    getTrace(traceId)
      .then(setTrace)
      .catch((e: Error) => setLoadError(e.message))
      .finally(() => setLoading(false))
  }, [traceId, open])

  return (
    <>
      {/* Backdrop */}
      {open && <div className="fixed inset-0 bg-black/10 z-30" onClick={onClose} />}

      {/* Drawer */}
      <div className={`fixed right-0 top-0 h-full w-[560px] max-w-[90vw] z-40 bg-white/95 backdrop-blur-2xl shadow-[-12px_0_40px_rgba(27,54,93,0.08)] transition-transform duration-300 ${open ? 'translate-x-0' : 'translate-x-full'}`}>
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between px-6 py-4 border-b border-outline-variant/15 bg-white/90 backdrop-blur-md">
          <div>
            <h2 className="font-headline font-bold text-lg text-primary flex items-center gap-2">
              <span className="material-symbols-outlined text-[20px]">library_books</span>
              完整溯源
            </h2>
            {trace && (
              <span className="text-xs text-on-surface-variant">
                耗时 {trace.duration_ms ? `${(trace.duration_ms / 1000).toFixed(1)}s` : '-'}
              </span>
            )}
          </div>
          <button onClick={onClose} className="p-2 hover:bg-surface-container-high rounded-full transition-colors cursor-pointer">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto h-[calc(100%-64px)] space-y-8">
          {loading && <div className="text-center text-on-surface-variant py-12">加载中...</div>}

          {loadError && !loading && (
            <div className="bg-error-container/80 text-on-error-container p-4 rounded-lg text-sm">{loadError}</div>
          )}

          {trace && !loading && !loadError && (() => {
            const res = trace.result as Record<string, unknown> | undefined
            if (!res || typeof res !== 'object') {
              return (
                <div className="text-sm text-on-surface-variant">该记录没有可展示的分析结果。</div>
              )
            }
            const pipelineError = typeof res.error === 'string' ? res.error : null
            const legalRefs = normalizeLegalReferences(res)
            const retrievedSources = res.retrieved_legal_sources as RetrievedLegalSource[] | undefined
            const showLegalSection =
              (retrievedSources && retrievedSources.length > 0) || legalRefs.length > 0
            const reasoningText = formatReasoningChain(res.reasoning_chain)
            const isViolation = Boolean(res.is_violation)
            const hasRisk = Boolean(res.has_risk_flag)
            const conf = typeof res.confidence === 'number' ? res.confidence : 0
            const violationType = typeof res.violation_type === 'string' ? res.violation_type : '无违规'
            const traceRole = (trace.role || 'consumer') as Role
            const rem = res.remediation as Record<string, unknown> | undefined

            return (
            <>
              {/* Query */}
              <section>
                <div className="text-xs text-on-surface-variant mb-2 font-medium uppercase tracking-wider">原始查询</div>
                <div className="bg-surface-container-low p-4 rounded-lg text-sm text-on-surface leading-relaxed">
                  {trace.query}
                </div>
              </section>

              {pipelineError && (
                <section>
                  <div className="text-xs text-on-surface-variant mb-2 font-medium uppercase tracking-wider">管线错误</div>
                  <div className="bg-error-container/50 text-on-error-container p-4 rounded-lg text-sm whitespace-pre-wrap">
                    {pipelineError}
                  </div>
                </section>
              )}

              {/* Verdict */}
              <section>
                <div className="text-xs text-on-surface-variant mb-2 font-medium uppercase tracking-wider">判定结果</div>
                <div className="flex gap-3 flex-wrap">
                  {isViolation ? (
                    <span className="bg-error-container text-on-error-container text-sm font-medium px-3 py-1.5 rounded-sm flex items-center gap-1">
                      <span className="material-symbols-outlined text-[16px]">warning</span> 违规 — {violationType}
                    </span>
                  ) : hasRisk ? (
                    <span className="bg-tertiary-fixed text-on-tertiary-fixed-variant text-sm font-medium px-3 py-1.5 rounded-sm flex items-center gap-1">
                      <span className="material-symbols-outlined text-[16px]">info</span> 存在风险
                    </span>
                  ) : (
                    <span className="bg-secondary-container text-on-secondary-container text-sm font-medium px-3 py-1.5 rounded-sm flex items-center gap-1">
                      <span className="material-symbols-outlined text-[16px]">check_circle</span> 合规
                    </span>
                  )}
                  <span className="bg-surface-container text-on-surface-variant text-sm px-3 py-1.5 rounded-sm">
                    置信度: {Math.round(conf * 100)}%
                  </span>
                </div>
              </section>

              {/* Legal references：检索全文下拉 + 摘要兜底 */}
              {showLegalSection && (
                <section>
                  <div className="text-xs text-on-surface-variant mb-2 font-medium uppercase tracking-wider">法律依据</div>
                  <LegalSourcesPanel sources={retrievedSources} fallbackRefs={legalRefs} />
                </section>
              )}

              {/* Reasoning chain */}
              {reasoningText.length > 0 && (
                <section>
                  <div className="text-xs text-on-surface-variant mb-2 font-medium uppercase tracking-wider">推理链</div>
                  <div className="bg-surface-container-low p-4 rounded-lg text-sm leading-relaxed font-headline whitespace-pre-line text-on-surface border border-outline-variant/10">
                    {reasoningText}
                  </div>
                </section>
              )}

              {/* Remediation / 身份化建议 */}
              {res.remediation && typeof res.remediation === 'object' && (
                <section>
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <span className="text-xs text-on-surface-variant font-medium uppercase tracking-wider">
                      {getAdviceSectionTitle(
                        traceRole,
                        rem,
                        isViolation,
                        Boolean((res.remediation as { has_risk_flag?: boolean }).has_risk_flag),
                      )}
                    </span>
                    {traceRole === 'regulator' && typeof rem?.risk_rating === 'string' && (
                      <span className="text-[11px] px-2 py-0.5 rounded bg-surface-container text-on-surface-variant">
                        风险档位: {rem.risk_rating}
                      </span>
                    )}
                  </div>
                  {traceRole === 'regulator' && typeof rem?.supervision_focus === 'string' && isViolation && (
                    <p className="text-xs text-on-surface-variant mb-3 leading-relaxed">{rem.supervision_focus}</p>
                  )}
                  {(res.remediation as { remediation_steps?: unknown[] }).remediation_steps?.map((step, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm text-on-surface py-1">
                      <span className="text-secondary font-bold">{i + 1}.</span>
                      <span>{formatRemediationStep(step)}</span>
                    </div>
                  ))}
                  {(res.remediation as { risk_suggestions?: unknown[] }).risk_suggestions?.map((s, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm text-on-surface py-1">
                      <span className="text-surface-tint font-bold">{i + 1}.</span>
                      <span>{formatRemediationStep(s)}</span>
                    </div>
                  ))}
                  {(res.remediation as { message?: string; remediation_steps?: string[] }).message &&
                    !(res.remediation as { remediation_steps?: string[] }).remediation_steps?.length && (
                    <p className="text-sm text-on-surface-variant">{String((res.remediation as { message?: string }).message)}</p>
                  )}
                </section>
              )}

              {/* Raw data (collapsed) */}
              <details className="text-xs">
                <summary className="text-on-surface-variant cursor-pointer hover:text-primary">查看原始 JSON</summary>
                <pre className="mt-2 p-3 bg-surface-container-highest rounded-lg overflow-auto max-h-60 text-[11px]">
                  {JSON.stringify(trace.result, null, 2)}
                </pre>
              </details>
            </>
            )
          })()}
        </div>
      </div>
    </>
  )
}
