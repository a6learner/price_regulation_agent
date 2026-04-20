import type { AnalysisResult, Role, RetrievedLegalSource } from '../types'
import { getAdviceSectionTitle } from '../adviceHeading'
import { formatReasoningChain, formatRemediationStep, normalizeLegalReferences } from '../analysisDisplay'
import LegalSourcesPanel from './LegalSourcesPanel'

interface Props {
  result: AnalysisResult
  role: Role
  onOpenTrace: () => void
}

export default function EvidenceCard({ result, role, onOpenTrace }: Props) {
  const raw = result as Record<string, unknown>
  const isViolation = Boolean(result.is_violation)
  const hasRisk = Boolean(result.has_risk_flag)
  const confidence = typeof result.confidence === 'number' ? Math.round(result.confidence * 100) : 0
  const remediation = result.remediation
  const remRaw = remediation as Record<string, unknown> | undefined
  const reasoningText = formatReasoningChain(raw.reasoning_chain)
  const legalRefs = normalizeLegalReferences(raw)
  const retrievedSources = raw.retrieved_legal_sources as RetrievedLegalSource[] | undefined
  const showLegalBlock =
    (retrievedSources && retrievedSources.length > 0) || legalRefs.length > 0

  return (
    <div className="bg-surface-container-lowest rounded-lg ghost-border shadow-ambient overflow-hidden">
      {/* Header bar */}
      <div className={`h-2 w-full ${isViolation ? 'bg-error' : hasRisk ? 'bg-surface-tint' : 'bg-secondary'}`} />

      <div className="p-6 space-y-5">
        {/* Title row */}
        <div className="flex justify-between items-start">
          <div>
            <h3 className="font-headline font-bold text-xl text-primary mb-2">分析完成</h3>
            <div className="flex gap-2 flex-wrap">
              {isViolation ? (
                <span className="bg-error-container text-on-error-container text-xs font-medium px-2 py-1 rounded-sm border border-error/20 flex items-center gap-1">
                  <span className="material-symbols-outlined text-[14px]">warning</span> 存在违规
                </span>
              ) : hasRisk ? (
                <span className="bg-tertiary-fixed text-on-tertiary-fixed-variant text-xs font-medium px-2 py-1 rounded-sm border border-tertiary-fixed-dim/30 flex items-center gap-1">
                  <span className="material-symbols-outlined text-[14px]">info</span> 存在风险
                </span>
              ) : (
                <span className="bg-secondary-container text-on-secondary-container text-xs font-medium px-2 py-1 rounded-sm flex items-center gap-1">
                  <span className="material-symbols-outlined text-[14px]">check_circle</span> 合规
                </span>
              )}
              <span className="bg-surface-container text-on-surface-variant text-xs font-medium px-2 py-1 rounded-sm border border-outline-variant/30">
                置信度: {confidence}%
              </span>
            </div>
          </div>
          {result.violation_type && result.violation_type !== '无违规' && (
            <div className="text-right">
              <div className="text-xs text-on-surface-variant mb-1">违规类型</div>
              <div className="font-bold text-error text-sm">{result.violation_type}</div>
            </div>
          )}
        </div>

        {/* Legal references：检索条文全文（下拉）+ 无数据时的摘要 */}
        {showLegalBlock && (
          <div>
            <div className="text-xs text-on-surface-variant mb-2 font-medium">法律依据</div>
            <LegalSourcesPanel sources={retrievedSources} fallbackRefs={legalRefs} />
          </div>
        )}

        {/* Reasoning chain */}
        {reasoningText.length > 0 && (
          <div>
            <div className="text-xs text-on-surface-variant mb-2 font-medium">推理分析</div>
            <div className="text-sm leading-relaxed text-on-surface font-headline bg-surface-container-low/50 p-4 rounded border border-outline-variant/10 whitespace-pre-line">
              {reasoningText}
            </div>
          </div>
        )}

        {/* Remediation */}
        {remediation && (isViolation || hasRisk || !!remediation.message) && (
          <div className={`pt-4 border-t border-outline-variant/15 ${role === 'merchant' ? '' : ''}`}>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="text-xs text-on-surface-variant font-medium uppercase tracking-wider">
                {getAdviceSectionTitle(role, remRaw, isViolation, hasRisk)}
              </span>
              {role === 'regulator' && typeof remRaw?.risk_rating === 'string' && (
                <span className="text-[11px] px-2 py-0.5 rounded bg-surface-container text-on-surface-variant">
                  风险档位: {remRaw.risk_rating}
                </span>
              )}
            </div>
            {role === 'regulator' && typeof remRaw?.supervision_focus === 'string' && isViolation && (
              <p className="text-xs text-on-surface-variant mb-3 leading-relaxed">{remRaw.supervision_focus}</p>
            )}
            {remediation.remediation_steps && remediation.remediation_steps.length > 0 ? (
              <ul className="list-disc list-inside text-sm text-on-surface space-y-1">
                {remediation.remediation_steps.map((step, i) => (
                  <li key={i}>{formatRemediationStep(step as unknown)}</li>
                ))}
              </ul>
            ) : remediation.risk_suggestions && remediation.risk_suggestions.length > 0 ? (
              <ul className="list-disc list-inside text-sm text-on-surface space-y-1">
                {remediation.risk_suggestions.map((s, i) => (
                  <li key={i}>{formatRemediationStep(s as unknown)}</li>
                ))}
              </ul>
            ) : remediation.message ? (
              <p className="text-sm text-on-surface-variant">{remediation.message}</p>
            ) : null}
          </div>
        )}

        {/* View full trace button */}
        <button
          onClick={onOpenTrace}
          className="text-sm text-primary font-medium flex items-center gap-1 hover:underline cursor-pointer"
        >
          <span className="material-symbols-outlined text-[16px]">open_in_new</span>
          查看完整溯源
        </button>
      </div>
    </div>
  )
}
