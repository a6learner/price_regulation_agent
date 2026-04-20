/** 后端推理结果字段在 LLM 输出下可能是 string 或 string[]，统一为可安全渲染的文本 */

export function formatReasoningChain(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    return value.map((x) => (typeof x === 'string' ? x : JSON.stringify(x))).join('\n')
  }
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

/** 后端 remediation_steps 可能是 string，也可能是 { step, action, legal_basis, priority, responsible_party } */
export function formatRemediationStep(step: unknown): string {
  if (step == null) return ''
  if (typeof step === 'string') return step
  if (typeof step === 'object' && step !== null) {
    const o = step as Record<string, unknown>
    if (typeof o.action === 'string') {
      const n = o.step != null ? `${o.step}. ` : ''
      let s = `${n}${o.action}`
      if (typeof o.legal_basis === 'string' && o.legal_basis.trim()) {
        s += `（依据：${o.legal_basis}）`
      }
      if (typeof o.responsible_party === 'string' && o.responsible_party.trim()) {
        s += ` — ${o.responsible_party}`
      }
      return s
    }
    try {
      return JSON.stringify(step)
    } catch {
      return String(step)
    }
  }
  return String(step)
}

/** 前端曾用 legal_references，后端推理 JSON 多为 legal_basis */
export function normalizeLegalReferences(result: Record<string, unknown>): string[] {
  const refs = result.legal_references
  if (Array.isArray(refs)) {
    return refs.map((r) => (typeof r === 'string' ? r : String(r))).filter(Boolean)
  }
  const basis = result.legal_basis
  if (typeof basis === 'string' && basis.trim()) return [basis.trim()]
  return []
}
