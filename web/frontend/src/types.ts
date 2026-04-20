export type Role = 'consumer' | 'regulator' | 'merchant'

export const NODE_NAMES = ['intent', 'retrieval', 'grading', 'reasoning', 'reflection', 'remediation'] as const
export type NodeName = (typeof NODE_NAMES)[number]
export type NodeStatus = 'pending' | 'active' | 'done'

export const NODE_LABELS: Record<NodeName, string> = {
  intent: '意图分析',
  retrieval: '法规检索',
  grading: '质量评分',
  reasoning: '推理分析',
  reflection: '反思验证',
  remediation: '整改建议',
}

export const ROLE_LABELS: Record<Role, string> = {
  consumer: '消费者',
  regulator: '政府监管',
  merchant: '网店商家',
}

export interface NodeState {
  name: NodeName
  status: NodeStatus
  detail?: Record<string, unknown>
}

export interface Message {
  id: string
  sender: 'user' | 'ai'
  content: string
  result?: AnalysisResult
  traceId?: string
  nodes?: NodeState[]
  error?: string
}

/** 后端 RAG 检索并经 Grader 保留的法规片段（含全文） */
export interface RetrievedLegalSource {
  chunk_id?: string
  label: string
  law_name?: string
  article?: string
  content: string
  score?: number
}

export interface AnalysisResult {
  is_violation: boolean
  violation_type: string
  confidence: number
  has_risk_flag?: boolean
  reasoning_chain?: string
  legal_references?: string[]
  /** 检索到的法规全文，供前端下拉展示 */
  retrieved_legal_sources?: RetrievedLegalSource[]
  remediation?: {
    has_violation: boolean
    has_risk_flag?: boolean
    /** 后端按身份生成的区块标题 */
    panel_title?: string
    audience?: string
    /** 监管视角：模型置信度映射的风险档位 */
    risk_rating?: string
    supervision_focus?: string
    remediation_steps?: string[]
    risk_suggestions?: string[]
    message?: string
    generation_mode?: string
  }
  [key: string]: unknown
}

export interface TraceItem {
  id: string
  query: string
  role: string
  duration_ms: number | null
  created_at: string
}

export interface TraceDetail extends TraceItem {
  result: AnalysisResult
}

export interface KnowledgeItem {
  chunk_id: string
  content: string
  metadata: Record<string, string>
}

export interface KnowledgePage {
  items: KnowledgeItem[]
  total: number
  page: number
  page_size: number
}

export interface SSEEvent {
  event: string
  data: Record<string, unknown>
}
