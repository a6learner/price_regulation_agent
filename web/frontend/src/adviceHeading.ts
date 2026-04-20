import type { Role } from './types'

/** 与后端 remediation.panel_title 一致；无则按身份兜底 */
export function getAdviceSectionTitle(
  role: Role,
  remediation: Record<string, unknown> | undefined,
  isViolation: boolean,
  hasRisk: boolean,
): string {
  const pt = remediation?.panel_title
  if (typeof pt === 'string' && pt.trim()) return pt
  if (hasRisk) {
    if (role === 'consumer') return '风险提示与自我保护'
    if (role === 'regulator') return '监管关注与行政指导'
    return '合规风险提示'
  }
  if (isViolation) {
    if (role === 'consumer') return '维权与法律指引'
    if (role === 'regulator') return '监管处置与下一步'
    return '整改建议'
  }
  if (role === 'consumer') return '说明'
  if (role === 'regulator') return '监管意见'
  return '说明'
}
